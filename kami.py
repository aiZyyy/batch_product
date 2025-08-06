import hashlib
import platform
import re
import subprocess
import time
import uuid

import requests


def unbind_machine(app_id, kami, markcode=None, enable_sign=False, secret_key=None):
    base_url = "http://118.89.191.103/api.php"

    # 构建基本参数
    params = {
        "api": "kmunmachine",
        "app": app_id,
        "kami": kami
    }

    # 添加设备码（如果提供）
    if markcode:
        params["markcode"] = markcode

    # 处理签名逻辑
    if enable_sign:
        if not secret_key:
            return {"error": "签名功能需要提供secret_key"}

        # 添加时间戳（秒级）
        t = str(int(time.time()))
        params["t"] = t

        # 生成签名：按参数名排序后拼接 + secret_key，然后MD5
        param_str = ""
        for key in sorted(params.keys()):
            param_str += f"{key}{params[key]}"
        param_str += secret_key

        sign = hashlib.md5(param_str.encode('utf-8')).hexdigest()
        params["sign"] = sign

    try:
        # 发送GET请求（禁用SSL验证，因为使用HTTP）
        response = requests.get(
            url=base_url,
            params=params,
            verify=False,  # 注意：实际生产环境建议使用HTTPS并启用验证
            timeout=10
        )

        # 解析JSON响应
        result = response.json()

        # 检查返回状态码
        if "code" not in result:
            return {"error": "API返回格式异常", "raw": result}

        # 状态码转换（文档说明是String，但示例是int）
        code = result.get('code')
        if isinstance(code, str):
            code = int(code) if code.isdigit() else code

        # 成功返回
        if code == 200:
            return {
                "status": "success",
                "raw_data": result
            }
        # 错误处理
        else:
            error_map = {
                101: "应用不存在",
                102: "应用已关闭",
                104: "签名为空",
                105: "数据过期",
                106: "签名有误",
                148: "卡密为空",
                149: "卡密不存在",
                151: "卡密禁用",
                169: "IP不一致",
                171: "接口维护中",
                172: "接口未添加或不存在"
            }
            msg = error_map.get(code, f"未知错误 (code: {code})")
            return {
                "status": "error",
                "code": code,
                "message": msg,
                "raw": result
            }

    except requests.exceptions.RequestException as e:
        return {"error": f"网络请求失败: {str(e)}"}
    except ValueError as e:
        return {"error": f"JSON解析失败: {str(e)}"}


def kmlogin_api(app_id, kami, markcode=None, enable_sign=False, secret_key=None):
    """
    调用卡密登录验证接口

    :param app_id: 应用ID (必填)
    :param kami: 卡密 (必填)
    :param markcode: 设备码 (如果后台开启设备验证则必填)
    :param enable_sign: 是否启用数据签名
    :param secret_key: 签名密钥（enable_sign=True时需要）
    :return: API响应数据字典 或 错误信息字典
    """
    # 基础URL（注意文档提供的是HTTP而非HTTPS）
    base_url = "http://118.89.191.103/api.php"

    # 构建基本参数
    params = {
        "api": "kmlogon",
        "app": app_id,
        "kami": kami
    }

    # 添加设备码（如果提供）
    if markcode:
        params["markcode"] = markcode

    # 处理签名逻辑
    if enable_sign:
        if not secret_key:
            return {"error": "签名功能需要提供secret_key"}

        # 添加时间戳（秒级）
        t = str(int(time.time()))
        params["t"] = t

        # 生成签名：按参数名排序后拼接 + secret_key，然后MD5
        param_str = ""
        for key in sorted(params.keys()):
            param_str += f"{key}{params[key]}"
        param_str += secret_key

        sign = hashlib.md5(param_str.encode('utf-8')).hexdigest()
        params["sign"] = sign

    try:
        # 发送GET请求（禁用SSL验证，因为使用HTTP）
        response = requests.get(
            url=base_url,
            params=params,
            verify=False,  # 注意：实际生产环境建议使用HTTPS并启用验证
            timeout=10
        )

        # 解析JSON响应
        result = response.json()

        # 检查返回状态码
        if "code" not in result:
            return {"error": "API返回格式异常", "raw": result}

        # 状态码转换（文档说明是String，但示例是int）
        code = result.get('code')
        if isinstance(code, str):
            code = int(code) if code.isdigit() else code

        # 成功返回
        if code == 200:
            return {
                "status": "success",
                "kami": result.get("msg", {}).get("kami"),
                "vip": result.get("msg", {}).get("vip"),
                "raw_data": result
            }
        # 错误处理
        else:
            error_map = {
                101: "应用不存在",
                102: "应用已关闭",
                104: "签名为空",
                105: "数据过期",
                106: "签名有误",
                148: "卡密为空",
                149: "卡密不存在",
                151: "卡密禁用",
                169: "IP不一致",
                171: "接口维护中",
                172: "接口未添加或不存在"
            }
            msg = error_map.get(code, f"未知错误 (code: {code})")
            return {
                "status": "error",
                "code": code,
                "message": msg,
                "raw": result
            }

    except requests.exceptions.RequestException as e:
        return {"error": f"网络请求失败: {str(e)}"}
    except ValueError as e:
        return {"error": f"JSON解析失败: {str(e)}"}


