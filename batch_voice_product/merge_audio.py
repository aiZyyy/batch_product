import subprocess
import sys

"""
Merge TTS audio clips into a single MP3.
Usage: python merge_audio.py <prefix> <num_clips> [output_dir]
Example: python merge_audio.py "2026-04-22-11_" 12 "D:\ai\...\voice\"
"""

import os

if len(sys.argv) < 3:
    print("[FAIL] Usage: python merge_audio.py <prefix> <num_clips> [output_dir]")
    sys.exit(1)

prefix = sys.argv[1]
num_clips = int(sys.argv[2])
output_dir = sys.argv[3] if len(sys.argv) > 3 else os.getcwd()

# Build concat list
concat_file = os.path.join(output_dir, "concat.txt")
with open(concat_file, "w", encoding="ascii") as f:
    for i in range(1, num_clips + 1):
        f.write(f"file '{prefix}{i:05d}.mp3'\n")

merged_file = os.path.join(output_dir, f"{prefix}merged.mp3")
result = subprocess.run(
    ["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", merged_file],
    capture_output=True,
    text=True
)
if result.returncode != 0:
    print(f"[FAIL] ffmpeg error: {result.stderr}")
    sys.exit(1)
else:
    print(f"[OK] Merged {num_clips} clips -> {merged_file}")
