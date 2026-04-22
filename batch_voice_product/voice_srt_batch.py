#!/usr/bin/env python3
"""
Submit TTS workflow to ComfyUI
Usage:
    python voice_srt_batch.py --audio xinzhongzhicheng.WAV --prompt "your text"
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime
from urllib import request, error
from copy import deepcopy

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
                        print(f"[OK] Submit success! prompt_id: {resp_data.get('prompt_id', 'unknown')}")
                        return True
                    else:
                        print(f"[FAIL] Request failed, status: {response.status}")
            except error.HTTPError as e:
                print(f"[WARN] HTTP error {e.code}: {e.reason}")
                try:
                    detail = e.read().decode('utf-8')
                    print(f"   Detail: {detail[:200]}")
                except:
                    pass
            except error.URLError as e:
                print(f"[WARN] Network error: {str(e)}")
            time.sleep(2 ** attempt)
        return False

def main():
    parser = argparse.ArgumentParser(description="Submit TTS workflow to ComfyUI")
    parser.add_argument("--audio", required=True, help="Audio filename (in ComfyUI input)")
    parser.add_argument("--prompt", required=True, help="TTS text")
    parser.add_argument("--output_time", help="Custom time suffix YYYY-MM-DD-HH")
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW, help=f"Workflow JSON path")
    parser.add_argument("--api_url", default=DEFAULT_API_URL, help=f"ComfyUI API URL")
    args = parser.parse_args()

    if args.output_time:
        time_suffix = args.output_time
    else:
        now = datetime.now()
        time_suffix = f"{now.strftime('%Y-%m-%d')}-{now.hour:02d}"
    date_str = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(args.workflow):
        print(f"[FAIL] Workflow file not found: {args.workflow}")
        sys.exit(1)
    with open(args.workflow, 'r', encoding='utf-8') as f:
        template = json.load(f)

    workflow = deepcopy(template)

    if "10" not in workflow:
        print("[FAIL] Node 10 (LoadAudio) missing in workflow")
        sys.exit(1)
    workflow["10"]["inputs"]["audio"] = args.audio
    print(f"[AUDIO] Input: {args.audio}")

    if "9" not in workflow:
        print("[FAIL] Node 9 (CR Prompt Text) missing in workflow")
        sys.exit(1)
    workflow["9"]["inputs"]["prompt"] = args.prompt
    print(f"[PROMPT] TTS: {args.prompt[:50]}...")

    if "11" not in workflow:
        print("[FAIL] Node 11 (SaveAudioMP3) missing")
        sys.exit(1)
    audio_prefix = f"AI/{date_str}/voice/{time_suffix}_"
    workflow["11"]["inputs"]["filename_prefix"] = audio_prefix
    print(f"[AUDIO] Output prefix: {audio_prefix}")

    if "67" not in workflow:
        print("[FAIL] Node 67 (SaveText) missing")
        sys.exit(1)
    srt_filename = f"AI/{date_str}/srt/{time_suffix}.srt"
    workflow["67"]["inputs"]["file"] = srt_filename
    print(f"[SRT] Output file: {srt_filename}")

    api = ComfyAPI(args.api_url)
    print(f"\n[SUBMIT] Submitting to {args.api_url} ...")
    success = api.send_prompt(workflow)

    if success:
        print("[DONE] Workflow submitted, check ComfyUI output.")
    else:
        print("[FAIL] Submit failed, check ComfyUI status.")
        sys.exit(1)

if __name__ == "__main__":
    main()
