from flask import Flask
from flask import render_template
from flask import jsonify
from flask import request, Response
from hx711.HX711 import Hx711
from db.db import maoDB
from config import *
import json
import time
import sqlite3
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

mao = maoDB()
hx711 = Hx711(db=mao)

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

# ========================
# 图表
# ========================
weight_stream_active = True  # 初始为 True

@app.route('/start_weight_table', methods=['POST', 'GET'])
def start_weight_table():
    global weight_stream_active
    weight_stream_active = True  # 每次启动重置
    
    def generate():
        global weight_stream_active
        while weight_stream_active:
            # 从队列获取数据（非阻塞）
            data = hx711.queue.get()
            
            if data:
                t, weight = data
                json_data = json.dumps({
                    'time': t.strftime('%H:%M:%S'),
                    'weight': weight
                })
                yield f"data: {json_data}\n\n"
            else:
                # 没有数据时发送心跳（保持连接）
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"
            
            time.sleep(1)
        
        # 循环结束，发送结束标记
        yield f"data: {json.dumps({'status': 'stopped'})}\n\n"
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Access-Control-Allow-Origin': '*'
        }
    )

@app.route('/stop_weight_table', methods=['GET', 'POST'])
def stop_weight_table():
    """停止推送"""
    global weight_stream_active
    weight_stream_active = False
    return {'status': 'stopped'}


@app.route('/api/daily_consumption', methods=['GET', 'POST'])
def api_daily_consumption():
    stats = mao.get_daily_consumption()
    return jsonify(stats)

# ========================
# 日志
# ========================
# ========================
# 初始化接口
# ========================
@app.route('/init_log', methods=['GET', 'POST'])
def init_log():
    """客户端初始化：返回最新的5条记录，并记录客户端状态"""
    try:
        # 获取客户端标识（可以用IP、session_id或前端传来的client_id）
        client_id = request.args.get('client_id', request.remote_addr)
        
        # 获取最新的5条记录
        latest_records = mao.get_recent_records(5)
        
        if latest_records:
            # 最新记录的ID（最大ID）
            latest_id = latest_records[0]['id']
            # 最旧的ID（当前返回的5条中最小的）
            oldest_id = latest_records[-1]['id']
        else:
            latest_id = 0
            oldest_id = 0
        
        
        # 返回数据
        return jsonify({
            'success': True,
            'head': latest_records,     # 最新的5条（降序）
            'end': []                    # 初始化时没有更旧的记录
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/update_log', methods=['GET', 'POST'])
def update_log():
    """客户端告诉服务器自己已有的最新ID和最旧ID"""
    current_end = request.args.get('current_end', 0, type=int)
    current_begin = request.args.get('current_begin', 0, type=int)
    
    # 获取新记录（ID > current_end）
    
    head_records = mao.get_recent_records(mao.get_record_count() - current_end)
    
    # 获取更旧的5条记录（ID < current_begin）
    conn = sqlite3.connect(mao.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM eating_records 
        WHERE id < ?
        ORDER BY id DESC
        LIMIT 5
    """, (current_begin,))
    end_records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'head': head_records,
        'end': end_records
    })

# =========================
# 启动
# =========================

if __name__ == '__main__':

    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG
    )