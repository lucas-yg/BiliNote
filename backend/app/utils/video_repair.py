"""
视频修复和验证工具
用于处理损坏的视频文件和提供健壮的音频提取
"""
import os
import subprocess
import tempfile
import shutil
from typing import Optional, Tuple, Dict
import json
import logging

logger = logging.getLogger(__name__)


class VideoRepairTool:
    """视频修复工具"""
    
    def __init__(self):
        self.temp_dir = None
        
    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="video_repair_")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def validate_video(self, video_path: str) -> Tuple[bool, Dict]:
        """
        验证视频文件完整性
        返回: (是否有效, 视频信息)
        """
        try:
            # 使用ffprobe检查视频信息
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"视频验证失败: {result.stderr}")
                return False, {"error": result.stderr}
            
            info = json.loads(result.stdout)
            
            # 检查是否有视频流
            has_video = any(
                stream.get('codec_type') == 'video' 
                for stream in info.get('streams', [])
            )
            
            # 检查是否有音频流
            has_audio = any(
                stream.get('codec_type') == 'audio' 
                for stream in info.get('streams', [])
            )
            
            return True, {
                "has_video": has_video,
                "has_audio": has_audio,
                "format": info.get('format', {}),
                "streams": info.get('streams', [])
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"视频验证超时: {video_path}")
            return False, {"error": "验证超时"}
        except json.JSONDecodeError as e:
            logger.error(f"解析视频信息失败: {e}")
            return False, {"error": "信息解析失败"}
        except Exception as e:
            logger.error(f"视频验证异常: {e}")
            return False, {"error": str(e)}
    
    def repair_video(self, input_path: str, output_path: str) -> bool:
        """
        尝试修复损坏的视频文件
        """
        try:
            logger.info(f"尝试修复视频: {input_path}")
            
            # 使用ffmpeg的错误恢复选项重新编码视频
            cmd = [
                'ffmpeg',
                '-err_detect', 'ignore_err',  # 忽略错误
                '-i', input_path,
                '-c:v', 'libx264',           # 重新编码视频
                '-c:a', 'aac',               # 重新编码音频
                '-avoid_negative_ts', 'make_zero',  # 避免负时间戳
                '-fflags', '+genpts',        # 生成PTS
                '-r', '25',                  # 固定帧率
                '-y',                        # 覆盖输出
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"视频修复成功: {output_path}")
                return True
            else:
                logger.warning(f"视频修复失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("视频修复超时")
            return False
        except Exception as e:
            logger.error(f"视频修复异常: {e}")
            return False
    
    def extract_audio_robust(
        self, 
        video_path: str, 
        audio_path: str, 
        bitrate: str = "128k"
    ) -> bool:
        """
        健壮的音频提取，支持损坏视频
        """
        try:
            # 首先验证视频
            is_valid, info = self.validate_video(video_path)
            
            if not is_valid:
                logger.warning(f"视频文件可能已损坏，尝试强制提取音频: {video_path}")
            elif not info.get("has_audio"):
                logger.error(f"视频文件不包含音频流: {video_path}")
                return False
            
            # 构建强健的ffmpeg命令
            cmd = [
                'ffmpeg',
                '-err_detect', 'ignore_err',     # 忽略解码错误
                '-fflags', '+discardcorrupt',    # 丢弃损坏的包
                '-i', video_path,
                '-vn',                           # 不处理视频
                '-acodec', 'mp3',               # 音频编码
                '-ab', bitrate,                 # 比特率
                '-ar', '22050',                 # 采样率
                '-ac', '1',                     # 单声道 (减少处理复杂度)
                '-avoid_negative_ts', 'make_zero',  # 避免时间戳问题
                '-y',                           # 覆盖输出
                audio_path
            ]
            
            logger.info(f"执行健壮音频提取: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            # 检查结果
            if result.returncode == 0 and os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                if file_size > 1024:  # 至少1KB
                    logger.info(f"音频提取成功: {audio_path} ({file_size} bytes)")
                    return True
                else:
                    logger.warning("提取的音频文件过小，可能为空")
                    return False
            else:
                # 如果标准方法失败，尝试更激进的参数
                logger.warning("标准音频提取失败，尝试激进模式")
                return self._extract_audio_aggressive(video_path, audio_path, bitrate)
                
        except subprocess.TimeoutExpired:
            logger.error("音频提取超时")
            return False
        except Exception as e:
            logger.error(f"音频提取异常: {e}")
            return False
    
    def _extract_audio_aggressive(
        self, 
        video_path: str, 
        audio_path: str, 
        bitrate: str
    ) -> bool:
        """
        激进模式音频提取，用于处理严重损坏的视频
        """
        try:
            logger.info("使用激进模式提取音频")
            
            # 更激进的参数
            cmd = [
                'ffmpeg',
                '-f', 'mp4',                    # 强制输入格式
                '-err_detect', 'ignore_err',
                '-fflags', '+discardcorrupt+igndts+ignidx',  # 忽略更多错误
                '-i', video_path,
                '-vn',
                '-acodec', 'mp3',
                '-ab', '64k',                   # 降低比特率
                '-ar', '16000',                 # 降低采样率
                '-ac', '1',                     # 单声道
                '-map', '0:a?',                 # 尝试映射任何音频流
                '-ignore_unknown',              # 忽略未知流
                '-y',
                audio_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0 and os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                if file_size > 512:  # 至少512字节
                    logger.info(f"激进模式音频提取成功: {file_size} bytes")
                    return True
            
            logger.error(f"激进模式也失败了: {result.stderr}")
            return False
            
        except Exception as e:
            logger.error(f"激进模式音频提取异常: {e}")
            return False
    
    def get_video_duration(self, video_path: str) -> Optional[float]:
        """
        获取视频时长，支持损坏视频
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
            
            return None
            
        except Exception as e:
            logger.warning(f"获取视频时长失败: {e}")
            return None


def safe_extract_audio(
    video_path: str, 
    audio_path: str, 
    bitrate: str = "128k",
    repair_if_needed: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    安全的音频提取函数，自动处理损坏视频
    
    返回: (是否成功, 错误信息或None)
    """
    if not os.path.exists(video_path):
        return False, f"视频文件不存在: {video_path}"
    
    try:
        with VideoRepairTool() as repair_tool:
            # 直接尝试提取音频
            if repair_tool.extract_audio_robust(video_path, audio_path, bitrate):
                return True, None
            
            # 如果失败且允许修复，尝试修复后再提取
            if repair_if_needed:
                logger.info("尝试修复视频后重新提取音频")
                
                # 创建修复后的临时视频文件
                repaired_video = os.path.join(
                    repair_tool.temp_dir, 
                    f"repaired_{os.path.basename(video_path)}"
                )
                
                if repair_tool.repair_video(video_path, repaired_video):
                    # 从修复后的视频提取音频
                    if repair_tool.extract_audio_robust(repaired_video, audio_path, bitrate):
                        return True, None
                    else:
                        return False, "修复后仍无法提取音频"
                else:
                    return False, "视频修复失败"
            
            return False, "音频提取失败"
            
    except Exception as e:
        logger.error(f"安全音频提取过程异常: {e}")
        return False, f"处理异常: {str(e)}"


def validate_and_repair_video(video_path: str) -> Tuple[bool, str, Dict]:
    """
    验证并修复视频文件
    
    返回: (是否成功, 处理后的文件路径, 视频信息)
    """
    try:
        with VideoRepairTool() as repair_tool:
            is_valid, info = repair_tool.validate_video(video_path)
            
            if is_valid:
                return True, video_path, info
            
            # 需要修复
            logger.info(f"视频需要修复: {video_path}")
            
            # 创建修复文件路径
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            repaired_path = os.path.join(video_dir, f"{video_name}_repaired.mp4")
            
            if repair_tool.repair_video(video_path, repaired_path):
                # 验证修复结果
                is_repaired_valid, repaired_info = repair_tool.validate_video(repaired_path)
                if is_repaired_valid:
                    return True, repaired_path, repaired_info
                else:
                    # 修复失败，但可能仍可以使用原文件进行处理
                    return False, video_path, info
            else:
                return False, video_path, info
                
    except Exception as e:
        logger.error(f"视频验证修复异常: {e}")
        return False, video_path, {"error": str(e)}