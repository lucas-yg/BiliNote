import os
import subprocess
from abc import ABC
from typing import Optional

from app.downloaders.base import Downloader
from app.enmus.note_enums import DownloadQuality
from app.models.audio_model import AudioDownloadResult
import os
import subprocess

from app.utils.video_helper import save_cover_to_static


class LocalDownloader(Downloader, ABC):
    def __init__(self):

        super().__init__()


    def extract_cover(self, input_path: str, output_dir: Optional[str] = None) -> str:
        """
        从本地视频文件中提取一张封面图，支持损坏视频
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")

        if output_dir is None:
            output_dir = os.path.dirname(input_path)

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_cover.jpg")

        # 使用增强的ffmpeg命令，支持损坏视频
        command = [
            'ffmpeg',
            '-err_detect', 'ignore_err',        # 忽略解码错误
            '-fflags', '+discardcorrupt',       # 丢弃损坏的包
            '-ss', '00:00:01',                  # 跳到视频第1秒，防止黑屏
            '-i', input_path,
            '-vframes', '1',                    # 只截取一帧
            '-q:v', '2',                        # 高质量
            '-avoid_negative_ts', 'make_zero',  # 避免负时间戳
            '-y',                               # 覆盖
            output_path
        ]

        try:
            result = subprocess.run(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                timeout=30,
                check=False
            )

            if result.returncode != 0:
                print(f"封面提取失败，尝试备用方案: {result.stderr}")
                # 尝试更宽松的参数
                fallback_command = [
                    'ffmpeg',
                    '-err_detect', 'ignore_err',
                    '-fflags', '+discardcorrupt+igndts',
                    '-ss', '00:00:00.5',               # 更早的时间点
                    '-i', input_path,
                    '-vframes', '1',
                    '-vf', 'scale=640:-1',             # 缩放减少处理复杂度
                    '-q:v', '5',                       # 降低质量要求
                    '-y',
                    output_path
                ]
                
                fallback_result = subprocess.run(
                    fallback_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                    check=False
                )
                
                if fallback_result.returncode != 0:
                    # 如果都失败了，创建占位图
                    from app.utils.video_helper import _create_placeholder_image
                    return _create_placeholder_image(output_path, "无法提取封面")

            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                from app.utils.video_helper import _create_placeholder_image
                return _create_placeholder_image(output_path, "封面提取失败")

            return output_path
            
        except subprocess.TimeoutExpired:
            from app.utils.video_helper import _create_placeholder_image
            return _create_placeholder_image(output_path, "封面提取超时")
        except Exception as e:
            print(f"提取封面异常: {e}")
            from app.utils.video_helper import _create_placeholder_image
            return _create_placeholder_image(output_path, "封面提取异常")

    def convert_to_mp3(self, input_path: str, output_path: str = None) -> str:
        """
        将本地视频文件转为 MP3 音频文件，支持损坏视频
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")

        if output_path is None:
            base, _ = os.path.splitext(input_path)
            output_path = base + ".mp3"

        # 使用安全的音频提取工具
        from app.utils.video_repair import safe_extract_audio
        
        success, error_msg = safe_extract_audio(
            input_path,
            output_path,
            bitrate="128k",
            repair_if_needed=True
        )
        
        if success:
            print(f"音频转换成功: {output_path}")
            return output_path
        else:
            raise RuntimeError(f"音频转换失败: {error_msg}")
    def download_video(self, video_url: str, output_dir: str = None) -> str:
        """
        处理本地文件路径，返回视频文件路径
        """
        if video_url.startswith('/uploads'):
            project_root = os.getcwd()
            video_url = os.path.join(project_root, video_url.lstrip('/'))
            video_url = os.path.normpath(video_url)

        if not os.path.exists(video_url):
            raise FileNotFoundError()
        return video_url
    def download(
            self,
            video_url: str,
            output_dir: str = None,
            quality: DownloadQuality = "fast",
            need_video: Optional[bool] = False
    ) -> AudioDownloadResult:
        """
        处理本地文件路径，返回音频元信息
        """
        if video_url.startswith('/uploads'):
            project_root = os.getcwd()
            video_url = os.path.join(project_root, video_url.lstrip('/'))
            video_url = os.path.normpath(video_url)

        if not os.path.exists(video_url):
            raise FileNotFoundError(f"本地文件不存在: {video_url}")

        file_name = os.path.basename(video_url)
        title, _ = os.path.splitext(file_name)
        print(title, file_name,video_url)
        file_path=self.convert_to_mp3(video_url)
        cover_path = self.extract_cover(video_url)
        cover_url = save_cover_to_static(cover_path)

        print('file——path',file_path)
        return AudioDownloadResult(
            file_path=file_path,
            title=title,
            duration=0,  # 可选：后续加上读取时长
            cover_url=cover_url,  # 暂无封面
            platform="local",
            video_id=title,
            raw_info={
                'path':  file_path
            },
            video_path=None
        )
