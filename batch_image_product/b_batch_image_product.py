import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from urllib import request, error

import pandas as pd
import yaml


# ----------------------------
# 配置加载模块
# ----------------------------
class AppConfig:
    def __init__(self, config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.raw = yaml.safe_load(f)

        # 路径配置
        self.workflow_path = Path("workflow/" + self.raw['workflow_path'])
        self.prompt_file = Path("prompts/" + self.raw['prompt_file'])
        self.prompt_file_str = self.raw['prompt_file']
        self.lora_active_list = Path("lora/" + self.raw['lora_active_list'])
        self.filename_prefix = self.raw['prompt_file']

        # 模型参数
        self.checkpoint = self.raw['checkpoint']
        # self.lora_name = self.raw['lora_name']

        self.seed_range = tuple(self.raw['seed_range'])

        # 图像参数
        self.width = self.raw['width']
        self.height = self.raw['height']
        self.batch_size = self.raw['batch_size']
        # self.filename_prefix = self.raw['filename_prefix']
        self.max_filename_length = self.raw['max_filename_length']

        # 网络设置
        self.max_retries = self.raw['max_retries']
        self.request_timeout = self.raw['request_timeout']


# ----------------------------
# 节点发现模块
# ----------------------------
class WorkflowNodes:
    NODE_MAP = {
        'ksampler': 'KSampler',
        'checkpoint_loader': 'CheckpointLoaderSimple',
        'lora_loader': 'LoraLoader',
        'latent_img': 'EmptyLatentImage',
        'prompt_pos': 'CLIPTextEncode',
        'save_image': 'SaveImage'
    }

    def __init__(self, workflow):
        self.nodes = {}
        for node_id, node_data in workflow.items():
            for key, value in self.NODE_MAP.items():
                if node_data['class_type'] == value:
                    self.nodes[key] = node_data
                    break

        # 完整性检查
        required_nodes = ['ksampler', 'checkpoint_loader', 'lora_loader']
        missing = [n for n in required_nodes if n not in self.nodes]
        if missing:
            raise ValueError(f"缺少关键节点: {missing}")


# ----------------------------
# 网络请求模块（带重试）
# ----------------------------
class ComfyAPI:
    def __init__(self, config):
        self.endpoint = "http://127.0.0.1:8188/prompt"
        self.max_retries = config.max_retries
        self.timeout = config.request_timeout

    def send_prompt(self, workflow_data):
        data = json.dumps({"prompt": workflow_data}).encode('utf-8')
        req = request.Request(
            self.endpoint,
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    if response.status == 200:
                        return True
                    print(f"请求失败，状态码: {response.status}")
            except error.URLError as e:
                print(f"尝试 {attempt}/{self.max_retries} 失败: {str(e)}")
                time.sleep(2 ** attempt)

        return False


# ----------------------------
# 日志模块
# ----------------------------
# class GenerationLogger:
#     def __init__(self, log_path):
#         self.log_path = log_path
#         if not os.path.exists(log_path):
#             with open(log_path, 'w', encoding='utf-8') as f:
#                 f.write("lora,filename,prompt,seed,timestamp,status\n")
#
#     def log(self, lora, filename, prompt, seed, status):
#         # prompt_hash = hash(prompt) % 1000000  # 生成短哈希
#         entry = f"{lora},{filename},{prompt},{seed},{datetime.now().strftime("%Y-%m-%d")},{status}\n"
#         with open(self.log_path, 'a', encoding='utf-8') as f:
#             f.write(entry)
class GenerationLogger:
    def __init__(self, log_dir):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_data = []

    def log(self, lora, filename, prompt, seed, url):
        entry = {
            'lora': lora,
            '关键词': prompt,
            '文件名': filename,
            '种子': seed,
            '图片地址': url,
            '日期': datetime.now().strftime("%Y-%m-%d")
        }
        self.log_data.append(entry)

    def save_to_excel(self, prompt_file_str):
        date_str = datetime.now().strftime("%Y-%m-%d") + "_" + prompt_file_str + "_"
        log_path = os.path.join(self.log_dir, f"{date_str}.xlsx")
        df = pd.DataFrame(self.log_data)
        df.to_excel(log_path, index=False)

    # ----------------------------


# 主程序
# ----------------------------
def main():
    # 初始化配置
    config = AppConfig("resource/config.yaml")
    logger = GenerationLogger(config.raw['log_dir'])
    api = ComfyAPI(config)

    # 加载提示词
    with open(config.prompt_file, 'r', encoding='utf-8') as f:
        prompts = [line.strip() for line in f if line.strip()]

    # 加载lora列表名称
    with open(config.lora_active_list, 'r', encoding='utf-8') as f:
        loras = [line.strip() for line in f if line.strip()]

    # 加载工作流模板
    with open(config.workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)

    nodes = WorkflowNodes(workflow).nodes

    # 配置静态参数
    nodes['checkpoint_loader']['inputs']['ckpt_name'] = config.checkpoint
    # nodes['lora_loader']['inputs']['lora_name'] = config.lora_name
    nodes['latent_img']['inputs'].update({
        'width': config.width,
        'height': config.height,
        'batch_size': config.batch_size
    })

    for idx, loraName in enumerate(loras, 1):
        nodes['lora_loader']['inputs']['lora_name'] = loraName
        # 处理每个提示词
        total = len(prompts)
        for idx, prompt in enumerate(prompts, 1):
            start_time = time.time()
            status = "FAILED"
            try:
                # 动态参数设置
                nodes['prompt_pos']['inputs']['text'] = prompt
                seed = random.randint(*config.seed_range)
                nodes['ksampler']['inputs']['seed'] = seed

                # 清理文件名
                clean_prefix = ''.join(c for c in prompt[:config.max_filename_length] if c.isalnum())
                file_name = f"{clean_prefix}" + str(seed)
                nodes['save_image']['inputs']['filename_prefix'] = \
                    f"{config.filename_prefix}" + "/" + f"{loraName}" + "/" + file_name

                url = nodes['save_image']['inputs']['filename_prefix'] + ".png"
                # 发送请求
                success = api.send_prompt(workflow)
                status = "SUCCESS" if success else "FAILED"

            except Exception as e:
                print(f"处理提示词时发生错误: {str(e)}")

            # 记录日志
            elapsed = time.time() - start_time
            logger.log(loraName, file_name, prompt, seed, url)

            # 进度显示
            print(f"[{idx:03d}/{total:03d}] {status} | 耗时: {elapsed:.2f}s | 种子: {seed}")

            # 保存日志到 Excel
            logger.save_to_excel(config.prompt_file_str)


if __name__ == "__main__":
    main()
