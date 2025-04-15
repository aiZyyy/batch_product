import os
import re
from datetime import datetime

from openpyxl import Workbook


def load_keywords(keyword_file):
    """加载提示词库（存储原始内容和处理后的版本）"""
    with open(keyword_file, 'r', encoding='utf-8') as f:
        # 存储元组：(原始提示词, 处理后的提示词)
        return [(
            line.strip(),  # 原始内容
            re.sub(r'[^a-zA-Z0-9]', '', line.strip())  # 处理后的内容
        ) for line in f if line.strip()]


def parse_image_info(file_path, keywords):
    """解析图片路径中的关键信息"""
    # 获取父目录名称作为Lora
    lora = os.path.basename(os.path.dirname(file_path))

    # 提取文件名（不含路径）
    filename = os.path.basename(file_path)

    # 提取文件名前12位（不足则取全部）
    filename_prefix = filename[:12] if len(filename) >= 12 else filename

    # 匹配关键词（处理后的版本），获取原始版本
    matched_keyword = "未找到匹配关键词"
    for raw_kw, processed_kw in keywords:
        if processed_kw.startswith(filename_prefix):
            matched_keyword = raw_kw
            break

    # 从文件名第13位开始截取到第一个下划线
    try:
        seed = filename[12:filename.index('_', 12)] if len(filename) >= 13 else "未知"
    except ValueError:
        seed = filename[12:] if len(filename) >= 13 else "未知"

    # 获取当前日期
    current_date = datetime.now().strftime("%Y-%m-%d")

    return [lora, matched_keyword, filename, seed, file_path, current_date]


def organize_images_to_excel(folder_path, keyword_file, output_file):
    """主处理函数"""
    # 加载提示词库
    keywords = load_keywords(keyword_file)

    # 创建工作簿
    wb = Workbook()
    ws = wb.active
    ws.append(["lora", "关键词", "文件名", "种子", "图片地址", "日期"])

    # 遍历文件夹
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                file_path = os.path.join(root, file)
                row_data = parse_image_info(file_path, keywords)
                ws.append(row_data)

    # 保存文件
    wb.save(output_file)
    print(f"已生成Excel文件：{output_file}")


if __name__ == "__main__":
    # 使用示例
    folder_path = r"G:\image\4.11-zl.txt"  # 替换为实际路径
    keyword_file = "F://workspace//python//batch_product//batch_image_product//prompts//ZL.txt"  # 提示词文件路径
    output_file = "4.11-zl.txt.xlsx"
    organize_images_to_excel(folder_path, keyword_file, output_file)
