# 从 APScheduler 导入后台定时器
from apscheduler.schedulers.background import BackgroundScheduler

# 导入投喂函数
from feeder.motor import feed

# 导入自动投喂状态
from feeder.feed_manager import (
    is_auto_feed_enabled
)

# 创建后台定时器
scheduler = BackgroundScheduler()

# 保存所有定时任务
feed_jobs = []

# 定时执行函数
def scheduled_feed():

    # 判断自动投喂是否开启
    if is_auto_feed_enabled():

        print("定时自动投喂")

        # 执行投喂
        feed()

# 启动定时器
def start_scheduler():

    scheduler.start()

# 添加定时任务
def add_feed_schedule(hour, minute):

    # 任务ID
    job_id = f"{hour}_{minute}"

    # 防止重复添加
    if job_id in feed_jobs:

        print("该时间已存在")

        return

    # 添加定时任务
    scheduler.add_job(
        scheduled_feed,
        'cron',
        hour=hour,
        minute=minute,
        id=job_id
    )

    # 保存到列表
    feed_jobs.append(job_id)

    print(f"添加定时：{hour}:{minute}")

# 获取全部定时
def get_schedules():

    return feed_jobs

# 删除定时
def remove_schedule(hour, minute):

    job_id = f"{hour}_{minute}"

    if job_id in feed_jobs:

        scheduler.remove_job(job_id)

        feed_jobs.remove(job_id)

        print(f"删除定时：{hour}:{minute}")