import json
import os
import sys
import time
import shutil
from datetime import datetime
from urllib import request, error
from copy import deepcopy

# ============================
# 配置
# ============================
COMFY_API_URL = "http://127.0.0.1:8188/prompt"
WORKFLOW_PATH = "workflow/ZImage-batch.json"   # 工作流文件路径
MAX_RETRIES = 3
REQUEST_TIMEOUT = 120

# 目标保存目录（绝对路径）
TARGET_OUTPUT_ROOT = r"F:\AI"

# ComfyUI 默认输出目录（可根据实际情况修改）
# 如果你不知道，可以留空，脚本会自动查找常见位置
COMFYUI_OUTPUT_DIR = r"D:\ai\ComfyUI-WorkFisher-V2\ComfyUI\output"   # 例如 r"C:\ComfyUI\output"

# 是否在生成后自动移动文件到目标目录
AUTO_MOVE_FILES = True


# ============================
# 网络请求模块
# ============================
class ComfyAPI:
    def __init__(self, endpoint, max_retries, timeout):
        self.endpoint = endpoint
        self.max_retries = max_retries
        self.timeout = timeout

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

# ============================
# 主程序
# ============================
def main():
    if len(sys.argv) < 2:
        print("用法: python zImage_batch.py <提示词文本文件>")
        sys.exit(1)

    txt_path = sys.argv[1]
    if not os.path.exists(txt_path):
        print(f"文件不存在: {txt_path}")
        sys.exit(1)

    # 加载工作流
    if not os.path.exists(WORKFLOW_PATH):
        print(f"工作流文件不存在: {WORKFLOW_PATH}")
        sys.exit(1)
    with open(WORKFLOW_PATH, 'r', encoding='utf-8') as f:
        template_workflow = json.load(f)

    # 读取整个文本文件
    with open(txt_path, 'r', encoding='utf-8') as f:
        prompts_multiline = f.read()

    # 深拷贝并修改工作流
    workflow = deepcopy(template_workflow)

    # 节点3：多行提示词
    if "3" not in workflow:
        print("错误: 工作流中缺少节点3")
        sys.exit(1)
    workflow["3"]["inputs"]["value"] = prompts_multiline

    # 节点8：保存路径 —— 使用相对路径，避免跨驱动器错误
    date_str = datetime.now().strftime("%Y-%m-%d")
    relative_save_path = f"AI/{date_str}/image/jt_"   # 相对路径，例如 "AI/2026-04-14"
    if "8" not in workflow:
        print("错误: 工作流中缺少节点8 (SaveImage)")
        sys.exit(1)
    workflow["8"]["inputs"]["filename_prefix"] = relative_save_path
    print(f"设置保存前缀为: {relative_save_path}")

    # 可选随机种子
    seed_node_id = "1:51"
    if seed_node_id in workflow and "inputs" in workflow[seed_node_id]:
        import random
        new_seed = random.randint(1, 2**32 - 1)
        workflow[seed_node_id]["inputs"]["seed"] = new_seed
        print(f"随机种子: {new_seed}")

    # 发送请求
    api = ComfyAPI(COMFY_API_URL, MAX_RETRIES, REQUEST_TIMEOUT)
    print(f"发送请求到 {COMFY_API_URL} ...")
    success = api.send_prompt(workflow)

    if success:
        print("工作流已提交。")
    else:
        print("提交失败，请检查 ComfyUI 服务状态。")

if __name__ == "__main__":
    main()