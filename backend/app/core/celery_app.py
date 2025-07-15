import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# Redis配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 创建Celery实例
celery_app = Celery(
    "bilinote",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.scheduled_tasks", "app.tasks.video_tasks"]
)

# Celery配置
celery_app.conf.update(
    # 时区设置
    timezone="Asia/Shanghai",
    enable_utc=True,
    
    # 任务结果过期时间 (24小时)
    result_expires=86400,
    
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 任务路由
    task_routes={
        "app.tasks.video_tasks.parse_video_task": {"queue": "video_parsing"},
        "app.tasks.scheduled_tasks.execute_scheduled_task": {"queue": "scheduled"},
    },
    
    # Worker配置
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # 错误重试配置
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # 定时任务配置
    beat_schedule={
        "check-scheduled-tasks": {
            "task": "app.tasks.scheduled_tasks.check_and_execute_scheduled_tasks",
            "schedule": 60.0,  # 每60秒检查一次
        },
    },
)