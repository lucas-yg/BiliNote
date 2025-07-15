"""
存储清理服务
自动清理上传文件和处理缓存，防止磁盘空间无限增长
"""
import os
import time
import shutil
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StorageCleanupService:
    """存储清理服务"""
    
    def __init__(self, base_path: str = "backend"):
        self.base_path = Path(base_path)
        self.uploads_path = self.base_path / "uploads"
        self.data_path = self.base_path / "data"
        self.note_results_path = self.base_path / "note_results"
        
        # 默认保留策略（天数）
        self.default_retention = {
            "uploads": 7,           # 上传文件保留7天
            "data": 3,              # 处理数据保留3天
            "output_frames": 1,     # 截图帧保留1天
            "grid_output": 1,       # 网格截图保留1天
            "note_results": 7,      # 笔记结果保留7天
        }
    
    def cleanup_after_processing(self, task_id: str, keep_uploads: bool = False, uploaded_filename: str = None, video_path: Optional[Path] = None):
        """
        处理完成后立即清理相关文件
        
        Args:
            task_id: 任务ID
            keep_uploads: 是否保留上传文件
            uploaded_filename: 上传的文件名（用于清理上传文件）
            video_path: 下载的视频文件路径（需要清理）
        """
        try:
            # 清理任务相关的临时文件
            self._cleanup_task_files(task_id, keep_uploads, uploaded_filename, video_path)
            
            logger.info(f"任务 {task_id} 的临时文件已清理")
            
        except Exception as e:
            logger.error(f"清理任务 {task_id} 文件时出错: {e}")
    
    def _cleanup_task_files(self, task_id: str, keep_uploads: bool, uploaded_filename: str = None, video_path: Optional[Path] = None):
        """清理特定任务的文件"""
        # 清理下载的视频文件（优先处理）
        if video_path and video_path.exists():
            try:
                if video_path.is_file():
                    video_path.unlink()
                    logger.info(f"已删除下载的视频文件: {video_path}")
                elif video_path.is_dir():
                    shutil.rmtree(video_path)
                    logger.info(f"已删除下载的视频目录: {video_path}")
            except Exception as e:
                logger.warning(f"删除下载视频文件 {video_path} 失败: {e}")
        
        # 清理data目录中的任务相关文件
        for subdir in ["data", "output_frames", "grid_output"]:
            dir_path = self.data_path / subdir
            if dir_path.exists():
                for file_path in dir_path.glob(f"*{task_id}*"):
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                    except Exception as e:
                        logger.warning(f"删除文件 {file_path} 失败: {e}")
        
        # 清理note_results目录中的任务相关文件（音频、转写缓存等）
        if self.note_results_path.exists():
            for file_path in self.note_results_path.glob(f"{task_id}*"):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        logger.info(f"已删除任务文件: {file_path}")
                except Exception as e:
                    logger.warning(f"删除任务文件 {file_path} 失败: {e}")
        
        # 清理上传文件
        if not keep_uploads and self.uploads_path.exists():
            # 1. 根据task_id匹配的文件
            for file_path in self.uploads_path.glob(f"*{task_id}*"):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        logger.info(f"已删除上传文件: {file_path}")
                except Exception as e:
                    logger.warning(f"删除上传文件 {file_path} 失败: {e}")
            
            # 2. 根据具体文件名删除上传文件
            if uploaded_filename:
                file_path = self.uploads_path / uploaded_filename
                if file_path.exists():
                    try:
                        file_path.unlink()
                        logger.info(f"已删除上传文件: {file_path}")
                    except Exception as e:
                        logger.warning(f"删除上传文件 {file_path} 失败: {e}")
        
        # 清理任务相关的其他视频文件（可能在根目录或其他位置）
        root_path = self.base_path
        for ext in [".mp4", ".avi", ".mkv", ".mov", ".flv", ".webm", ".wav", ".mp3", ".m4a"]:
            for file_path in root_path.glob(f"*{task_id}*{ext}"):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        logger.info(f"已删除视频/音频文件: {file_path}")
                except Exception as e:
                    logger.warning(f"删除视频/音频文件 {file_path} 失败: {e}")
    
    def cleanup_old_files(self, custom_retention: Optional[dict] = None):
        """
        清理过期文件
        
        Args:
            custom_retention: 自定义保留策略
        """
        retention_policy = self.default_retention.copy()
        if custom_retention:
            retention_policy.update(custom_retention)
        
        cleaned_info = {}
        
        # 清理uploads目录
        if self.uploads_path.exists():
            cleaned_info["uploads"] = self._cleanup_directory(
                self.uploads_path, 
                retention_policy["uploads"]
            )
        
        # 清理data子目录
        for subdir in ["data", "output_frames", "grid_output"]:
            dir_path = self.data_path / subdir
            if dir_path.exists():
                cleaned_info[subdir] = self._cleanup_directory(
                    dir_path, 
                    retention_policy.get(subdir, retention_policy["data"])
                )
        
        # 清理note_results目录
        if self.note_results_path.exists():
            cleaned_info["note_results"] = self._cleanup_directory(
                self.note_results_path, 
                retention_policy["note_results"]
            )
        
        return cleaned_info
    
    def _cleanup_directory(self, directory: Path, retention_days: int) -> dict:
        """
        清理指定目录中的过期文件
        
        Args:
            directory: 目录路径
            retention_days: 保留天数
            
        Returns:
            清理统计信息
        """
        if not directory.exists():
            return {"before_size": 0, "after_size": 0, "files_deleted": 0}
        
        # 计算截止时间
        cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
        
        # 统计清理前的大小
        before_size = self._get_directory_size(directory)
        files_deleted = 0
        
        # 遍历并删除过期文件
        for file_path in directory.rglob("*"):
            try:
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    files_deleted += 1
            except Exception as e:
                logger.warning(f"删除文件 {file_path} 失败: {e}")
        
        # 删除空目录
        for dir_path in directory.rglob("*"):
            try:
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
            except Exception as e:
                logger.warning(f"删除空目录 {dir_path} 失败: {e}")
        
        # 统计清理后的大小
        after_size = self._get_directory_size(directory)
        
        return {
            "before_size": before_size,
            "after_size": after_size,
            "files_deleted": files_deleted,
            "space_freed": before_size - after_size
        }
    
    def _get_directory_size(self, directory: Path) -> int:
        """计算目录大小（字节）"""
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"计算目录大小失败 {directory}: {e}")
        return total_size
    
    def get_storage_usage(self) -> dict:
        """获取存储使用情况"""
        usage = {}
        
        directories = [
            ("uploads", self.uploads_path),
            ("data", self.data_path),
            ("note_results", self.note_results_path),
        ]
        
        for name, path in directories:
            if path.exists():
                size = self._get_directory_size(path)
                usage[name] = {
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "files_count": len(list(path.rglob("*")))
                }
            else:
                usage[name] = {"size_bytes": 0, "size_mb": 0, "files_count": 0}
        
        return usage
    
    def emergency_cleanup(self, max_size_mb: int = 1000):
        """
        紧急清理：当存储超过指定大小时强制清理
        
        Args:
            max_size_mb: 最大存储大小（MB）
        """
        usage = self.get_storage_usage()
        total_size_mb = sum(info["size_mb"] for info in usage.values())
        
        if total_size_mb > max_size_mb:
            logger.warning(f"存储空间过大 ({total_size_mb}MB > {max_size_mb}MB)，开始紧急清理")
            
            # 更激进的清理策略
            aggressive_retention = {
                "uploads": 1,           # 只保留1天
                "data": 1,              # 只保留1天
                "output_frames": 0,     # 立即清理
                "grid_output": 0,       # 立即清理
                "note_results": 3,      # 保留3天
            }
            
            return self.cleanup_old_files(aggressive_retention)
        
        return None

# 全局实例
storage_cleanup = StorageCleanupService()