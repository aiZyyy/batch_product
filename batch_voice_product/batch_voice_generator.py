import logging
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd
import yaml
from gradio_client import Client, handle_file


def _load_config(config_path):
    """加载配置文件"""
    with open(config_path, encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 路径标准化
    config["excel"]["path"] = Path(config["excel"]["path"])
    config["paths"]["output_root"] = Path(config["paths"]["output_root"])
    config["paths"]["log"] = Path(config["paths"]["log"])
    return config


def save_audio(file_path_str, output_path):
    """保存音频文件"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    """保存音频文件"""
    # 直接复制文件
    shutil.copy(file_path_str['value'], output_path)


class ExcelTTSGenerator:
    def __init__(self, config_path="resource/config_excel.yaml"):
        self.config = _load_config(config_path)
        self.client = Client(self.config["api"]["endpoint"])
        self._setup_logging()

    def _setup_logging(self):
        """配置日志系统"""
        log_dir = self.config["paths"]["log"]
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "processing.log"
        logging.basicConfig(
            level=self.config["logging"]["level"],
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                RotatingFileHandler(
                    log_dir / "processing.log",
                    maxBytes=self.config["logging"]["max_bytes"],
                    backupCount=self.config["logging"]["backup_count"]
                ),
                logging.StreamHandler(),
                logging.FileHandler(log_file, encoding='utf-8'),
            ]
        )

    def generate_output_path(self, row, process_time):
        """生成包含日期的输出路径"""
        date_str = process_time.strftime(self.config["paths"]["date_format"])
        custom_prefix = row.get("负责人", "")

        path_parts = [
            self.config["paths"]["output_root"],
            date_str,
            custom_prefix,
            f"{Path(row['参考音频']).stem}_{Path(row['合成文本']).stem[:8]}_{process_time:%H%M%S}.wav"
        ]

        return Path().joinpath(*filter(None, path_parts))

    def process_excel(self):
        """处理Excel工作流"""
        try:
            # 读取Excel
            df = pd.read_excel(
                self.config["excel"]["path"],
                sheet_name=self.config["excel"]["sheet"],
                engine='openpyxl'
            )

            # 添加结果列
            if "输出音频" not in df.columns:
                df["输出音频"] = None
            if "日期" not in df.columns:
                df["日期"] = None

            # 处理每条记录
            for idx, row in df.iterrows():
                process_time = datetime.now()
                output_path = self.generate_output_path(row, process_time)
                input_root = self.config["paths"]["input_root"]

                try:
                    # # ==== 新增音色选择逻辑 ====
                    # self.client.predict(api_name="/gen_single")

                    # ==== 新API调用方式 ====
                    voice_path = Path(input_root) / row["参考音频"]  # 使用Path处理路径
                    result = self.client.predict(
                        prompt=handle_file(str(voice_path)),  # 处理音频路径
                        text=row["合成文本"],
                        infer_mode="批次推理",
                        max_text_tokens_per_sentence=160,
                        sentences_bucket_max_size=4,
                        param_5=True,
                        param_6=0.8,
                        param_7=30,
                        param_8=1,
                        param_9=1,
                        param_10=3,
                        param_11=10,
                        param_12=600,
                        api_name="/gen_single"
                    )

                    # ==== 保存结果 ====
                    save_audio(result, output_path)  # 直接使用result
                    df.at[idx, "输出音频"] = str(output_path)
                    df.at[idx, "日期"] = process_time.strftime(self.config["paths"]["date_format"])

                    logging.info(f"成功处理行 {idx + 1}")

                except Exception as e:
                    logging.error(f"行 {idx + 1} 错误: {str(e)}")
                    df.at[idx, "输出音频"] = f"错误: {str(e)}"

            # 保存结果
            self._save_excel(df)

        except Exception as e:
            logging.critical(f"全局错误: {str(e)}")
            raise

    def _save_excel(self, df):
        """保存结果到Excel"""
        with pd.ExcelWriter(
                self.config["excel"]["path"],
                engine='openpyxl',
                mode='a',
                if_sheet_exists='replace'
        ) as writer:
            df.to_excel(
                writer,
                sheet_name=self.config["excel"]["sheet"],
                index=False
            )


if __name__ == "__main__":
    generator = ExcelTTSGenerator()
    generator.process_excel()
