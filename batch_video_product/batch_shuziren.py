import os
import shutil
from datetime import datetime

import pandas as pd
import yaml
from gradio_client import Client


def load_config(config_path):
    """加载配置文件并进行验证"""
    with open(config_path, encoding='utf-8') as f:
        config = yaml.safe_load(f)

    required_keys = ['excel', 'api', 'output']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"缺失必要配置项: {key}")

    return config

class BatchVideoProcessor:
    def __init__(self, config_path="config_excel.yaml"):
        self.config = load_config(config_path)
        self.client = Client(self.config['api']['endpoint'])
        self.setup_directories()
        self.task_data = self.load_task_data()

    def setup_directories(self):
        """创建输出目录结构"""
        os.makedirs(self.config['output']['dir'], exist_ok=True)
        os.makedirs(self.config['output']['log_dir'], exist_ok=True)

    def load_task_data(self):
        """从Excel加载任务数据"""
        try:
            df = pd.read_excel(
                self.config['excel']['path'],
                sheet_name=self.config['excel']['sheet'],
                usecols=[
                    self.config['excel']['columns']['video'],
                    self.config['excel']['columns']['audio'],
                ]
            )
        except Exception as e:
            raise ValueError(f"Excel文件读取失败: {str(e)}")

        # 清理数据
        df = df.dropna(subset=[
            self.config['excel']['columns']['video'],
            self.config['excel']['columns']['audio']
        ])

        return df.to_dict('records')

    def process_all_tasks(self):
        """处理所有任务"""
        log_data = []
        total = len(self.task_data)

        print(f"开始批量处理，共 {total} 个任务")

        for idx, task in enumerate(self.task_data, 1):
            task_log = self.process_single_task(task, idx)
            log_data.append(task_log)

            # 进度显示
            print(
                f"\r处理进度: {idx}/{total} | 成功: {len([x for x in log_data if x['status']])} 失败: {len([x for x in log_data if not x['status']])}",
                end="")

        # 保存处理日志
        self.save_log_report(log_data)
        print("\n处理完成，结果已保存至输出目录")

    def process_single_task(self, task, task_id):
        """处理单个任务"""
        log_entry = {
            'task_id': task_id,
            'video': task[self.config['excel']['columns']['video']],
            'audio': task[self.config['excel']['columns']['audio']],
            'status': False,
            'output_path': None,
            'time_cost': None,
            'error': None
        }

        try:
            # 准备参数
            params = {
                "video": str(task[self.config['excel']['columns']['video']]),
                "audio": str(task[self.config['excel']['columns']['audio']]),
                "min_resolution": float(task.get(
                    self.config['excel']['columns'].get('min_res', ''),
                    self.config['api']['defaults']['min_resolution']
                )),
                "if_res": bool(task.get(
                    self.config['excel']['columns'].get('if_res', ''),
                    self.config['api']['defaults']['if_res']
                ))
            }

            # API调用
            result = self.client.predict(
                **params,
                api_name=self.config['api']['name']
            )

            # 处理结果
            output_video = result[0]['video']
            time_cost = result[1]

            # 移动文件到输出目录
            final_path = self.save_output_file(
                output_video,
                params['video'],
                params['audio']
            )

            log_entry.update({
                'status': True,
                'output_path': final_path,
                'time_cost': time_cost
            })

        except Exception as e:
            log_entry['error'] = str(e)
            self.write_error_log(task_id, str(e))

        return log_entry

    def save_output_file(self, src_path, video_ref, audio_ref):
        """保存输出文件"""
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = os.path.splitext(os.path.basename(video_ref))[0][:15]
        audio_name = os.path.splitext(os.path.basename(audio_ref))[0][:15]

        filename = f"{timestamp}_{video_name}_{audio_name}.mp4"
        dest_path = os.path.join(self.config['output']['dir'], filename)

        shutil.move(src_path, dest_path)
        return dest_path

    def save_log_report(self, log_data):
        """保存日志报告"""
        # Excel日志
        df = pd.DataFrame(log_data)
        report_path = os.path.join(
            self.config['output']['log_dir'],
            f"processing_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
        df.to_excel(report_path, index=False)

        # 文本日志
        text_log_path = os.path.join(
            self.config['output']['log_dir'],
            f"processing_log_{datetime.now().strftime('%Y%m%d')}.log"
        )
        with open(text_log_path, "a") as f:
            for entry in log_data:
                log_line = f"[{datetime.now()}] Task {entry['task_id']} - {'SUCCESS' if entry['status'] else 'FAILED'}"
                if entry['status']:
                    log_line += f" | Output: {entry['output_path']} | Time: {entry['time_cost']}"
                else:
                    log_line += f" | Error: {entry['error']}"
                f.write(log_line + "\n")

    def write_error_log(self, task_id, error_msg):
        """单独记录错误日志"""
        error_log_path = os.path.join(
            self.config['output']['log_dir'],
            "error_log.log"
        )
        with open(error_log_path, "a") as f:
            f.write(f"[{datetime.now()}] Task {task_id} - Error: {error_msg}\n")


if __name__ == "__main__":
    try:
        processor = BatchVideoProcessor()
        processor.process_all_tasks()
    except Exception as e:
        print(f"初始化失败: {str(e)}")
