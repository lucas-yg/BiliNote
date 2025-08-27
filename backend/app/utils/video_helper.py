import shutil
from pathlib import Path

from dotenv import load_dotenv
import subprocess
import os
import uuid
load_dotenv()
api_path = os.getenv("API_BASE_URL", "http://localhost")
BACKEND_PORT= os.getenv("BACKEND_PORT", 8483)

BACKEND_BASE_URL = f"{api_path}:{BACKEND_PORT}"

from typing import Optional
def generate_screenshot(video_path: str, output_dir: str, timestamp: int, index: int) -> str:
    """
    使用 ffmpeg 生成截图，支持损坏视频，返回生成图片路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"screenshot_{index:03}_{uuid.uuid4()}.jpg"
    output_path = output_dir / filename

    # 增强的ffmpeg命令，支持损坏视频
    command = [
        "ffmpeg",
        "-err_detect", "ignore_err",        # 忽略解码错误
        "-fflags", "+discardcorrupt",       # 丢弃损坏的包
        "-ss", str(timestamp),              # 跳转到指定时间
        "-i", str(video_path),
        "-frames:v", "1",                   # 只提取1帧
        "-q:v", "2",                        # 高质量
        "-avoid_negative_ts", "make_zero",  # 避免负时间戳
        "-y",                               # 覆盖输出文件
        str(output_path)
    ]

    print(f"生成截图命令: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            timeout=30
        )

        if result.returncode != 0:
            print(f"截图生成失败: {result.stderr}")
            
            # 如果失败，尝试更宽松的参数
            fallback_command = [
                "ffmpeg",
                "-err_detect", "ignore_err",
                "-fflags", "+discardcorrupt+igndts",
                "-ss", str(max(0, timestamp - 1)),  # 稍微提前一点
                "-i", str(video_path),
                "-frames:v", "1",
                "-vf", "scale=640:-1",              # 缩放以减少处理复杂度
                "-q:v", "5",                        # 降低质量要求
                "-f", "image2",                     # 强制图像格式
                "-y",
                str(output_path)
            ]
            
            print(f"尝试备用截图命令: {' '.join(fallback_command)}")
            result = subprocess.run(
                fallback_command, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"备用截图也失败: {result.stderr}")
                # 创建一个默认的占位图片
                return _create_placeholder_image(str(output_path), f"无法生成截图 (时间: {timestamp}s)")

        # 检查文件是否成功创建
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            print("截图文件未创建或为空")
            return _create_placeholder_image(str(output_path), f"截图生成失败 (时间: {timestamp}s)")

        print(f"截图生成成功: {output_path}")
        return str(output_path)
        
    except subprocess.TimeoutExpired:
        print(f"截图生成超时 (时间戳: {timestamp})")
        return _create_placeholder_image(str(output_path), f"截图超时 (时间: {timestamp}s)")
    except Exception as e:
        print(f"截图生成异常: {e}")
        return _create_placeholder_image(str(output_path), f"截图异常 (时间: {timestamp}s)")


def _create_placeholder_image(output_path: str, text: str) -> str:
    """创建占位图片"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 创建一个简单的占位图
        img = Image.new('RGB', (640, 360), color='gray')
        draw = ImageDraw.Draw(img)
        
        try:
            # 尝试使用默认字体
            font = ImageFont.load_default()
        except:
            font = None
        
        # 在图片中心添加文字
        if font:
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            x = (640 - text_width) // 2
            y = (360 - text_height) // 2
            draw.text((x, y), text, fill='white', font=font)
        
        img.save(output_path, 'JPEG')
        return output_path
        
    except ImportError:
        # 如果没有PIL，创建一个空文件
        with open(output_path, 'w') as f:
            f.write("placeholder")
        return output_path
    except Exception:
        # 如果所有都失败，至少确保有文件存在
        Path(output_path).touch()
        return output_path



def save_cover_to_static(local_cover_path: str, subfolder: Optional[str] = "cover") -> str:
    """
    将封面图片保存到 static 目录下，并返回前端可访问的路径
    :param local_cover_path: 本地原封面路径（比如提取出来的jpg）
    :param subfolder: 子目录，默认是 cover，可以自定义
    :return: 前端访问路径，例如 /static/cover/xxx.jpg
    """
    # 项目根目录
    project_root = os.getcwd()

    # static目录
    static_dir = os.path.join(project_root, "static")

    # 确定目标子目录
    target_dir = os.path.join(static_dir, subfolder or "cover")
    os.makedirs(target_dir, exist_ok=True)

    # 拷贝文件
    file_name = os.path.basename(local_cover_path)
    target_path = os.path.join(target_dir, file_name)
    shutil.copy2(local_cover_path, target_path)  # 保留原时间戳、权限
    image_relative_path = f"/static/{subfolder}/{file_name}".replace("\\", "/")
    url_path = f"{BACKEND_BASE_URL.rstrip('/')}/{image_relative_path.lstrip('/')}"
    # 返回前端可访问的路径
    return url_path
