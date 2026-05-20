from flask import Flask
from flask import render_template
from flask import jsonify
from flask import request

from config import *

# 摄像头
from camera.camera import (
    open_camera,
    close_camera,
    capture_image,
    video_feed
)

# 云台
from camera.servo_control import (
    move_servo
)

# 投喂
from feeder.feed_manager import (
    manual_feed,
    enable_auto_feed,
    disable_auto_feed
)

# 定时器
from feeder.scheduler import (
    start_scheduler,
    add_feed_schedule,
    get_schedules,
    remove_schedule
)

# 按钮
from feeder.button import (
    setup_button
)

app = Flask(
    __name__,
    template_folder="templates"
)

# 启动定时器
start_scheduler()

# 启动按钮监听
setup_button()

# =========================
# 首页
# =========================

@app.route('/')
def index():

    return render_template('index.html')

# =========================
# 视频流
# =========================

@app.route('/video_feed')
def video():

    return video_feed()

# =========================
# 摄像头
# =========================

@app.route('/open_camera', methods=['POST'])
def open_cam():

    result = open_camera()

    return jsonify(status=result)

@app.route('/close_camera', methods=['POST'])
def close_cam():

    result = close_camera()

    return jsonify(status=result)

@app.route('/capture', methods=['POST'])
def capture():

    result = capture_image()

    return jsonify(status=result)

# =========================
# 云台
# =========================

@app.route('/move/<direction>', methods=['POST'])
def move(direction):

    move_servo(direction)

    return jsonify(status="ok")

# =========================
# 手动投喂
# =========================

@app.route('/feed', methods=['POST'])
def feed():

    manual_feed()

    return jsonify(status="feeding")

# =========================
# 自动投喂
# =========================

@app.route('/enable_auto', methods=['POST'])
def enable_auto():

    enable_auto_feed()

    return jsonify(status="enabled")

@app.route('/disable_auto', methods=['POST'])
def disable_auto():

    disable_auto_feed()

    return jsonify(status="disabled")

# =========================
# 添加定时
# =========================

@app.route('/add_schedule', methods=['POST'])
def add_schedule():

    data = request.get_json()

    time_str = data['time']

    hour, minute = map(
        int,
        time_str.split(':')
    )

    add_feed_schedule(hour, minute)

    return jsonify(status="schedule added")

# 获取全部定时
@app.route('/get_schedules')
def schedules():

    return jsonify(
        schedules=get_schedules()
    )

# 删除定时
@app.route('/remove_schedule', methods=['POST'])
def remove_time():

    data = request.get_json()

    time_str = data['time']

    hour, minute = map(
        int,
        time_str.split('_')
    )

    remove_schedule(hour, minute)

    return jsonify(status="删除成功")

# =========================
# 启动
# =========================

if __name__ == '__main__':

    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG
    )