def get_device_code():
    """
    生成基于电脑硬件信息的设备码（哈希值）
    组合了多个硬件标识符以提高稳定性和唯一性
    """
    # 收集多种硬件标识符
    identifiers = {
        "machine_id": get_machine_id(),
        "mac_address": get_mac_address(),
        "disk_serial": get_disk_serial(),
        "bios_serial": get_bios_serial(),
        "cpu_info": get_cpu_info(),
        "platform_info": get_platform_info()
    }

    # 组合所有标识符生成哈希
    combined = "".join(identifiers.values()).encode('utf-8')
    device_hash = hashlib.md5(combined).hexdigest()

    return device_hash.upper()  # 返回大写的MD5哈希值


# 辅助函数 =============================================

def get_machine_id():
    """获取系统生成的机器ID"""
    try:
        if platform.system() == 'Windows':
            return subprocess.check_output(
                'wmic csproduct get uuid',
                shell=True,
                text=True
            ).split('\n')[1].strip()
        elif platform.system() == 'Linux':
            with open('/var/lib/dbus/machine-id') as f:
                return f.read().strip()
        elif platform.system() == 'Darwin':
            return subprocess.check_output(
                'ioreg -rd1 -c IOPlatformExpertDevice | grep IOPlatformUUID',
                shell=True,
                text=True
            ).split('=')[-1].replace('"', '').strip()
    except:
        return ""


def get_mac_address():
    """获取MAC地址"""
    try:
        mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
        # 使用第一个非本地MAC地址
        if mac != "00:00:00:00:00:00":
            return mac
    except:
        pass
    return ""


def get_disk_serial():
    """获取主硬盘序列号"""
    try:
        if platform.system() == 'Windows':
            result = subprocess.check_output(
                'wmic diskdrive get SerialNumber',
                shell=True,
                text=True
            )
            # 取第一个有效序列号
            for line in result.split('\n'):
                if line.strip() and "SerialNumber" not in line:
                    return line.strip()
        elif platform.system() == 'Linux':
            result = subprocess.check_output(
                'hdparm -i /dev/sda | grep SerialNo',
                shell=True,
                text=True
            )
            return result.split('SerialNo=')[1].split()[0].strip()
        elif platform.system() == 'Darwin':
            result = subprocess.check_output(
                'diskutil info /dev/disk0 | grep "Device / Media" -A 10 | grep "Serial Number"',
                shell=True,
                text=True
            )
            return result.split(':')[-1].strip()
    except:
        pass
    return ""


def get_bios_serial():
    """获取BIOS序列号"""
    try:
        if platform.system() == 'Windows':
            return subprocess.check_output(
                'wmic bios get serialnumber',
                shell=True,
                text=True
            ).split('\n')[1].strip()
        elif platform.system() == 'Linux':
            with open('/sys/class/dmi/id/product_serial') as f:
                return f.read().strip()
        elif platform.system() == 'Darwin':
            return subprocess.check_output(
                'ioreg -l | grep IOPlatformSerialNumber',
                shell=True,
                text=True
            ).split('=')[-1].replace('"', '').strip()
    except:
        return ""


def get_cpu_info():
    """获取CPU标识信息"""
    try:
        if platform.system() == 'Windows':
            return subprocess.check_output(
                'wmic cpu get ProcessorId',
                shell=True,
                text=True
            ).split('\n')[1].strip()
        elif platform.system() == 'Linux':
            with open('/proc/cpuinfo') as f:
                for line in f:
                    if line.strip() and line.split(':')[0].strip() == 'model name':
                        return line.split(':')[1].strip()
        elif platform.system() == 'Darwin':
            return subprocess.check_output(
                'sysctl -n machdep.cpu.brand_string',
                shell=True,
                text=True
            ).strip()
    except:
        pass
    return platform.processor() or ""


def get_platform_info():
    """获取平台基本信息"""
    return f"{platform.system()}_{platform.release()}_{platform.machine()}"


# if __name__ == "__main__":
#     # 基本参数（必填）
#     APP_ID = "10002"  # 替换为你的应用ID
#     CARD_KEY = "MonuqT5YDjXuqQXSQiJqLsPjU46p"  # 替换为你的卡密
#
#     # 可选参数（根据后台配置决定）
#     DEVICE_CODE = get_device_code()  # 如果开启设备验证则需要
#     print(f"生成的设备码: {DEVICE_CODE}")
#     print(f"长度: {len(DEVICE_CODE)} 字符")
#     ENABLE_SIGN = False  # 如果开启数据签名需要设为True
#     SECRET_KEY = "your_secret"  # 后台配置的签名密钥
#
#     # 调用API
#     result = kmlogin_api(
#         app_id=APP_ID,
#         kami=CARD_KEY,
#         markcode=DEVICE_CODE,  # 如果不需要可以设为None
#         enable_sign=ENABLE_SIGN,
#         secret_key=SECRET_KEY  # 签名启用时才需要
#     )
#
#     # 输出结果
#     print("API调用结果:")
#     print(result)

    # 使用示例 ==============================================
if __name__ == "__main__":
    # 基本参数
    APP_ID = "10002"  # 替换为你的应用ID
    DEVICE_CODE = "BB16FB1AEA00E75D4A34055A968E40ED "  # 替换为要解绑的设备码
    kami="Monshg4gJDjez2hfeGLkhmrZLXSg"

    # 可选参数
    ENABLE_SIGN = False  # 是否启用签名
    SECRET_KEY = "your_secret"  # 签名密钥

    # 调用解绑API
    result = unbind_machine(
        app_id=APP_ID,
        kami=kami,
        markcode=DEVICE_CODE,
        enable_sign=ENABLE_SIGN,
        secret_key=SECRET_KEY
    )

    # 输出结果
    print("解绑操作结果:")
    print(result)