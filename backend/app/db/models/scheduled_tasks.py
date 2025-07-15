from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, func
from sqlalchemy.dialects.sqlite import JSON

from app.db.engine import Base


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(255), nullable=False)
    video_url = Column(Text, nullable=False)
    platform = Column(String(50), nullable=False)
    
    # 调度配置
    schedule_time = Column(DateTime, nullable=False)
    repeat_type = Column(String(20), default="once")  # once, daily, weekly, monthly
    enabled = Column(Boolean, default=True)
    
    # 任务配置 (JSON格式存储用户设置)
    task_config = Column(JSON, nullable=True)
    
    # 状态跟踪
    status = Column(String(20), default="pending")  # pending, running, completed, failed, cancelled
    last_run_time = Column(DateTime, nullable=True)
    next_run_time = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)
    max_runs = Column(Integer, nullable=True)  # 最大执行次数，null表示无限制
    
    # 执行结果
    last_task_id = Column(String, nullable=True)  # 关联到video_tasks表
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100), default="system")  # 预留用户字段