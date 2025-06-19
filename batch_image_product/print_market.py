# -*- coding: utf-8 -*-
"""
图像批量生成工具 - 增强版
功能：
1. 根据图片分辨率动态修改工作流
2. 遍历指定文件夹中的所有图片
3. 自动替换工作流中的关键参数
4. 随机选择LORA模型
5. 动态生成输出路径
"""

import imghdr
import json
import random
import re
import struct
import time
from datetime import datetime
from pathlib import Path
from urllib import request, error

import yaml
import argparse


class AppConfig:
    def __init__(self, config_path, image_folder=None):
        """初始化并加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.raw = yaml.safe_load(f)  # 加载YAML配置

        # 路径配置
        # 修改：优先使用命令行传入的image_folder
        self.image_folder = Path(image_folder) if image_folder else Path(self.raw['image_folder'])
        self.lora_names = self.raw['lora_names']  # LORA模型名称列表
        # 现在只使用一个工作流文件
        self.workflow_file = Path("workflow/" + self.raw['workflow'])
        self.BiRefNet_url = self.raw['BiRefNet_url']
        self.flux_Guide = self.raw['flux_Guide']
        self.style_num = self.raw['style_num']

        self.max_retries = self.raw['max_retries']
        self.request_timeout = self.raw['request_timeout']
        self.people = self.raw['people']
        self.batch_size = self.raw['batch_size']

        self.seed_range = tuple(self.raw['seed_range'])

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


def get_image_dimensions(image_path):
    """获取图片的宽度和高度（不加载整个图片）"""
    try:
        with open(image_path, 'rb') as f:
            # 读取文件头信息判断图片类型
            head = f.read(24)
            if len(head) != 24:
                return None

            # 检查图片类型并获取尺寸
            if imghdr.what(image_path) == 'png':
                # PNG格式: 宽度和高度在16-24字节
                width, height = struct.unpack(">ii", head[16:24])
            elif imghdr.what(image_path) == 'jpeg':
                # JPEG格式: 需要查找SOF标记
                f.seek(0)
                size = 2
                ftype = 0
                while not 0xc0 <= ftype <= 0xcf:
                    f.seek(size, 1)
                    byte = f.read(1)
                    while ord(byte) == 0xff:
                        byte = f.read(1)
                    ftype = ord(byte)
                    size = struct.unpack('>H', f.read(2))[0] - 2
                # SOF块包含高度和宽度信息
                f.seek(1, 1)  # 跳过精度字节
                height, width = struct.unpack('>HH', f.read(4))
            else:
                # 其他格式使用PIL（如果需要）
                try:
                    from PIL import Image
                    with Image.open(image_path) as img:
                        return img.size
                except ImportError:
                    print("警告: 需要PIL库来获取此图片类型的尺寸")
                    return None
            return width, height
    except Exception as e:
        print(f"获取图片尺寸失败: {str(e)}")
        return None


def process_images(config, api):
    """处理所有图片并发送到ComfyUI，保留目录结构"""
    # 获取所有图片文件（递归子文件夹）
    image_files = []
    for ext in ['.png', '.jpg', '.jpeg', '.webp']:
        image_files.extend(config.image_folder.rglob(f'*{ext}'))
        image_files.extend(config.image_folder.rglob(f'*{ext.upper()}'))  # 处理大写后缀

    # 去重并确保只保留文件
    image_files = [f for f in set(image_files) if f.is_file()]

    if not image_files:
        print(f"在 {config.image_folder} 中没有找到图片文件")
        return

    print(f"找到 {len(image_files)} 张图片，开始处理...")

    # 预先加载工作流模板
    with open(config.workflow_file, 'r', encoding='utf-8') as f:
        base_workflow = json.load(f)

    for img_path in image_files:
        try:
            # 获取图片尺寸
            dimensions = get_image_dimensions(img_path)
            if not dimensions:
                print(f"跳过无法获取尺寸的图片: {img_path.name}")
                continue

            width, height = dimensions
            # 获取相对于根目录的路径
            relative_path = img_path.relative_to(config.image_folder)
            print(f"图片: {relative_path} | 分辨率: {width}x{height}")

            # 深拷贝工作流，以便修改
            workflow = json.loads(json.dumps(base_workflow))

            # 根据分辨率动态修改工作流
            if width > 1000 or height > 1000:
                print("  高分辨率图片，移除放大节点")

                # 移除放大节点
                if "301" in workflow:
                    del workflow["301"]
                if "302" in workflow:
                    del workflow["302"]

                # 直接连接原始图片到缩放节点
                if "127" in workflow:
                    workflow["127"]["inputs"]["image"] = ["288", 0]
            else:
                print("  低分辨率图片，保留放大节点")

            # 获取图片基本信息
            img_name = img_path.stem
            sanitized_name = sanitize_filename(img_name)

            # 随机选择LORA模型
            lora_name = random.choice(config.lora_names)
            sanitized_lora = sanitize_filename(lora_name.split('.')[0])
            seed1 = random.randint(*config.seed_range)
            workflow["50"]["inputs"]["seed"] = seed1
            print(f"种子1为: {seed1}")
            seed2 = random.randint(*config.seed_range)
            workflow["109"]["inputs"]["seed"] = seed2
            print(f"种子2为: {seed2}")

            # 更新工作流节点
            # 节点288: 图片路径
            workflow["288"]["inputs"]["paths"] = str(img_path.resolve())

            workflow["294"]["inputs"]["batch_size"] = config.batch_size
            workflow["290"]["inputs"]["value"] = config.style_num
            workflow["106"]["inputs"]["guidance"] = config.flux_Guide
            workflow["76"]["inputs"]["local_model_path"] = config.BiRefNet_url

            # 节点293: LORA名称
            workflow["293"]["inputs"]["lora_name"] = lora_name

            # 节点291: 当前日期
            workflow["291"]["inputs"]["String"] = config.people + "_" + config.date_folder

            # 获取相对目录路径（保持文件夹结构）
            relative_dir = relative_path.parent
            # 节点214: 原图路径（保留文件夹结构）
            output_path_214 = f"原图/{relative_dir}/{sanitized_lora}_{sanitized_name}".replace('\\', '/')
            workflow["214"]["inputs"]["String"] = output_path_214

            # 节点216: 透明底路径（保留文件夹结构）
            output_path_216 = f"透明/{relative_dir}/{sanitized_lora}_{sanitized_name}".replace('\\', '/')
            workflow["216"]["inputs"]["String"] = output_path_216

            print(f"  输出路径: {output_path_214}")
            print(f"  透明路径: {output_path_216}")

            # 发送处理请求
            if api.send_prompt(workflow):
                print(f"  成功发送: {relative_path} | LORA: {lora_name}")
            else:
                print(f"  处理失败: {relative_path}")

        except Exception as e:
            print(f"处理图片 {img_path} 时出错: {str(e)}")


def main():
    """主函数"""
    try:
        # 新增：命令行参数解析
        parser = argparse.ArgumentParser(description='图像批量生成工具')
        parser.add_argument('--image_folder', type=str, help='覆盖配置中的图片文件夹路径')
        args = parser.parse_args()

        # 初始化配置和API
        config = AppConfig("resource/print_workshop_advance.yaml", image_folder=args.image_folder)
        api = ComfyAPI(config)

        # 处理所有图片
        process_images(config, api)

        print("所有图片处理完成！")

    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()