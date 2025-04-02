from gradio_client import Client, handle_file

# 初始化客户端（注意检查端口是否匹配）
client = Client("http://localhost:9872/")

def generate_tts(custom_audio_path, synthesis_text):
    """
    语音合成生成函数
    :param custom_audio_path: 自定义参考音频路径（3-10秒，支持本地路径或URL）
    :param synthesis_text: 需要合成的文本内容
    :return: 生成的音频文件路径
    """
    try:
        # 步骤1：处理参考音频
        # 自动识别参考音频文本
        recognized_text = client.predict(
            prompt_wav=handle_file(custom_audio_path),
            api_name="/prompt_wav_recognition"
        )
        
        # 步骤2：执行语音合成
        result = client.predict(
            text=synthesis_text,  # 需要合成的文本
            text_lang="中文",       # 文本语种（根据实际情况修改）
            
            # 参考音频相关参数
            ref_audio_path=handle_file(custom_audio_path),
            prompt_text=recognized_text,
            prompt_lang="中文",     # 参考音频语种
            
            # 以下为保持默认的重要参数
            aux_ref_audio_paths=[], # 不使用辅参考音频
            top_k=5,
            top_p=1,
            temperature=1,
            speed_factor=1,
            sample_steps=32,
            
            # 保持其他默认参数
            api_name="/inference"
        )
        
        return result[0]  # 返回生成的音频路径
        
    except Exception as e:
        print(f"生成失败: {str(e)}")
        return None

# 使用示例 ---------------------------------------------------
if __name__ == "__main__":
    # 自定义参数设置
    my_audio = "1.MP3"  # 替换为你的音频路径
    my_text = "今天天气真好，我们一起出去散步吧！注意：返回的路径是服务器端路径，如需下载使用需额外处理，自定义参数设置"  # 替换为你的文本
    
    # 执行生成
    output_audio = generate_tts(my_audio, my_text)
    
    if output_audio:
        print(f"生成成功！音频文件保存于：{output_audio}")
        # 注意：返回的路径是服务器端路径，如需下载使用需额外处理