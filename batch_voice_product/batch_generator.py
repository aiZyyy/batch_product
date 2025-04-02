import shutil
import yaml
import logging
from datetime import datetime
from pathlib import Path
from gradio_client import Client, handle_file

class BatchTTSEngine:
    def __init__(self, config_path="config.yaml"):
        self.load_config(config_path)
        self.setup_logging()
        self.client = Client(self.config["api"]["endpoint"])

    def load_config(self, config_path):
        with open(config_path, encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 路径预处理
        Path(self.config["paths"]["output_dir"]).mkdir(parents=True, exist_ok=True)
        Path(self.config["logging"]["log_dir"]).mkdir(parents=True, exist_ok=True)

    def setup_logging(self):
        log_config = self.config["logging"]
        log_file = Path(log_config["log_dir"]) / "generation.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def generate_filename(self, audio_path, text):
        """生成规范化的文件名"""
        audio_stem = Path(audio_path).stem[:5]  # 取文件名前10字符
        text_stem = text[:5].strip().replace(" ", "_")  # 取文本前15字符
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{audio_stem}_{text_stem}_{timestamp}.wav"

    def process_single(self, audio_path, text):
        """处理单个音频文本组合"""
        try:
            start_time = datetime.now()
            
            # 生成输出路径
            output_path = Path(self.config["paths"]["output_dir"]) / self.generate_filename(audio_path, text)
            
            # 调用API
            result = self.client.predict(
                aux_ref_audio_paths=[],
                text=text,
                text_lang=self.config["generation"]["text_lang"],
                ref_audio_path=handle_file(audio_path),
                prompt_text="",  # 自动识别
                prompt_lang=self.config["generation"]["prompt_lang"],
                speed_factor=self.config["generation"]["speed_factor"],
                top_k=self.config["generation"]["top_k"],
                sample_steps=self.config["generation"]["sample_steps"],
                api_name="/inference"
            )
            
            # 保存结果
            self.save_audio(result[0], output_path)
            
            # 记录日志
            time_cost = (datetime.now() - start_time).total_seconds()
            logging.info(f"生成成功 | 耗时: {time_cost:.2f}s | 路径: {output_path}")
            
            return True
        except Exception as e:
            logging.error(f"生成失败 | 音频: {audio_path} | 文本: {text} | 错误: {str(e)}")
            return False

    def save_audio(self, file_path_str, output_path):
        """保存音频文件"""
        # 直接复制文件
        shutil.copy(file_path_str, output_path)

    def run_batch(self):
        """执行批量生成"""
        logging.info("===== 开始批量生成 =====")
        
        audio_paths = self.config["paths"]["audio_inputs"]
        texts = self.config["paths"]["text_inputs"]
        
        total = len(audio_paths) * len(texts)
        success = 0
        
        for audio in audio_paths:
            if not Path(audio).exists():
                logging.warning(f"音频文件不存在: {audio}")
                continue
                
            for text in texts:
                if self.process_single(audio, text):
                    success += 1
        
        logging.info(f"===== 生成完成 | 成功率: {success}/{total} =====")

if __name__ == "__main__":
    engine = BatchTTSEngine()
    engine.run_batch()