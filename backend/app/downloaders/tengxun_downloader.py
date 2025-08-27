import os
import re
import requests
import tempfile
import subprocess
from typing import Union, Optional
from urllib.parse import urlparse, parse_qs

from app.downloaders.base import Downloader
from app.enmus.note_enums import DownloadQuality
from app.models.audio_model import AudioDownloadResult
from app.utils.path_helper import get_data_dir


class TengxunDownloader(Downloader):
    def __init__(self):
        super().__init__()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://v.qq.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def extract_video_id(self, url: str) -> str:
        """从腾讯视频URL中提取视频ID"""
        try:
            # 处理不同类型的腾讯视频URL
            # 1. 普通播放页面 https://v.qq.com/x/page/xxxxx.html
            # 2. 分享链接 https://v.qq.com/x/cover/xxxxx/xxxxx.html  
            # 3. 下载链接 https://finder.video.qq.com/...
            
            if "finder.video.qq.com" in url:
                # 对于下载链接，从URL中提取相关参数作为ID
                parsed = urlparse(url)
                path_parts = parsed.path.split('/')
                if len(path_parts) >= 3:
                    return f"{path_parts[1]}_{path_parts[2]}"
                return "tengxun_video"
            
            # 对于普通播放链接
            patterns = [
                r'/x/page/([^/]+)\.html',
                r'/x/cover/[^/]+/([^/]+)\.html',
                r'vid=([^&]+)',
                r'/([a-zA-Z0-9]{10,})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # 如果都匹配不到，生成一个默认ID
            return "tengxun_" + str(hash(url))[-8:]
            
        except Exception as e:
            print(f"提取视频ID失败: {e}")
            return "tengxun_video"

    def _is_direct_video_link(self, url: str) -> bool:
        """判断是否为直接的视频文件链接"""
        try:
            # 检查URL是否直接指向视频文件
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.webm', '.m4v']
            url_lower = url.lower()
            
            # 检查文件扩展名
            for ext in video_extensions:
                if ext in url_lower:
                    return True
            
            # 检查Content-Type（发送HEAD请求）
            try:
                response = requests.head(url, headers=self.headers, timeout=10)
                content_type = response.headers.get('content-type', '').lower()
                if 'video/' in content_type:
                    return True
            except:
                pass  # 如果HEAD请求失败，继续其他检查
                
            # 检查是否为已知的直链域名模式
            direct_patterns = [
                'cdn.',
                'static.',
                'video.',
                'media.',
                '/uploads/',
                '/videos/',
                '/media/',
            ]
            
            for pattern in direct_patterns:
                if pattern in url_lower:
                    return True
                    
            return False
            
        except Exception as e:
            print(f"检查链接类型失败: {e}")
            return False

    def download(
        self,
        video_url: str,
        output_dir: Union[str, None] = None,
        quality: DownloadQuality = "fast",
        need_video: Optional[bool] = False
    ) -> AudioDownloadResult:
        """流式处理腾讯视频，不保存完整视频到本地"""
        try:
            print(f"正在处理腾讯视频: {video_url}，质量: {quality}")
            
            if output_dir is None:
                output_dir = get_data_dir()
            if not output_dir:
                output_dir = self.cache_data
            os.makedirs(output_dir, exist_ok=True)

            video_id = self.extract_video_id(video_url)
            
            # 关键检查：拒绝处理finder.video.qq.com加密链接
            if "finder.video.qq.com" in video_url:
                raise Exception(
                    "检测到微信加密视频链接，无法直接处理。\n\n"
                    "💡 解决方案：\n"
                    "1. 使用 res-downloader 工具：\n"
                    "   - 下载：https://github.com/putyy/res-downloader\n"
                    "   - 启动代理模式，在微信中播放视频\n"
                    "   - 获取真实的视频链接后再使用\n\n"
                    "2. 或者使用其他平台的视频：\n"
                    "   - 哔哩哔哩、YouTube、抖音等\n"
                    "   - 这些平台可以直接处理\n\n"
                    "3. 如果是腾讯视频，请使用 v.qq.com 的播放页面链接"
                )
            
            # 检查URL类型并选择处理方式
            if self._is_direct_video_link(video_url):
                # 直接的视频文件链接（MP4等）
                print("检测到直接视频链接，开始下载...")
                return self._stream_process_direct_link(video_url, output_dir, video_id, quality)
            else:
                # 播放页面链接，需要解析
                print("检测到播放页面链接，开始解析...")
                return self._stream_process_play_page(video_url, output_dir, video_id, quality)
                
        except Exception as e:
            print(f"流式处理失败: {e}")
            raise e

    def _stream_process_direct_link(self, video_url: str, output_dir: str, video_id: str, quality: DownloadQuality) -> AudioDownloadResult:
        """流式处理直接视频链接，只提取音频"""
        temp_video = None
        try:
            audio_path = os.path.join(output_dir, f"{video_id}.mp3")
            
            # 如果音频文件已存在，直接返回
            if os.path.exists(audio_path):
                return AudioDownloadResult(
                    file_path=audio_path,
                    title=f"视频_{video_id}",
                    duration=0,
                    cover_url="",
                    platform="tengxun",
                    video_id=video_id,
                    raw_info={'source_url': video_url, 'cached': True},
                    video_path=None
                )
            
            # 创建临时文件用于视频流
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_video = temp_file.name
                
                print("正在下载视频流...")
                response = requests.get(video_url, headers=self.headers, stream=True)
                response.raise_for_status()
                
                print(f"响应状态码: {response.status_code}")
                print(f"内容类型: {response.headers.get('content-type', 'unknown')}")
                
                # 流式写入临时文件
                bytes_downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        bytes_downloaded += len(chunk)
                
                print(f"下载完成，共下载 {bytes_downloaded} 字节")
            
            print("正在从视频流中提取音频...")
            # 使用ffmpeg直接从临时视频文件提取音频
            self._extract_audio_with_ffmpeg(temp_video, audio_path, quality)
            
            # 获取音频信息
            duration = self._get_audio_duration(audio_path)
            file_size = os.path.getsize(audio_path)
            
            return AudioDownloadResult(
                file_path=audio_path,
                title=f"视频_{video_id}",
                duration=duration,
                cover_url="",
                platform="tengxun",
                video_id=video_id,
                raw_info={
                    'source_url': video_url,
                    'audio_size': file_size,
                    'processing_method': 'stream'
                },
                video_path=None  # 不保存视频文件
            )
            
        except Exception as e:
            print(f"流式处理直接链接失败: {e}")
            raise e
        finally:
            # 清理临时视频文件
            if temp_video and os.path.exists(temp_video):
                try:
                    os.unlink(temp_video)
                    print("临时视频文件已清理")
                except Exception as cleanup_error:
                    print(f"清理临时文件失败: {cleanup_error}")

    def _stream_process_play_page(self, video_url: str, output_dir: str, video_id: str, quality: DownloadQuality) -> AudioDownloadResult:
        """流式处理播放页面"""
        try:
            # 获取播放页面
            response = requests.get(video_url, headers=self.headers)
            response.raise_for_status()
            html_content = response.text
            
            # 这里需要解析页面获取真实的视频下载链接
            # 腾讯视频的解析比较复杂，通常需要逆向分析其API
            # 暂时返回一个示例实现，表示不支持播放页面的流式处理
            
            raise ValueError("播放页面的流式解析暂未实现，请使用直接下载链接")
            
        except Exception as e:
            print(f"流式处理播放页面失败: {e}")
            raise e

    def _extract_audio_with_ffmpeg(self, video_path: str, audio_path: str, quality: DownloadQuality):
        """使用增强的ffmpeg从视频中提取音频，支持损坏视频修复"""
        from app.utils.video_repair import safe_extract_audio
        
        try:
            # 根据质量设置音频比特率
            quality_map = {
                "fast": "64k",    # 提高最低质量
                "medium": "128k", 
                "slow": "192k"    # 提高高质量设置
            }
            bitrate = quality_map.get(quality, "128k")
            
            print(f"开始提取音频: {video_path} -> {audio_path} (质量: {bitrate})")
            
            # 使用健壮的音频提取工具
            success, error_msg = safe_extract_audio(
                video_path, 
                audio_path, 
                bitrate=bitrate,
                repair_if_needed=True  # 允许自动修复
            )
            
            if success:
                file_size = os.path.getsize(audio_path)
                print(f"音频提取成功: {audio_path} ({file_size} bytes)")
            else:
                raise Exception(f"音频提取失败: {error_msg}")
            
        except FileNotFoundError:
            raise Exception("ffmpeg未安装或不在PATH中，请安装ffmpeg后重试")
        except Exception as e:
            error_msg = str(e)
            if "Invalid NAL unit size" in error_msg or "Error splitting the input into NAL units" in error_msg:
                raise Exception("视频文件已损坏，无法提取音频。请尝试使用其他视频文件或联系技术支持")
            elif "timeout" in error_msg.lower():
                raise Exception("音频提取超时，视频文件可能过大或已损坏")
            else:
                raise Exception(f"音频提取失败: {error_msg}")

    def _try_decrypt_wechat_video(self, encrypted_file: str, decrypted_file: str) -> bool:
        """尝试解密微信视频文件"""
        try:
            print("尝试解密微信视频文件...")
            
            # 检查文件大小
            file_size = os.path.getsize(encrypted_file)
            if file_size < 131072:  # 2^17 字节
                print("文件太小，可能不是加密的微信视频")
                return False
            
            # 简单的XOR解密尝试（基于已知模式）
            with open(encrypted_file, 'rb') as f_in:
                # 读取文件头部分析
                header = f_in.read(16)
                print(f"文件头: {header.hex()}")
                
                # 尝试简单的XOR密钥模式
                possible_keys = [
                    b'\x82\xcf\x2a\xe8',  # 从实际加密文件观察到的模式
                    b'\x00\x00\x00\x00',  # 空密钥测试
                ]
                
                for key in possible_keys:
                    f_in.seek(0)
                    test_data = f_in.read(16)
                    
                    # 尝试XOR解密
                    decrypted_test = bytes(test_data[i] ^ key[i % len(key)] for i in range(len(test_data)))
                    
                    # 检查是否为有效的MP4文件头
                    if b'ftyp' in decrypted_test:
                        print(f"找到可能的解密密钥: {key.hex()}")
                        return self._decrypt_with_key(encrypted_file, decrypted_file, key)
                        
            # 如果简单XOR失败，尝试其他方法
            print("简单XOR解密失败，尝试其他解密方法...")
            
            # 尝试跳过加密部分（有些视频只有开头部分加密）
            with open(encrypted_file, 'rb') as f_in:
                with open(decrypted_file, 'wb') as f_out:
                    # 跳过前面可能加密的部分，寻找有效的MP4数据
                    for offset in [0, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072]:
                        f_in.seek(offset)
                        test_data = f_in.read(16)
                        if b'ftyp' in test_data or b'mdat' in test_data:
                            print(f"在偏移 {offset} 处找到有效MP4数据")
                            f_in.seek(offset)
                            f_out.write(f_in.read())
                            return True
                            
            return False
            
        except Exception as e:
            print(f"解密过程出错: {e}")
            return False
    
    def _decrypt_with_key(self, encrypted_file: str, decrypted_file: str, key: bytes) -> bool:
        """使用指定密钥解密文件"""
        try:
            with open(encrypted_file, 'rb') as f_in:
                with open(decrypted_file, 'wb') as f_out:
                    # 解密前 131072 字节
                    encrypted_data = f_in.read(131072)
                    decrypted_data = bytes(encrypted_data[i] ^ key[i % len(key)] for i in range(len(encrypted_data)))
                    f_out.write(decrypted_data)
                    
                    # 剩余部分直接复制
                    remaining_data = f_in.read()
                    f_out.write(remaining_data)
                    
            print(f"解密完成: {decrypted_file}")
            return True
            
        except Exception as e:
            print(f"使用密钥解密失败: {e}")
            return False
    def _get_audio_duration(self, audio_path: str) -> int:
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return int(duration)
            else:
                return 0
                
        except Exception:
            return 0

    def download_video(self, video_url: str, output_dir: Union[str, None] = None) -> str:
        """注意：腾讯视频下载器采用流式处理，不保存视频文件到本地"""
        raise NotImplementedError("腾讯视频下载器采用流式处理策略，不支持保存完整视频文件到本地。如需视频内容，请使用音频转录功能。")


if __name__ == '__main__':
    # 测试代码
    downloader = TengxunDownloader()
    test_url = "https://finder.video.qq.com/251/20302/stodownload?encfilekey=rjD5jyTuFrIpZ2ibE8T7Ym3K77SEULgkiatib7VaS1RcMDbsqcdZUMAgjibsesfVfJ5iaBG9bB4AeK6SSDvGsibK1jbNDBbvicfbv1Bbib7k2r98fCbmYU6upALRfA"
    
    try:
        print("测试流式音频提取...")
        result = downloader.download(test_url)
        print(f"流式处理成功: {result.file_path}")
        print(f"音频时长: {result.duration}秒")
        print("注意：视频文件未保存到本地，仅保留音频文件")
    except Exception as e:
        print(f"测试失败: {e}")