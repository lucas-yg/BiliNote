from datetime import datetime, timedelta
from typing import List, Optional, Union
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, model_validator

from app.db.scheduled_task_dao import ScheduledTaskDAO
from app.utils.response import ResponseWrapper as R
from app.enmus.note_enums import DownloadQuality

router = APIRouter()


class ScheduledTaskRequest(BaseModel):
    """创建定时任务请求"""
    task_name: str
    video_url: str
    platform: str
    schedule_time: Optional[datetime] = None
    delay_minutes: Optional[int] = None
    repeat_type: str = "once"  # once, daily, weekly, monthly
    enabled: bool = True
    
    # 笔记生成配置
    quality: DownloadQuality = DownloadQuality.MEDIUM
    screenshot: bool = False
    link: bool = False
    model_name: str
    provider_id: str
    format: List[str] = []
    style: str = "minimal"
    extras: Optional[str] = None
    video_understanding: bool = False
    video_interval: int = 4
    grid_size: List[int] = [3, 3]
    
    @model_validator(mode='after')
    def validate_schedule_params(self):
        if self.schedule_time is None and self.delay_minutes is None:
            raise ValueError("必须提供 schedule_time 或 delay_minutes")
        
        if self.schedule_time is not None and self.delay_minutes is not None:
            raise ValueError("不能同时提供 schedule_time 和 delay_minutes")
        
        if self.schedule_time is not None and self.schedule_time <= datetime.now():
            raise ValueError("定时时间必须大于当前时间")
        
        if self.delay_minutes is not None:
            if self.delay_minutes <= 0:
                raise ValueError("延迟分钟数必须大于0")
            if self.delay_minutes > 1440:  # 限制最大24小时
                raise ValueError("延迟分钟数不能超过1440分钟（24小时）")
        
        return self
    
    @field_validator("repeat_type")
    def validate_repeat_type(cls, v):
        if v not in ["once", "daily", "weekly", "monthly"]:
            raise ValueError("重复类型必须是 once, daily, weekly, monthly 中的一个")
        return v


class UpdateScheduleTimeRequest(BaseModel):
    """更新定时时间请求"""
    schedule_time: Optional[datetime] = None
    delay_minutes: Optional[int] = None
    
    @model_validator(mode='after')
    def validate_schedule_params(self):
        if self.schedule_time is None and self.delay_minutes is None:
            raise ValueError("必须提供 schedule_time 或 delay_minutes")
        
        if self.schedule_time is not None and self.delay_minutes is not None:
            raise ValueError("不能同时提供 schedule_time 和 delay_minutes")
        
        if self.schedule_time is not None and self.schedule_time <= datetime.now():
            raise ValueError("定时时间必须大于当前时间")
        
        if self.delay_minutes is not None:
            if self.delay_minutes <= 0:
                raise ValueError("延迟分钟数必须大于0")
            if self.delay_minutes > 1440:
                raise ValueError("延迟分钟数不能超过1440分钟（24小时）")
        
        return self


class ToggleTaskRequest(BaseModel):
    """切换任务状态请求"""
    enabled: bool


@router.post("/scheduled_tasks")
def create_scheduled_task(data: ScheduledTaskRequest):
    """创建定时任务"""
    try:
        # 计算实际的定时时间
        if data.delay_minutes is not None:
            schedule_time = datetime.now() + timedelta(minutes=data.delay_minutes)
        else:
            schedule_time = data.schedule_time
        
        # 构建任务配置
        task_config = {
            "quality": data.quality.value,
            "screenshot": data.screenshot,
            "link": data.link,
            "model_name": data.model_name,
            "provider_id": data.provider_id,
            "format": data.format,
            "style": data.style,
            "extras": data.extras,
            "video_understanding": data.video_understanding,
            "video_interval": data.video_interval,
            "grid_size": data.grid_size
        }
        
        scheduled_task = ScheduledTaskDAO.create_scheduled_task(
            task_name=data.task_name,
            video_url=data.video_url,
            platform=data.platform,
            schedule_time=schedule_time,
            task_config=task_config,
            repeat_type=data.repeat_type,
            enabled=data.enabled
        )
        
        return R.success({
            "id": scheduled_task.id,
            "task_name": scheduled_task.task_name,
            "schedule_time": scheduled_task.schedule_time.isoformat(),
            "repeat_type": scheduled_task.repeat_type,
            "enabled": scheduled_task.enabled,
            "delay_minutes": data.delay_minutes
        }, msg="定时任务创建成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduled_tasks")
