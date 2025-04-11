# 新增导入
import re  # 添加正则模块

import pandas as pd


class AppConfig:
    def __init__(self, config_path):
        # ...原有代码不变...
        # 新增配置项
        self.excel_file = self.raw.get('excel_file', 'data.xlsx')  # Excel文件名
        self.date_folder = datetime.now().strftime("%Y-%m-%d")  # 新增日期目录


# 修改主程序结构
def main():
    config = AppConfig("config.yaml")
    api = ComfyAPI(config)

    # 创建日期目录
    date_dir = os.path.join(config.filename_prefix, config.date_folder)
    os.makedirs(date_dir, exist_ok=True)

    # 读取Excel数据
    try:
        df = pd.read_excel(config.excel_file, engine='openpyxl')
        required_columns = ['lora', '关键词']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Excel缺少必要列，必须包含：{required_columns}")
    except Exception as e:
        print(f"读取Excel失败: {str(e)}")
        return

    # 新增文件名清理函数
    def sanitize_filename(text, max_length=15):
        cleaned = re.sub(r'[\\/*?:"<>|]', '', text)
        return cleaned.replace(' ', '_')[:max_length]

    # 处理数据
    for index, row in df.iterrows():
        start_time = time.time()
        status = "FAILED"
        seed = None
        file_name = None

        try:
            loraName = str(row['lora']).strip()
            prompt = str(row['关键词']).strip()

            if not loraName or not prompt:
                print(f"第{index + 1}行数据不完整，跳过处理")
                continue

            # 动态创建Lora目录
            save_dir = os.path.join(date_dir, loraName)
            os.makedirs(save_dir, exist_ok=True)

            # 生成唯一文件名
            seed = random.randint(*config.seed_range)
            clean_prefix = sanitize_filename(prompt)
            file_name = f"{clean_prefix}_{seed}.png"

            # 更新工作流节点
            nodes['lora_loader']['inputs']['lora_name'] = loraName
            nodes['prompt_pos']['inputs']['text'] = prompt
            nodes['ksampler']['inputs']['seed'] = seed
            nodes['save_image']['inputs']['filename_prefix'] = os.path.join(save_dir, clean_prefix)

            # 发送请求并更新数据
            if api.send_prompt(workflow):
                df.at[index, '文件名'] = file_name
                df.at[index, '种子'] = seed
                df.at[index, '日期'] = datetime.now().strftime("%Y-%m-%d")
                status = "SUCCESS"

            # 每处理10条保存一次进度
            if index % 10 == 0:
                df.to_excel(config.excel_file, index=False, engine='openpyxl')

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"第{index + 1}行处理失败: {error_msg}")
            df.at[index, '错误信息'] = error_msg
        finally:
            elapsed = time.time() - start_time
            print(f"[{index + 1}/{len(df)}] {status} | 耗时: {elapsed:.2f}s")

    # 最终保存Excel
    try:
        df.to_excel(config.excel_file, index=False, engine='openpyxl')
        print(f"处理完成，结果已保存至: {config.excel_file}")
    except Exception as e:
        print(f"保存Excel失败: {str(e)}")
