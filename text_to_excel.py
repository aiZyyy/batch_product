import pandas as pd
import sys
import os

def text_to_excel(input_file, output_file=None):
    """
    将文本文件中的每一行内容导出到Excel的单独单元格中
    
    参数:
    input_file (str): 输入的文本文件路径
    output_file (str, 可选): 输出的Excel文件路径，默认为None
    """
    # 读取文本文件
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file.readlines()]
    except UnicodeDecodeError:
        # 尝试其他编码
        with open(input_file, 'r', encoding='gbk') as file:
            lines = [line.strip() for line in file.readlines()]
    
    # 创建DataFrame
    df = pd.DataFrame(lines, columns=['内容'])
    
    # 设置输出文件名
    if output_file is None:
        output_file = os.path.splitext(input_file)[0] + '.xlsx'
    
    # 导出到Excel
    df.to_excel(output_file, index=False)
    print(f"成功导出 {len(lines)} 行内容到: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("请提供文本文件路径作为参数")
        print("用法: python script.py <input_file.txt> [output_file.xlsx]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    text_to_excel(input_path, output_path)