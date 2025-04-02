# main.py
import os
import shutil
from datetime import datetime

import yaml
from gradio_client import Client, handle_file


def load_config(config_path):
    """加载并验证配置文件"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # 验证必要配置项
    required_keys = ["api_config", "paths", "file_settings"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"配置文件中缺少必要字段: {key}")

    return config


class VideoGenerator:
    def __init__(self, config_path="config.yaml"):
        self.log_file = None
        self.config = load_config(config_path)
        self.client = Client(self.config["api_config"]["endpoint"])
        self.setup_directories()
        self.setup_logging()

    def setup_directories(self):
        """创建必要的目录结构"""
        dirs_to_create = [
            self.config["paths"]["input_video_dir"],
            self.config["paths"]["input_audio_dir"],
            self.config["paths"]["output_dir"],
            self.config["paths"]["log_dir"],
        ]

        for directory in dirs_to_create:
            os.makedirs(directory, exist_ok=True)

    def setup_logging(self):
        """初始化日志系统"""
        self.log_file = os.path.join(self.config["paths"]["log_dir"], "processing.log")

    def validate_file(self, file_path, file_type="video"):
        """增强版文件验证"""
        # 获取配置参数
        allowed_types = self.config["file_settings"][
            "allowed_video_types" if file_type == "video" else "allowed_audio_types"
        ]
        max_size = self.config["file_settings"]["max_file_size"] * 1024 * 1024

        # 基础验证
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 文件类型验证
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in allowed_types:
            raise ValueError(
                f"不支持的文件类型 {file_ext}，允许的类型: {allowed_types}"
            )

        # 文件大小验证
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            raise ValueError(
                f"文件大小 {file_size / 1024 / 1024:.2f}MB 超过限制 {self.config['file_settings']['max_file_size']}MB"
            )

        return True

    def parse_api_result(self, result):
        """智能解析API返回结果"""
        # 记录原始数据结构
        self.log(f"API原始响应: {str(result)[:500]}...")

        # 类型基础判断
        if isinstance(result, tuple) or isinstance(result, list):
            if len(result) >= 2:
                return {"video_data": result[0], "processing_time": result[1]}
            return {"video_data": result[0]}
        elif isinstance(result, dict):
            return result
        else:
            raise ValueError(f"无法识别的API响应格式: {type(result)}")

    def get_video_path(self, data):
        """递归查找视频路径"""
        if isinstance(data, dict):
            for key in ["video", "path", "output"]:
                if key in data:
                    result = self.get_video_path(data[key])
                    if result:
                        return result
        elif isinstance(data, str) and data.endswith(
                tuple(self.config["file_settings"]["allowed_video_types"])
        ):
            return data
        return None

    def process_single_video(self, video_path, audio_path):
        """处理单个视频文件"""
        try:
            # 验证输入文件
            self.validate_file(video_path, "video")
            self.validate_file(audio_path, "audio")

            # 构建请求参数
            video_data = {"video": handle_file(video_path)}
            audio_data = handle_file(audio_path)

            # API调用
            result = self.client.predict(
                video=video_data,
                audio=audio_data,
                api_name=self.config["api_config"]["api_name"],
            )

            # 解析结果
            parsed_result = self.parse_api_result(result)
            output_video = self.get_video_path(parsed_result.get("video_data", {}))
            processing_time = parsed_result.get("processing_time", "N/A")

            if not output_video or not os.path.exists(output_video):
                raise ValueError("生成的视频文件路径无效")

            # 创建唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"output_{timestamp}{os.path.splitext(output_video)[1]}"
            dest_path = os.path.join(
                self.config["paths"]["output_dir"], output_filename
            )

            # 移动文件
            shutil.move(output_video, dest_path)

            # 记录日志
            self.log(f"成功生成视频 | 耗时: {processing_time} | 路径: {dest_path}")

            return dest_path, processing_time

        except Exception as e:
            self.log(f"处理失败 | 错误: {str(e)}", is_error=True)
            raise

    def log(self, message, is_error=False):
        """统一的日志记录"""
        log_entry = (
            f"[{datetime.now()}] {'ERROR' if is_error else 'INFO'} - {message}\n"
        )
        with open(self.log_file, "a") as f:
            f.write(log_entry)
        if is_error:
            print(f"\033[91m{log_entry}\033[0m")  # 红色错误输出
        else:
            print(log_entry)


if __name__ == "__main__":
    try:
        generator = VideoGenerator()

        # 示例使用 - 实际应用中可遍历目录处理多个文件
        sample_video = os.path.join(
            generator.config["paths"]["input_video_dir"], "video1.mp4"
        )
        sample_audio = os.path.join(
            generator.config["paths"]["input_audio_dir"], "audio1.wav"
        )

        output_path, time_cost = generator.process_single_video(
            sample_video, sample_audio
        )
        print(f"视频生成成功！\n输出路径: {output_path}\n处理耗时: {time_cost}")

    except Exception as e:
        print(f"主程序错误: {str(e)}")
