# -*- coding: utf-8 -*-
"""
图像批量生成工具 - 增强版
功能：
1. 遍历指定文件夹中的所有图片
2. 自动替换工作流中的关键参数
3. 随机选择LORA模型
4. 动态生成输出路径
"""

import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from urllib import request, error

import yaml


class AppConfig:
    def __init__(self, config_path):
        """初始化并加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.raw = yaml.safe_load(f)  # 加载YAML配置

        # 路径配置
        self.workflow_path = Path("workflow/" + self.raw['workflow_path'])
        self.people = self.raw['people']
        self.batch_size = self.raw['batch_size']
        self.image_folder = Path(self.raw['image_folder'])  # 图片文件夹路径
        self.lora_names = self.raw['lora_names']  # LORA模型名称列表
        self.max_retries = self.raw['max_retries']
        self.request_timeout = self.raw['request_timeout']
        # 日期目录
        self.date_folder = datetime.now().strftime("%Y-%m-%d")


class ComfyAPI:
    def __init__(self, config):
        """初始化API连接参数"""
        self.endpoint = "http://127.0.0.1:8188/prompt"
        self.max_retries = config.max_retries
        self.timeout = config.request_timeout

    def send_prompt(self, workflow_data):
        """发送生成请求到ComfyUI"""
        data = json.dumps({"prompt": workflow_data}).encode('utf-8')
        req = request.Request(
            self.endpoint,
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        # 带指数退避的重试机制
        for attempt in range(1, self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    if response.status == 200:
                        return True
                    print(f"请求失败，状态码: {response.status}")
            except error.URLError as e:
                print(f"尝试 {attempt}/{self.max_retries} 失败: {str(e)}")
                time.sleep(2 ** attempt)  # 指数退避等待
        return False


def sanitize_filename(text, max_length=15):
    """清理文件名中的非法字符"""
    cleaned = re.sub(r'[\\/*?:"<>|]', '', text)
    cleaned = cleaned.replace(' ', '_')[:max_length]
    return cleaned


def process_images(config, api):
    """处理所有图片并发送到ComfyUI"""
    # 获取所有图片文件
    image_files = [
        f for f in config.image_folder.iterdir()
        if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']
    ]

    if not image_files:
        print(f"在 {config.image_folder} 中没有找到图片文件")
        return

    print(f"找到 {len(image_files)} 张图片，开始处理...")

    # 加载工作流模板
    with open(config.workflow_path, 'r', encoding='utf-8') as f:
        base_workflow = json.load(f)

    for img_path in image_files:
        try:
            # 复制工作流以避免修改原始模板
            workflow = json.loads(json.dumps(base_workflow))

            # 获取图片基本信息
            img_name = img_path.stem
            sanitized_name = sanitize_filename(img_name)

            # 随机选择LORA模型
            lora_name = random.choice(config.lora_names)
            sanitized_lora = sanitize_filename(lora_name.split('.')[0])

            # 更新工作流节点
            # 节点288: 图片路径
            workflow["288"]["inputs"]["paths"] = str(img_path.resolve())

            workflow["294"]["inputs"]["batch_size"] = config.batch_size

            # 节点293: LORA名称
            workflow["293"]["inputs"]["lora_name"] = lora_name

            # 节点291: 当前日期
            workflow["291"]["inputs"]["String"] = config.people + "_" + config.date_folder

            # 节点214: 原图路径
            workflow["214"]["inputs"]["String"] = f"原图/{sanitized_lora}/{sanitized_name}"

            # 节点216: 透明底路径
            workflow["216"]["inputs"]["String"] = f"透明/{sanitized_lora}/{sanitized_name}"

            # 发送处理请求
            print(f"处理图片: {img_path.name} | LORA: {lora_name}")
            if api.send_prompt(workflow):
                print(f"成功发送: {img_path.name}")
            else:
                print(f"处理失败: {img_path.name}")

        except Exception as e:
            print(f"处理图片 {img_path.name} 时出错: {str(e)}")


def main():
    """主函数"""
    try:
        # 初始化配置和API
        config = AppConfig("resource/print_workshop_advance.yaml")
        api = ComfyAPI(config)

        # 处理所有图片
        process_images(config, api)

        print("所有图片处理完成！")

    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()
