import uuid
from datetime import datetime
from celery import current_app as celery_app
from celery.utils.log import get_task_logger

from app.db.scheduled_task_dao import ScheduledTaskDAO
from app.services.note import NoteGenerator
from app.services.storage_cleanup import storage_cleanup
from app.enmus.note_enums import DownloadQuality

logger = get_task_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def check_and_execute_scheduled_tasks(self):
    """检查并执行到时的定时任务"""
    try:
        # 获取所有待执行的定时任务
        pending_tasks = ScheduledTaskDAO.get_pending_tasks()
        
        logger.info(f"检查到 {len(pending_tasks)} 个待执行的定时任务")
        
        for scheduled_task in pending_tasks:
            try:
                # 标记任务为运行中
                ScheduledTaskDAO.update_task_status(scheduled_task.id, "running")
                
                # 创建异步执行任务
                execute_scheduled_task.delay(scheduled_task.id)
                
            except Exception as e:
                logger.error(f"启动定时任务 {scheduled_task.id} 失败: {str(e)}")
                ScheduledTaskDAO.update_task_status(
                    scheduled_task.id, 
                    "failed", 
                    error_message=f"启动失败: {str(e)}"
                )
        
        return f"处理了 {len(pending_tasks)} 个定时任务"
        
    except Exception as e:
        logger.error(f"检查定时任务失败: {str(e)}")
        self.retry(countdown=60, exc=e)


@celery_app.task(bind=True, max_retries=2)
def execute_scheduled_task(self, scheduled_task_id: int):
    """执行单个定时任务"""
    try:
        # 获取定时任务详情
        scheduled_task = ScheduledTaskDAO.get_scheduled_task_by_id(scheduled_task_id)
        if not scheduled_task:
            logger.error(f"定时任务 {scheduled_task_id} 不存在")
            return
        
        if not scheduled_task.enabled:
            logger.info(f"定时任务 {scheduled_task_id} 已被禁用，跳过执行")
            ScheduledTaskDAO.update_task_status(scheduled_task_id, "cancelled")
            return
        
        logger.info(f"开始执行定时任务: {scheduled_task.task_name} (ID: {scheduled_task_id})")
        
        # 生成新的任务ID用于笔记生成
        task_id = str(uuid.uuid4())
        
        # 从配置中获取参数
        config = scheduled_task.task_config or {}
        
        # 调用笔记生成服务
        note_generator = NoteGenerator()
        note = note_generator.generate(
            video_url=scheduled_task.video_url,
            platform=scheduled_task.platform,
            quality=DownloadQuality(config.get("quality", "medium")),
            task_id=task_id,
            model_name=config.get("model_name"),
            provider_id=config.get("provider_id"),
            link=config.get("link", False),
            _format=config.get("format", []),
            style=config.get("style", "minimal"),
            extras=config.get("extras"),
            screenshot=config.get("screenshot", False),
            video_understanding=config.get("video_understanding", False),
            video_interval=config.get("video_interval", 4),
            grid_size=config.get("grid_size", [3, 3])
        )
        
        if note and note.markdown:
            # 执行成功
            ScheduledTaskDAO.update_task_status(
                scheduled_task_id, 
                "completed", 
                last_task_id=task_id
            )
            logger.info(f"定时任务 {scheduled_task_id} 执行成功，生成笔记任务 {task_id}")
        else:
            # 执行失败
            ScheduledTaskDAO.update_task_status(
                scheduled_task_id, 
                "failed", 
                error_message="笔记生成失败",
                last_task_id=task_id
            )
            logger.warning(f"定时任务 {scheduled_task_id} 执行失败：笔记生成失败")
        
        return f"定时任务 {scheduled_task_id} 执行完成"
        
    except Exception as e:
        logger.error(f"执行定时任务 {scheduled_task_id} 失败: {str(e)}")
        
        # 更新任务状态为失败
        ScheduledTaskDAO.update_task_status(
            scheduled_task_id, 
            "failed", 
            error_message=str(e)
        )
        
        # 如果还有重试次数，则重试
        if self.request.retries < self.max_retries:
            logger.info(f"将在 5 分钟后重试定时任务 {scheduled_task_id}")
            self.retry(countdown=300, exc=e)
        else:
            logger.error(f"定时任务 {scheduled_task_id} 重试次数用尽，最终失败")
            return f"定时任务 {scheduled_task_id} 执行失败: {str(e)}"


@celery_app.task(bind=True)
def cleanup_media_files(self, max_age_hours: int = 24):
    """
    定期清理所有音视频文件
    
    Args:
        max_age_hours: 文件最大保留时间（小时），默认24小时
    """
    try:
        logger.info(f"开始定期清理音视频文件（保留最近{max_age_hours}小时的文件）")
        result = storage_cleanup.cleanup_all_media_files(max_age_hours=max_age_hours)
        logger.info(f"定期清理完成: 成功删除 {result.get('deleted', 0)} 个文件, 失败 {result.get('failed', 0)} 个文件")
        return f"清理完成: 删除 {result.get('deleted', 0)} 个文件"
    except Exception as e:
        logger.error(f"定期清理音视频文件失败: {str(e)}")
        self.retry(countdown=60, exc=e)


@celery_app.task
def emergency_cleanup(max_size_mb: int = 1000):
    """
    紧急清理：当存储超过指定大小时强制清理
    
    Args:
        max_size_mb: 最大存储大小（MB），默认1000MB
    """
    try:
        logger.info(f"开始紧急清理（阈值: {max_size_mb}MB）")
        result = storage_cleanup.emergency_cleanup(max_size_mb=max_size_mb)
        if result:
            logger.info(f"紧急清理完成: {result}")
            return f"紧急清理完成"
        else:
            logger.info(f"存储空间未超过阈值，无需紧急清理")
            return "无需紧急清理"
    except Exception as e:
        logger.error(f"紧急清理失败: {str(e)}")
        return f"紧急清理失败: {str(e)}"