def get_scheduled_tasks(enabled_only: bool = False):
    """获取定时任务列表"""
    try:
        tasks = ScheduledTaskDAO.get_user_scheduled_tasks(enabled_only=enabled_only)
        
        result = []
        for task in tasks:
            result.append({
                "id": task.id,
                "task_name": task.task_name,
                "video_url": task.video_url,
                "platform": task.platform,
                "schedule_time": task.schedule_time.isoformat(),
                "next_run_time": task.next_run_time.isoformat() if task.next_run_time else None,
                "repeat_type": task.repeat_type,
                "enabled": task.enabled,
                "status": task.status,
                "run_count": task.run_count,
                "last_run_time": task.last_run_time.isoformat() if task.last_run_time else None,
                "last_task_id": task.last_task_id,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat(),
                "task_config": task.task_config
            })
        
        return R.success(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduled_tasks/{task_id}")
def get_scheduled_task(task_id: int):
    """获取单个定时任务详情"""
    try:
        task = ScheduledTaskDAO.get_scheduled_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="定时任务不存在")
        
        return R.success({
            "id": task.id,
            "task_name": task.task_name,
            "video_url": task.video_url,
            "platform": task.platform,
            "schedule_time": task.schedule_time.isoformat(),
            "next_run_time": task.next_run_time.isoformat() if task.next_run_time else None,
            "repeat_type": task.repeat_type,
            "enabled": task.enabled,
            "status": task.status,
            "run_count": task.run_count,
            "last_run_time": task.last_run_time.isoformat() if task.last_run_time else None,
            "last_task_id": task.last_task_id,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat(),
            "task_config": task.task_config
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scheduled_tasks/{task_id}/toggle")
def toggle_scheduled_task(task_id: int, data: ToggleTaskRequest):
    """启用/禁用定时任务"""
    try:
        task = ScheduledTaskDAO.toggle_task_enabled(task_id, data.enabled)
        if not task:
            raise HTTPException(status_code=404, detail="定时任务不存在")
        
        return R.success({
            "id": task.id,
            "enabled": task.enabled,
            "status": task.status,
            "next_run_time": task.next_run_time.isoformat() if task.next_run_time else None
        }, msg=f"定时任务已{'启用' if data.enabled else '禁用'}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scheduled_tasks/{task_id}/schedule_time")
def update_schedule_time(task_id: int, data: UpdateScheduleTimeRequest):
    """更新定时任务的执行时间"""
    try:
        # 计算实际的定时时间
        if data.delay_minutes is not None:
            schedule_time = datetime.now() + timedelta(minutes=data.delay_minutes)
        else:
            schedule_time = data.schedule_time
        
        task = ScheduledTaskDAO.update_schedule_time(task_id, schedule_time)
        if not task:
            raise HTTPException(status_code=404, detail="定时任务不存在")
        
        return R.success({
            "id": task.id,
            "schedule_time": task.schedule_time.isoformat(),
            "next_run_time": task.next_run_time.isoformat() if task.next_run_time else None,
            "status": task.status,
            "delay_minutes": data.delay_minutes
        }, msg="定时时间更新成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduled_tasks/{task_id}")
def delete_scheduled_task(task_id: int):
    """删除定时任务"""
    try:
        success = ScheduledTaskDAO.delete_scheduled_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="定时任务不存在")
        
        return R.success(msg="定时任务删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))