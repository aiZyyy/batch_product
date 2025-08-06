import json
import os
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
        self.filename_prefix = self.raw['filename_prefix']  # 统一前缀
        self.prompt_file_str = self.raw['prompt_file']

        # 固定种子值
        self.fixed_seed = 3857022511

        # 图像参数
        self.width = self.raw['width']
        self.height = self.raw['height']
        self.batch_size = self.raw['batch_size']
        self.max_filename_length = self.raw['max_filename_length']

        # 网络设置
        self.max_retries = self.raw['max_retries']
        self.request_timeout = self.raw['request_timeout']


# ----------------------------
# 节点发现模块（适配皮影戏工作流）
# ----------------------------
class WorkflowNodes:
    NODE_MAP = {
        'ksampler': 'KSampler',
        'prompt_pos': 'CLIPTextEncode',  # 节点1
        'negative_prompt': 'CLIPTextEncode',  # 节点48
        'latent_img': 'EmptySD3LatentImage',
        'save_image': 'SaveImage',
        'vae_loader': 'VAELoader',
        'model_loader': 'NunchakuFluxDiTLoader'
    }

    def __init__(self, workflow):
        self.nodes = {}
        for node_id, node_data in workflow.items():
            for key, value in self.NODE_MAP.items():
                if node_data['class_type'] == value:
                    # 特别区分正负提示词节点
                    if key == 'prompt_pos' and node_id == '1':
                        self.nodes[key] = node_id
                    elif key == 'negative_prompt' and node_id == '48':
                        self.nodes[key] = node_id
                    else:
                        self.nodes[key] = node_id

        # 完整性检查
        required_nodes = ['ksampler', 'prompt_pos', 'negative_prompt', 'latent_img', 'save_image']
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
class GenerationLogger:
    def __init__(self, log_dir):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_data = []

    def log(self, filename, prompt, seed, url):
        entry = {
            '关键词': prompt,
            '文件名': filename,
            '种子': seed,
            '图片地址': url,
            '日期': datetime.now().strftime("%Y-%m-%d")
        }
        self.log_data.append(entry)

    def save_to_excel(self, prompt_file_str):
        date_str = datetime.now().strftime("%Y-%m-%d") + "_" + prompt_file_str
        log_path = os.path.join(self.log_dir, f"{date_str}.xlsx")

        # 将当前日志数据转换为DataFrame
        new_df = pd.DataFrame(self.log_data)

        # 检查文件是否存在
        if os.path.exists(log_path):
            # 读取旧数据
            old_df = pd.read_excel(log_path)
            # 合并新旧数据
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        # 写入Excel文件（覆盖模式）
        with pd.ExcelWriter(log_path, engine='openpyxl', mode='w') as writer:
            combined_df.to_excel(writer, index=False, sheet_name='Logs')


# ----------------------------
# 主程序
# ----------------------------
def main():
    # 初始化配置
    config = AppConfig("resource/piyinxi.yaml")
    logger = GenerationLogger(config.raw['log_dir'])
    api = ComfyAPI(config)

    # 加载提示词文件 (1.txt)
    with open(config.prompt_file, 'r', encoding='utf-8') as f:
        prompts = [line.strip() for line in f if line.strip()]

    # 加载工作流模板
    with open(config.workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)

    # 定位关键节点
    node_finder = WorkflowNodes(workflow)
    prompt_node_id = node_finder.nodes['prompt_pos']  # 节点1
    negative_node_id = node_finder.nodes['negative_prompt']  # 节点48
    sampler_node_id = node_finder.nodes['ksampler']
    latent_node_id = node_finder.nodes['latent_img']
    save_node_id = node_finder.nodes['save_image']

    # 配置静态参数
    workflow[latent_node_id]['inputs'].update({
        'width': config.width,
        'height': config.height,
        'batch_size': config.batch_size
    })

    # 固定种子值
    fixed_seed = config.fixed_seed
    workflow[sampler_node_id]['inputs']['seed'] = fixed_seed

    # 处理每个提示词
    total = len(prompts)
    for idx, prompt in enumerate(prompts, 1):
        start_time = time.time()
        status = "FAILED"
        try:
            # 只替换节点1的文本输入
            workflow[prompt_node_id]['inputs']['text'] = prompt

            # 节点48保持不变（空字符串）
            workflow[negative_node_id]['inputs']['text'] = ""

            # 清理文件名并添加统一前缀
            clean_prefix = ''.join(c for c in prompt[:config.max_filename_length] if c.isalnum())
            file_name = f"{config.filename_prefix}_{clean_prefix}"
            workflow[save_node_id]['inputs']['filename_prefix'] = file_name

            # 生成图片URL（实际路径可能需要调整）
            url = f"{file_name}_00001_.png"

            # 发送请求
            success = api.send_prompt(workflow)
            status = "SUCCESS" if success else "FAILED"

        except Exception as e:
            print(f"处理提示词时发生错误: {str(e)}")

        # 记录日志
        elapsed = time.time() - start_time
        logger.log(file_name, prompt, fixed_seed, url)

        # 进度显示
        print(
            f"[{idx:03d}/{total:03d}] {status} | 耗时: {elapsed:.2f}s | 种子: {fixed_seed} | 提示词: {prompt[:30]}...")

        # 每处理10个提示词保存一次日志
        if idx % 10 == 0 or idx == total:
            logger.save_to_excel(config.prompt_file_str)


if __name__ == "__main__":
    main()