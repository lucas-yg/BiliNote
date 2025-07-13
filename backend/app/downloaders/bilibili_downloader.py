import os
from abc import ABC
from typing import Union, Optional
import random
import time
import logging

import yt_dlp
# 导入youtube-dl作为备选
import youtube_dl

from app.downloaders.base import Downloader, DownloadQuality, QUALITY_MAP
from app.models.notes_model import AudioDownloadResult
from app.utils.path_helper import get_data_dir
from app.utils.url_parser import extract_video_id


class BilibiliDownloader(Downloader, ABC):
    def __init__(self):
        super().__init__()

    def download(
        self,
        video_url: str,
        output_dir: Union[str, None] = None,
        quality: DownloadQuality = "fast",
        need_video:Optional[bool]=False
    ) -> AudioDownloadResult:
        if output_dir is None:
            output_dir = get_data_dir()
        if not output_dir:
            output_dir=self.cache_data
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, "%(id)s.%(ext)s")
        
        # 常见浏览器 User-Agent 列表
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0'
        ]
        
        # 随机选择一个User-Agent
        user_agent = random.choice(user_agents)

        # 尝试使用yt-dlp
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '64',
                }
            ],
            'noplaylist': True,
            'quiet': False,
            # 添加重试和连接设置
            'retries': 10,             # 重试10次
            'fragment_retries': 10,    # 片段下载重试10次
            'socket_timeout': 30,      # 套接字超时时间30秒
            'extractor_retries': 5,    # 提取器重试5次
            'nocheckcertificate': True, # 不检查SSL证书
            'http_headers': {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://www.bilibili.com/',
                'Origin': 'https://www.bilibili.com'
            }
        }

        info = None
        try:
            print("尝试使用 yt-dlp 下载...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"正在使用User-Agent: {user_agent}")
                print(f"尝试下载视频: {video_url}")
                info = ydl.extract_info(video_url, download=True)
                video_id = info.get("id")
                title = info.get("title")
                duration = info.get("duration", 0)
                cover_url = info.get("thumbnail")
                audio_path = os.path.join(output_dir, f"{video_id}.mp3")
                print(f"下载成功: {title}")
        except Exception as e:
            print(f"yt-dlp 下载失败，错误信息: {str(e)}")
            print("尝试使用备选下载器 youtube-dl...")
            
            # 失败后尝试使用 youtube_dl
            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    print(f"正在使用 youtube-dl 下载: {video_url}")
                    info = ydl.extract_info(video_url, download=True)
                    video_id = info.get("id")
                    title = info.get("title")
                    duration = info.get("duration", 0)
                    cover_url = info.get("thumbnail")
                    audio_path = os.path.join(output_dir, f"{video_id}.mp3")
                    print(f"youtube-dl 下载成功: {title}")
            except Exception as e2:
                print(f"youtube-dl 也下载失败，错误信息: {str(e2)}")
                raise Exception(f"所有下载方法都失败: yt-dlp错误: {str(e)}, youtube-dl错误: {str(e2)}")

        if not info:
            raise Exception("无法获取视频信息")
            
        # 检查下载是否成功
        video_id = info.get("id")
        audio_path = os.path.join(output_dir, f"{video_id}.mp3")
        
        # 等待5秒确保文件写入完成
        for _ in range(5):
            if os.path.exists(audio_path):
                break
            print(f"等待文件写入: {audio_path}")
            time.sleep(1)

        if not os.path.exists(audio_path):
            print(f"警告：下载可能成功但找不到文件: {audio_path}")
            
        return AudioDownloadResult(
            file_path=audio_path,
            title=info.get("title"),
            duration=info.get("duration", 0),
            cover_url=info.get("thumbnail"),
            platform="bilibili",
            video_id=video_id,
            raw_info=info,
            video_path=None  # ❗音频下载不包含视频路径
        )

    def download_video(
        self,
        video_url: str,
        output_dir: Union[str, None] = None,
    ) -> str:
        """
        下载视频，返回视频文件路径
        """

        if output_dir is None:
            output_dir = get_data_dir()
        os.makedirs(output_dir, exist_ok=True)
        print("video_url",video_url)
        video_id=extract_video_id(video_url, "bilibili")
        video_path = os.path.join(output_dir, f"{video_id}.mp4")
        if os.path.exists(video_path):
            return video_path

        # 常见浏览器 User-Agent 列表
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0'
        ]
        
        # 随机选择一个User-Agent
        user_agent = random.choice(user_agents)

        output_path = os.path.join(output_dir, "%(id)s.%(ext)s")

        ydl_opts = {
            'format': 'bv*[ext=mp4]/bestvideo+bestaudio/best',
            'outtmpl': output_path,
            'noplaylist': True,
            'quiet': False,
            'merge_output_format': 'mp4',  # 确保合并成 mp4
            # 添加重试和连接设置
            'retries': 10,             # 重试10次
            'fragment_retries': 10,    # 片段下载重试10次
            'socket_timeout': 30,      # 套接字超时时间30秒
            'extractor_retries': 5,    # 提取器重试5次
            'nocheckcertificate': True, # 不检查SSL证书
            'http_headers': {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://www.bilibili.com/',
                'Origin': 'https://www.bilibili.com'
            }
        }

        info = None
        try:
            print("尝试使用 yt-dlp 下载视频...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"正在使用User-Agent: {user_agent}")
                print(f"尝试下载视频: {video_url}")
                info = ydl.extract_info(video_url, download=True)
                video_id = info.get("id")
                video_path = os.path.join(output_dir, f"{video_id}.mp4")
                print(f"下载成功: {video_path}")
        except Exception as e:
            print(f"yt-dlp 下载视频失败，错误信息: {str(e)}")
            print("尝试使用备选下载器 youtube-dl...")
            
            # 失败后尝试使用 youtube_dl
            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    print(f"正在使用 youtube-dl 下载视频: {video_url}")
                    info = ydl.extract_info(video_url, download=True)
                    video_id = info.get("id")
                    video_path = os.path.join(output_dir, f"{video_id}.mp4")
                    print(f"youtube-dl 下载视频成功: {video_path}")
            except Exception as e2:
                print(f"youtube-dl 也下载视频失败，错误信息: {str(e2)}")
                raise Exception(f"所有下载视频方法都失败: yt-dlp错误: {str(e)}, youtube-dl错误: {str(e2)}")

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件未找到: {video_path}")

        return video_path

    def delete_video(self, video_path: str) -> str:
        """
        删除视频文件
        """
        if os.path.exists(video_path):
            os.remove(video_path)
            return f"视频文件已删除: {video_path}"
        else:
            return f"视频文件未找到: {video_path}"