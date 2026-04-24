#!/usr/bin/env python3
"""
批量提交 Wan2.2 首尾帧视频生成工作流到 ComfyUI
输出视频路径格式: AI/yyyy-mm-dd/video/起始图片文件名.mp4
示例:
    python run_wan2.2.py --start_img jt__00008_.png --end_img jt__00009_.png --duration 5 --prompt "你的提示词"
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime
from urllib import request, error
from copy import deepcopy

# ---------------------------- 默认配置 ---------------------------------
DEFAULT_API_URL = "http://127.0.0.1:8188"
DEFAULT_WORKFLOW = "workflow/wan2.2-batch.json"   # 工作流文件路径（相对于脚本或绝对路径）
MAX_RETRIES = 3
REQUEST_TIMEOUT = 120


# ---------------------------- 网络请求模块 ---------------------------------
class ComfyAPI:
    def __init__(self, endpoint, max_retries=MAX_RETRIES, timeout=REQUEST_TIMEOUT):
        self.endpoint = endpoint.rstrip('/') + "/prompt"
        self.max_retries = max_retries
        self.timeout = timeout

    def send_prompt(self, workflow_data):
        data = json.dumps({"prompt": workflow_data}).encode('utf-8')
        req = request.Request(
            self.endpoint,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        for attempt in range(1, self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    if response.status == 200:
                        resp_data = json.loads(response.read().decode('utf-8'))
                        print(f"✅ 提交成功！prompt_id: {resp_data.get('prompt_id', 'unknown')}")
                        return True
                    else:
                        print(f"❌ 请求失败，状态码: {response.status}")
            except error.HTTPError as e:
                print(f"⚠️ HTTP错误 {e.code}: {e.reason}")
                try:
                    detail = e.read().decode('utf-8')
                    print(f"   详情: {detail[:200]}")
                except:
                    pass
            except error.URLError as e:
                print(f"⚠️ 网络错误: {str(e)}")
            time.sleep(2 ** attempt)
        return False


# ---------------------------- 主程序 ---------------------------------
def find_image_in_subdir(batch_id, filename, base_dir):
    """在 AI/{date}/image/{batch_id}/ 下查找图片，返回完整路径或原文件名（让ComfyUI自己找）"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    subdir = os.path.join(base_dir, f"AI/{date_str}/image/{batch_id}")
    candidate = os.path.join(subdir, filename)
    if os.path.exists(candidate):
        return candidate
    return filename  # 找不到就返回原名，让ComfyUI按默认逻辑找


def main():
    parser = argparse.ArgumentParser(description="修改 Wan2.2 工作流并提交到 ComfyUI")
    parser.add_argument("--start_img", required=True, help="起始帧图片文件名 (如 jt__00008_.png)")
    parser.add_argument("--end_img", required=True, help="结束帧图片文件名 (如 jt__00009_.png)")
    parser.add_argument("--duration", type=int, required=True, help="视频长度 (秒)")
    parser.add_argument("--prompt", required=True, help="正向提示词文本")
    parser.add_argument("--batch-id", default="", help="批次/选题ID（如A1），用于定位图片子目录")
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW, help=f"工作流 JSON 文件路径 (默认 {DEFAULT_WORKFLOW})")
    parser.add_argument("--api_url", default=DEFAULT_API_URL, help=f"ComfyUI API 地址 (默认 {DEFAULT_API_URL})")
    args = parser.parse_args()

    # 1. 加载工作流模板
    if not os.path.exists(args.workflow):
        print(f"❌ 工作流文件不存在: {args.workflow}")
        sys.exit(1)
    with open(args.workflow, 'r', encoding='utf-8') as f:
        template = json.load(f)

    # 2. 深拷贝并修改节点
    workflow = deepcopy(template)

    # 图片路径处理：按 batch_id 定位到子目录
    if args.batch_id:
        base_dir = r"D:\ai\ComfyUI-WorkFisher-V2\ComfyUI\output"
        start_img = find_image_in_subdir(args.batch_id, args.start_img, base_dir)
        end_img = find_image_in_subdir(args.batch_id, args.end_img, base_dir)
    else:
        start_img = args.start_img
        end_img = args.end_img

    # 修改节点224 (起始帧)
    if "224" not in workflow:
        print("❌ 工作流中缺少节点224 (LoadImage)")
        sys.exit(1)
    workflow["224"]["inputs"]["image"] = start_img
    print(f"📷 起始帧: {start_img}")

    # 修改节点243 (结束帧)
    if "243" not in workflow:
        print("❌ 工作流中缺少节点243 (LoadImage)")
        sys.exit(1)
    workflow["243"]["inputs"]["image"] = end_img
    print(f"📷 结束帧: {end_img}")

    # 修改节点316 (视频秒数)
    if "316" not in workflow:
        print("❌ 工作流中缺少节点316 (Int)")
        sys.exit(1)
    workflow["316"]["inputs"]["Number"] = args.duration
    print(f"⏱️ 视频时长: {args.duration} 秒")

    # 修改节点227 (正向提示词)
    if "227" not in workflow:
        print("❌ 工作流中缺少节点227 (CLIPTextEncode)")
        sys.exit(1)
    workflow["227"]["inputs"]["text"] = args.prompt
    print(f"📝 提示词: {args.prompt[:80]}...")

    # 修改节点237的输出文件名前缀: AI/日期/video/起始图片文件名
    if "237" not in workflow:
        print("❌ 工作流中缺少节点237 (VideoCombine)")
        sys.exit(1)

    # 提取起始图片文件名（不含扩展名）
    start_basename = os.path.splitext(os.path.basename(args.start_img))[0]
    date_str = datetime.now().strftime("%Y-%m-%d")
    if args.batch_id:
        video_prefix = f"AI/{date_str}/video/{args.batch_id}/{start_basename}"
    else:
        video_prefix = f"AI/{date_str}/video/{start_basename}"
    workflow["237"]["inputs"]["filename_prefix"] = video_prefix
    print(f"🎬 输出视频前缀: {video_prefix}")

    # 3. 提交到 ComfyUI
    api = ComfyAPI(args.api_url)
    print(f"\n🚀 提交工作流到 {args.api_url} ...")
    success = api.send_prompt(workflow)

    if success:
        print("🎉 工作流已提交，请查看 ComfyUI 输出。")
    else:
        print("💥 提交失败，请检查 ComfyUI 是否正常运行且工作流无缺失节点。")
        sys.exit(1)


if __name__ == "__main__":
    main()