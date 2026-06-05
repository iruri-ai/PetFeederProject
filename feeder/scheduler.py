# 从 APScheduler 导入后台定时器
from apscheduler.schedulers.background import BackgroundScheduler

# 导入投喂函数
from feeder.motor import feed

# 导入自动投喂状态
from feeder.feed_manager import (
    is_auto_feed_enabled
)

# 导入数据库
from db.db import maoDB

# 创建后台定时器
scheduler = BackgroundScheduler()

# 创建数据库实例
db = maoDB()

# 保存所有定时任务（格式：hour_minute -> schedule_id）
feed_jobs = {}

# 定时执行函数
def scheduled_feed():
    if is_auto_feed_enabled():
        print("定时自动投喂")
        feed()

# 启动定时器（从数据库加载）
def start_scheduler():
    schedules = db.get_enabled_schedules()
    for schedule in schedules:
        feed_time = schedule['feed_time']
        schedule_id = schedule['id']
        hour, minute = map(int, feed_time.split(':'))
        job_id = f"{hour}_{minute}"
        
        scheduler.add_job(
            scheduled_feed,
            'cron',
            hour=hour,
            minute=minute,
            id=job_id
        )
        feed_jobs[job_id] = schedule_id
        print(f"从数据库加载定时：{hour}:{minute}")
    
    scheduler.start()

# 添加定时任务（先存数据库）
def add_feed_schedule(hour, minute):
    job_id = f"{hour}_{minute}"
    if job_id in feed_jobs:
        print("该时间已存在")
        return
    
    feed_time = f"{hour:02d}:{minute:02d}"
    schedule_id = db.insert_schedule(feed_time, enabled=1)
    
    scheduler.add_job(
        scheduled_feed,
        'cron',
        hour=hour,
        minute=minute,
        id=job_id
    )
    feed_jobs[job_id] = schedule_id
    print(f"添加定时：{hour}:{minute}")

# 获取全部定时
def get_schedules():
    return list(feed_jobs.keys())

# 删除定时（同步数据库）
def remove_schedule(hour, minute):
    job_id = f"{hour}_{minute}"
    if job_id in feed_jobs:
        schedule_id = feed_jobs[job_id]
        db.delete_schedule(schedule_id)
        
        scheduler.remove_job(job_id)
        del feed_jobs[job_id]
        print(f"删除定时：{hour}:{minute}")