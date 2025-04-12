import os
from datetime import datetime

from openpyxl import Workbook


def parse_image_info(file_path):
    """解析图片路径中的关键信息"""
    # 获取父目录名称作为Lora
    lora = os.path.basename(os.path.dirname(file_path))

    # 提取文件名
    filename = os.path.basename(file_path)

    # 使用正则提取种子（文件名开头的连续数字）
    # 从文件名第13位开始截取到第一个下划线（索引从0开始计算）
    try:
        # 确保文件名长度足够
        if len(filename) >= 13:
            # 从索引12开始截取到第一个下划线
            seed = filename[12:filename.index('_', 12)]
        else:
            seed = "未知"
    except ValueError:
        # 处理没有下划线的情况
        seed = filename[12:] if len(filename) >= 13 else "未知"

    # 获取当前日期
    current_date = datetime.now().strftime("%Y-%m-%d")

    return [lora, "", filename, seed, file_path, current_date]


def organize_images_to_excel(folder_path, output_file):
    """将图片信息整理到Excel"""
    # 创建工作簿
    wb = Workbook()
    ws = wb.active
    ws.append(["Lora", "关键词", "文件名", "种子", "图片地址", "日期"])

    # 遍历文件夹
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                file_path = os.path.join(root, file)
                row_data = parse_image_info(file_path)
                ws.append(row_data)

    # 保存文件
    wb.save(output_file)
    print(f"已生成Excel文件：{output_file}")


if __name__ == "__main__":
    # 使用示例
    folder_path = r"D:\image\国风zl.txt"  # 替换为实际路径
    output_file = "国风zl.txt.xlsx"
    organize_images_to_excel(folder_path, output_file)
