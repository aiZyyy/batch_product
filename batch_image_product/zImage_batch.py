import json
import os
import sys
import time
import shutil
import random
from datetime import datetime
from urllib import request, error
from copy import deepcopy

COMFY_API_URL = "http://127.0.0.1:8188/prompt"
WORKFLOW_PATH = "workflow/ZImage-batch.json"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 120
COMFYUI_OUTPUT_DIR = r"D:\ai\ComfyUI-WorkFisher-V2\ComfyUI\output"
AUTO_MOVE_FILES = True

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
                    print(f"[FAIL] Request failed, status: {response.status}")
            except error.URLError as e:
                print(f"[RETRY] Attempt {attempt}/{self.max_retries} failed: {str(e)}")
                time.sleep(2 ** attempt)
        return False

def main():
    parser.add_argument("--batch-id", required=True, help="批次/选题ID（如A1/B3），用于输出子目录隔离")
    parser.add_argument("prompt_file", help="提示词文本文件路径")

    args = parser.parse_args()
    batch_id = args.batch_id
    txt_path = args.prompt_file
    if not os.path.exists(txt_path):
        print(f"[FAIL] File not found: {txt_path}")
        sys.exit(1)

    if not os.path.exists(WORKFLOW_PATH):
        print(f"[FAIL] Workflow file not found: {WORKFLOW_PATH}")
        sys.exit(1)
    with open(WORKFLOW_PATH, 'r', encoding='utf-8') as f:
        template_workflow = json.load(f)

    with open(txt_path, 'r', encoding='utf-8') as f:
        prompts_multiline = f.read()

    workflow = deepcopy(template_workflow)

    if "3" not in workflow:
        print("[FAIL] Node 3 missing in workflow")
        sys.exit(1)
    workflow["3"]["inputs"]["value"] = prompts_multiline

    date_str = datetime.now().strftime("%Y-%m-%d")
    relative_save_path = f"AI/{date_str}/{batch_id}/image/jt_"
    if "8" not in workflow:
        print("[FAIL] Node 8 (SaveImage) missing in workflow")
        sys.exit(1)
    workflow["8"]["inputs"]["filename_prefix"] = relative_save_path
    print(f"[OK] Output prefix: {relative_save_path}")
    print(f"[OK] Batch ID: {batch_id}")

    seed_node_id = "1:51"
    if seed_node_id in workflow and "inputs" in workflow[seed_node_id]:
        new_seed = random.randint(1, 2**32 - 1)
        workflow[seed_node_id]["inputs"]["seed"] = new_seed
        print(f"[OK] Random seed: {new_seed}")

    api = ComfyAPI(COMFY_API_URL, MAX_RETRIES, REQUEST_TIMEOUT)
    print(f"[SUBMIT] Sending to {COMFY_API_URL} ...")
    success = api.send_prompt(workflow)

    if success:
        print("[DONE] Workflow submitted.")
    else:
        print("[FAIL] Submit failed, check ComfyUI status.")

if __name__ == "__main__":
    main()
