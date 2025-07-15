"""
存储清理定时任务
使用Celery定时执行存储清理，防止磁盘空间无限增长
"""
import logging
from celery import Celery
from app.core.celery_app import celery_app
from app.services.storage_cleanup import storage_cleanup

logger = logging.getLogger(__name__)

@celery_app.task(name="storage_cleanup_task")
def storage_cleanup_task():
    """
    定时存储清理任务
    建议每天凌晨2点运行：0 2 * * *
    """
    try:
        logger.info("开始执行存储清理任务...")
        
        # 获取清理前的存储使用情况
        before_usage = storage_cleanup.get_storage_usage()
        total_before = sum(info["size_mb"] for info in before_usage.values())
        
        # 执行清理
        cleanup_result = storage_cleanup.cleanup_old_files()
        
        # 获取清理后的存储使用情况
        after_usage = storage_cleanup.get_storage_usage()
        total_after = sum(info["size_mb"] for info in after_usage.values())
        
        # 计算清理效果
        space_freed = total_before - total_after
        
        logger.info(f"存储清理完成！释放空间: {space_freed:.2f}MB")
        logger.info(f"清理前: {total_before:.2f}MB -> 清理后: {total_after:.2f}MB")
        
        # 记录详细清理信息
        for directory, result in cleanup_result.items():
            if result["files_deleted"] > 0:
                logger.info(f"{directory}: 删除 {result['files_deleted']} 个文件, "
                           f"释放 {result['space_freed']/(1024*1024):.2f}MB")
        
        # 检查是否需要紧急清理
        if total_after > 2000:  # 如果清理后仍超过2GB
            logger.warning("存储空间仍然过大，执行紧急清理...")
            emergency_result = storage_cleanup.emergency_cleanup(1000)
            if emergency_result:
                logger.info("紧急清理完成")
        
        return {
            "success": True,
            "space_freed_mb": space_freed,
            "before_usage": before_usage,
            "after_usage": after_usage,
            "cleanup_details": cleanup_result
        }
        
    except Exception as e:
        logger.error(f"存储清理任务失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@celery_app.task(name="emergency_storage_cleanup")
def emergency_storage_cleanup_task(max_size_mb: int = 1000):
    """
    紧急存储清理任务
    当存储空间超过指定大小时立即执行
    """
    try:
        logger.warning(f"执行紧急存储清理，最大允许大小: {max_size_mb}MB")
        
        result = storage_cleanup.emergency_cleanup(max_size_mb)
        
        if result:
            logger.info("紧急清理完成")
            return {"success": True, "cleanup_result": result}
        else:
            logger.info("存储空间正常，无需紧急清理")
            return {"success": True, "message": "No cleanup needed"}
            
    except Exception as e:
        logger.error(f"紧急存储清理失败: {e}")
        return {"success": False, "error": str(e)}

@celery_app.task(name="storage_usage_check")
def storage_usage_check_task():
    """
    存储使用情况检查任务
    用于监控存储使用情况
    """
    try:
        usage = storage_cleanup.get_storage_usage()
        total_mb = sum(info["size_mb"] for info in usage.values())
        
        logger.info(f"当前存储使用情况: {total_mb:.2f}MB")
        
        # 如果超过阈值，发送告警
        if total_mb > 2000:  # 2GB阈值
            logger.warning(f"存储空间过大: {total_mb:.2f}MB，建议执行清理")
            
            # 自动触发紧急清理
            emergency_storage_cleanup_task.delay(1000)
        
        return {
            "success": True,
            "total_usage_mb": total_mb,
            "usage_details": usage
        }
        
    except Exception as e:
        logger.error(f"存储使用情况检查失败: {e}")
        return {"success": False, "error": str(e)}