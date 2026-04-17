#!/usr/bin/env python3
"""
提交语音TTS工作流到ComfyUI
用法:
    python voice_tts.py --audio 涨粉配音-男_钱追属狗人，踩了_094016.wav --prompt "你的TTS文本"
可选:
    --output_time "14-30"  # 自定义时间，默认当前小时-分钟
    --workflow voice_srt_batch.json
    --api_url http://127.0.0.1:8188
"""

import argparse
import json
import os
import sys
import time
from copy import deepcopy
from datetime import datetime
from urllib import request, error

DEFAULT_API_URL = "http://127.0.0.1:8188"
DEFAULT_WORKFLOW = "workflow/voice_srt_batch.json"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 120


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


def main():
    parser = argparse.ArgumentParser(description="修改语音TTS工作流并提交到ComfyUI")
    parser.add_argument("--audio", required=True, help="输入音频文件名 (位于ComfyUI input目录下)")
    parser.add_argument("--prompt", required=True, help="TTS生成文本")
    parser.add_argument("--output_time", help="自定义输出时间后缀，格式 HH-MM (默认当前时间)")
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW, help=f"工作流JSON路径 (默认 {DEFAULT_WORKFLOW})")
    parser.add_argument("--api_url", default=DEFAULT_API_URL, help=f"ComfyUI API地址 (默认 {DEFAULT_API_URL})")
    args = parser.parse_args()

    # 确定时间后缀
    if args.output_time:
        time_suffix = args.output_time
    else:
        now = datetime.now()
        time_suffix = f"{now.hour:02d}-{now.minute:02d}"
    date_str = datetime.now().strftime("%Y-%m-%d")

    # 加载工作流
    if not os.path.exists(args.workflow):
        print(f"❌ 工作流文件不存在: {args.workflow}")
        sys.exit(1)
    with open(args.workflow, 'r', encoding='utf-8') as f:
        template = json.load(f)

    workflow = deepcopy(template)

    # 修改节点10 (LoadAudio)
    if "10" not in workflow:
        print("❌ 工作流中缺少节点10 (LoadAudio)")
        sys.exit(1)
    workflow["10"]["inputs"]["audio"] = args.audio
    print(f"🎵 输入音频: {args.audio}")

    # 修改节点9 (CR Prompt Text)
    if "9" not in workflow:
        print("❌ 工作流中缺少节点9 (CR Prompt Text)")
        sys.exit(1)
    workflow["9"]["inputs"]["prompt"] = args.prompt
    print(f"📝 TTS文本: {args.prompt[:50]}...")

    # 修改节点11 (SaveAudioMP3) 的 filename_prefix
    if "11" not in workflow:
        print("❌ 工作流中缺少节点11 (SaveAudioMP3)")
        sys.exit(1)
    audio_prefix = f"AI/{date_str}/voice/{time_suffix}_"
    workflow["11"]["inputs"]["filename_prefix"] = audio_prefix
    print(f"🎧 音频输出前缀: {audio_prefix}")

    # 修改节点67 (SaveText) 的 file
    if "67" not in workflow:
        print("❌ 工作流中缺少节点67 (SaveText)")
        sys.exit(1)
    srt_filename = f"AI/{date_str}/srt/{time_suffix}.srt"
    workflow["67"]["inputs"]["file"] = srt_filename
    print(f"📄 SRT输出文件: {srt_filename}")

    # 提交
    api = ComfyAPI(args.api_url)
    print(f"\n🚀 提交工作流到 {args.api_url} ...")
    success = api.send_prompt(workflow)

    if success:
        print("🎉 工作流已提交，请查看ComfyUI输出。")
    else:
        print("💥 提交失败，请检查ComfyUI状态。")
        sys.exit(1)


if __name__ == "__main__":
    main()
