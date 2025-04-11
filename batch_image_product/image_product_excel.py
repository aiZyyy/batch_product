# -*- coding: utf-8 -*-
"""
图像批量生成工具 - Excel集成版
功能：
1. 从Excel读取lora模型和关键词
2. 自动创建带日期的目录结构
3. 生成后回写文件名、种子和日期到Excel
4. 增强的错误处理和文件名清理
"""

import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from urllib import request, error

import pandas as pd  # Excel处理
import yaml


# ----------------------------
# 配置加载模块
# ----------------------------
class AppConfig:
    def __init__(self, config_path):
        """初始化并加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.raw = yaml.safe_load(f)  # 加载YAML配置

        # 路径配置
        self.workflow_path = Path("workflow/" + self.raw['workflow_path'])  # 工作流模板路径
        self.filename_prefix = self.raw['excel_file']  # 输出根目录
        self.excel_file = Path("excel/" + self.raw['excel_file'])  # Excel数据文件路径

        # 模型参数
        self.checkpoint = self.raw['checkpoint']  # 主模型路径
        self.seed_range = tuple(self.raw['seed_range'])  # 种子范围

        # 图像参数
        self.width = self.raw['width']  # 图像宽度
        self.height = self.raw['height']  # 图像高度
        self.batch_size = self.raw['batch_size']  # 批量大小
        self.max_filename_length = self.raw['max_filename_length']  # 文件名最大长度

        # 网络设置
        self.max_retries = self.raw['max_retries']  # 最大重试次数
        self.request_timeout = self.raw['request_timeout']  # 请求超时时间

        # 新增日期目录
        self.date_folder = datetime.now().strftime("%Y-%m-%d")


# ----------------------------
# 工作流节点管理
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
        """从工作流中识别关键节点"""
        self.nodes = {}
        for node_id, node_data in workflow.items():
            for key, value in self.NODE_MAP.items():
                if node_data['class_type'] == value:
                    self.nodes[key] = node_data
                    break

        # 验证必须存在的节点
        required_nodes = ['ksampler', 'checkpoint_loader', 'lora_loader']
        missing = [n for n in required_nodes if n not in self.nodes]
        if missing:
            raise ValueError(f"缺少关键节点: {missing}")


# ----------------------------
# API通信模块
# ----------------------------
class ComfyAPI:
    def __init__(self, config):
        """初始化API连接参数"""
        self.endpoint = "http://127.0.0.1:8188/prompt"  # ComfyUI API地址
        self.max_retries = config.max_retries  # 最大重试次数
        self.timeout = config.request_timeout  # 超时时间

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


# ----------------------------
# 工具函数
# ----------------------------
def sanitize_filename(text, max_length=15):
    """清理文件名中的非法字符
    Args:
        text (str): 原始文本
        max_length (int): 最大长度
    Returns:
        str: 清理后的安全文件名
    """
    # 移除特殊字符并替换空格
    cleaned = re.sub(r'[\\/*?:"<>|]', '', text)
    cleaned = cleaned.replace(' ', '_')[:max_length]
    return cleaned


# ----------------------------
# 主程序
# ----------------------------
def main():
    try:
        # 初始化配置
        config = AppConfig("resource/config_excel.yaml")
        api = ComfyAPI(config)

        # 创建带日期的输出目录
        date_dir = os.path.join(config.date_folder, config.filename_prefix)
        # os.makedirs(date_dir, exist_ok=True)  # 自动创建目录

        # 加载工作流模板
        with open(config.workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        nodes = WorkflowNodes(workflow).nodes

        # 配置静态参数
        nodes['checkpoint_loader']['inputs']['ckpt_name'] = config.checkpoint
        nodes['latent_img']['inputs'].update({
            'width': config.width,
            'height': config.height,
            'batch_size': config.batch_size
        })

        # 读取Excel数据
        df = pd.read_excel(config.excel_file, engine='openpyxl')

        # 验证必要列是否存在
        required_cols = ['lora', '关键词']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Excel缺少必要列: {missing_cols}")

        # 在读取Excel后添加类型转换处理（主程序部分修改）
        # 原代码：
        # for col in ['文件名', '种子', '日期', '错误信息']:
        #     if col not in df.columns:
        #         df[col] = ''

        # 修改为：
        # 初始化或转换列数据类型
        col_types = {
            '文件名': str,  # 字符串类型
            '种子': str,  # 字符串类型
            '日期': 'datetime64[ns]',  # 日期类型
            '错误信息': str  # 字符串类型
        }

        for col, dtype in col_types.items():
            if col not in df.columns:
                # 创建新列时直接指定类型
                df[col] = pd.Series(dtype=dtype)
            else:
                # 转换现有列类型
                try:
                    df[col] = df[col].astype(dtype)
                except (TypeError, ValueError):
                    # 转换失败时用默认值初始化
                    df[col] = pd.Series(dtype=dtype)
                    print(f"列 {col} 类型转换失败，已重建")

        # 处理每个数据行
        total_rows = len(df)
        for index, row in df.iterrows():
            start_time = time.time()
            lora_name = str(row['lora']).strip()
            prompt = str(row['关键词']).strip()
            status = "FAILED"
            error_msg = ""
            seed = None
            filename = ""

            try:
                # 跳过空数据行
                if not lora_name or not prompt:
                    error_msg = "数据不完整"
                    raise ValueError(error_msg)

                # 生成种子和清理文件名
                seed = random.randint(*config.seed_range)
                clean_prefix = sanitize_filename(prompt, config.max_filename_length)
                filename = f"{clean_prefix}_{seed}.png"

                # 创建lora专属目录
                lora_dir = os.path.join(date_dir, lora_name)
                # os.makedirs(lora_dir, exist_ok=True)

                # 配置动态参数
                nodes['lora_loader']['inputs']['lora_name'] = lora_name
                nodes['prompt_pos']['inputs']['text'] = prompt
                nodes['ksampler']['inputs']['seed'] = seed
                nodes['save_image']['inputs']['filename_prefix'] = os.path.join(lora_dir, clean_prefix)

                # 发送生成请求
                if api.send_prompt(workflow):
                    # 赋值时确保类型安全（修改数据更新部分）
                    # 原代码：
                    # df.at[index, '文件名'] = filename
                    # df.at[index, '种子'] = seed

                    # 修改为：
                    if pd.api.types.is_string_dtype(df['文件名']):
                        df.at[index, '文件名'] = filename
                    else:
                        df['文件名'] = df['文件名'].astype(str)
                        df.at[index, '文件名'] = filename

                    if pd.api.types.is_string_dtype(df['种子']):
                        df.at[index, '种子'] = seed
                    else:
                        df['种子'] = df['种子'].astype(str)
                        df.at[index, '种子'] = seed
                    df.at[index, '日期'] = datetime.now().strftime("%Y-%m-%d")
                    status = "SUCCESS"

                # 每5条保存一次进度
                if (index + 1) % 5 == 0:
                    df.to_excel(config.excel_file, index=False, engine='openpyxl')
                    print(f"已保存进度：处理到第 {index + 1}/{total_rows} 行")

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                df.at[index, '错误信息'] = error_msg
                print(f"第 {index + 1} 行处理失败: {error_msg}")
            finally:
                # 记录处理日志
                elapsed = time.time() - start_time
                print(f"[{index + 1}/{total_rows}] {status} | 耗时: {elapsed:.2f}s")

        # 最终保存Excel
        df.to_excel(config.excel_file, index=False, engine='openpyxl')
        print(f"处理完成！结果已保存至: {os.path.abspath(config.excel_file)}")

    except Exception as e:
        print(f"程序运行失败: {str(e)}")
        if 'df' in locals():
            # 尝试保存当前进度
            try:
                df.to_excel(config.excel_file, index=False, engine='openpyxl')
                print("已保存当前处理进度")
            except:
                print("无法保存进度文件")


if __name__ == "__main__":
    main()
