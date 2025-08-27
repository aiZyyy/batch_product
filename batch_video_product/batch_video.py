from gradio_client import Client, handle_file
import os
from pathlib import Path

# 初始化客户端（注意检查端口是否匹配）
client = Client("http://localhost/")


def generate_video(text_z, width, height, img_path):
    """
    视频生成函数
    :param text_z: 文本提示
    :param width: 视频宽度
    :param height: 视频高度
    :param img_path: 图片路径
    :return: 生成的视频文件路径
    """
    try:
        # 处理图片文件
        img = handle_file(img_path)

        # 执行视频生成
        result = client.predict(
            text_z=text_z,
            width=width,
            height=height,
            length=2,
            img=img,
            step=3,
            img2=None,
            text_f="色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走",
            lora_open="无",
            lora_weight=0.9,
            refine_text="开启",
            api_name="/start_job"
        )

        return result  # 返回生成的视频路径

    except Exception as e:
        print(f"生成失败: {str(e)}")
        return None


def process_folder(folder_path, text_z="", width=261, height=464):
    """
    处理文件夹中的所有PNG图片
    :param folder_path: 文件夹路径
    :param text_z: 文本提示（可选）
    :param width: 视频宽度（可选）
    :param height: 视频高度（可选）
    """
    # 确保文件夹路径存在
    if not os.path.exists(folder_path):
        print(f"错误：文件夹路径 '{folder_path}' 不存在")
        return

    # 获取所有PNG文件
    png_files = list(Path(folder_path).glob("*.png"))

    if not png_files:
        print(f"在文件夹 '{folder_path}' 中未找到PNG文件")
        return

    print(f"找到 {len(png_files)} 个PNG文件，开始处理...")

    # 按文件名排序处理
    for i, img_path in enumerate(sorted(png_files)):
        print(f"处理第 {i + 1}/{len(png_files)} 个文件: {img_path.name}")

        # 调用生成函数
        result = generate_video(
            text_z=text_z,
            width=width,
            height=height,
            img_path=str(img_path)
        )

        if result:
            print(f"生成成功！视频文件保存于：{result}")
        else:
            print(f"生成失败：{img_path.name}")


# 使用示例 ---------------------------------------------------
if __name__ == "__main__":
    # 示例1：处理整个文件夹
    folder_url = "G:/your_folder_path"  # 替换为你的文件夹路径
    process_folder(folder_url, text_z="你的文本提示")

    # 示例2：处理单个图片
    # output_video = generate_video(
    #     text_z="你的文本提示",
    #     width=261,
    #     height=464,
    #     img_path="G:/1.png"
    # )
    # print(f"生成成功！视频文件保存于：{output_video}")