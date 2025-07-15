from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.engine import get_db
from app.db.models.scheduled_tasks import ScheduledTask


class ScheduledTaskDAO:
    """定时任务数据访问对象"""
    
    @staticmethod
    def create_scheduled_task(
        task_name: str,
        video_url: str, 
        platform: str,
        schedule_time: datetime,
        task_config: dict,
        repeat_type: str = "once",
        enabled: bool = True,
        created_by: str = "user"
    ) -> ScheduledTask:
        """创建定时任务"""
        with get_db() as db:
            scheduled_task = ScheduledTask(
                task_name=task_name,
                video_url=video_url,
                platform=platform,
                schedule_time=schedule_time,
                repeat_type=repeat_type,
                enabled=enabled,
                task_config=task_config,
                next_run_time=schedule_time,
                created_by=created_by
            )
            db.add(scheduled_task)
            db.commit()
            db.refresh(scheduled_task)
            return scheduled_task
    
    @staticmethod
    def get_scheduled_task_by_id(task_id: int) -> Optional[ScheduledTask]:
        """根据ID获取定时任务"""
        with get_db() as db:
            return db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    
    @staticmethod
    def get_user_scheduled_tasks(created_by: str = "user", enabled_only: bool = False) -> List[ScheduledTask]:
        """获取用户的定时任务列表"""
        with get_db() as db:
            query = db.query(ScheduledTask).filter(ScheduledTask.created_by == created_by)
            if enabled_only:
                query = query.filter(ScheduledTask.enabled == True)
            return query.order_by(ScheduledTask.created_at.desc()).all()
    
    @staticmethod
    def get_pending_tasks() -> List[ScheduledTask]:
        """获取待执行的定时任务（到达执行时间且状态为pending的启用任务）"""
        with get_db() as db:
            now = datetime.now()
            return db.query(ScheduledTask).filter(
                and_(
                    ScheduledTask.enabled == True,
                    ScheduledTask.next_run_time <= now,
                    ScheduledTask.status.in_(["pending", "failed"])  # 失败的任务也可以重试
                )
            ).all()
    
    @staticmethod
    def update_task_status(task_id: int, status: str, error_message: str = None, last_task_id: str = None):
        """更新任务状态"""
        with get_db() as db:
            task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if task:
                task.status = status
                task.last_run_time = datetime.now()
                task.run_count += 1
                
                if error_message:
                    task.error_message = error_message
                if last_task_id:
                    task.last_task_id = last_task_id
                
                # 如果是重复任务且成功执行，计算下次执行时间
                if status == "completed" and task.repeat_type != "once":
                    task.next_run_time = ScheduledTaskDAO._calculate_next_run_time(
                        task.schedule_time, task.repeat_type, task.run_count
                    )
                    task.status = "pending"  # 重置为pending等待下次执行
                elif task.repeat_type == "once":
                    # 一次性任务完成后禁用
                    task.enabled = False
                
                db.commit()
                db.refresh(task)
                return task
    
    @staticmethod
    def toggle_task_enabled(task_id: int, enabled: bool) -> Optional[ScheduledTask]:
        """启用/禁用定时任务"""
        with get_db() as db:
            task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if task:
                task.enabled = enabled
                if enabled and task.status in ["completed", "failed", "cancelled"]:
                    task.status = "pending"
                    # 重新计算下次执行时间
                    if task.repeat_type == "once":
                        task.next_run_time = task.schedule_time
                    else:
                        task.next_run_time = ScheduledTaskDAO._calculate_next_run_time(
                            task.schedule_time, task.repeat_type, 0
                        )
                db.commit()
                db.refresh(task)
                return task
    
    @staticmethod
    def delete_scheduled_task(task_id: int) -> bool:
        """删除定时任务"""
        with get_db() as db:
            task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if task:
                db.delete(task)
                db.commit()
                return True
            return False
    
    @staticmethod
    def update_schedule_time(task_id: int, new_schedule_time: datetime) -> Optional[ScheduledTask]:
        """更新定时任务的执行时间"""
        with get_db() as db:
            task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if task:
                task.schedule_time = new_schedule_time
                task.next_run_time = new_schedule_time
                task.status = "pending"
                db.commit()
                db.refresh(task)
                return task
    
    @staticmethod
    def _calculate_next_run_time(base_time: datetime, repeat_type: str, run_count: int) -> datetime:
        """计算下次执行时间"""
        if repeat_type == "daily":
            return base_time + timedelta(days=run_count + 1)
        elif repeat_type == "weekly":
            return base_time + timedelta(weeks=run_count + 1)
        elif repeat_type == "monthly":
            # 简单处理月份，这里假设每月30天
            return base_time + timedelta(days=(run_count + 1) * 30)
        else:
            return base_time