from flask import Flask, render_template, Response, request, jsonify
import cv2
import threading
import time
import os

# ===================== 舵机控制部分（已集成）=====================
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory

# 硬件PWM 稳定驱动
factory = PiGPIOFactory()

# 两个舵机：水平(左右) GPIO18 / 垂直(上下) GPIO23（你可以自己改）
servo_horizontal = Servo(18, pin_factory=factory, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)
servo_vertical = Servo(4, pin_factory=factory, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)

# 初始位置
current_h = 0.0
current_v = 0.0
STEP = 0.1  # 按一下动多少

def move_servo(direction):
    global current_h, current_v
    if direction == "up":
        current_v = max(-1, current_v - STEP)
        servo_vertical.value = current_v
    elif direction == "down":
        current_v = min(1, current_v + STEP)
        servo_vertical.value = current_v
    elif direction == "left":
        current_h = min(1, current_h + STEP)
        servo_horizontal.value = current_h
    elif direction == "right":
        current_h = max(-1, current_h - STEP)
        servo_horizontal.value = current_h

# ===================== 原来的摄像头代码 =====================
app = Flask(__name__, template_folder="web")

cap = None
lock = threading.Lock()
camera_on = False
frame = None

save_folder = "captures"
os.makedirs(save_folder, exist_ok=True)

def capture_frames():
    global cap, frame, camera_on
    while camera_on:
        ret, img = cap.read()
        if ret:
            with lock:
                frame = img.copy()
        time.sleep(0.01)

def gen_frames():
    global frame
    while True:
        with lock:
            if frame is None or not camera_on:
                continue
            ret, buffer = cv2.imencode('.jpg', frame)
            jpg = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/open_camera', methods=['POST'])
def open_camera():
    global cap, camera_on, frame
    if not camera_on:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        camera_on = True
        frame = None
        threading.Thread(target=capture_frames, daemon=True).start()
        return jsonify(status="视频已打开")
    return jsonify(status="视频已开启")

@app.route('/close_camera', methods=['POST'])
def close_camera():
    global cap, camera_on
    if camera_on:
        camera_on = False
        time.sleep(0.1)
        cap.release()
        return jsonify(status="视频已关闭")
    return jsonify(status="视频未开启")

@app.route('/capture', methods=['POST'])
def capture():
    global frame, camera_on, cap
    if not camera_on or cap is None or not cap.isOpened():
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        time.sleep(0.1)
        ret, frame = cap.read()
        if ret:
            filename = os.path.join(save_folder, f"capture_{int(time.time())}.jpg")
            cv2.imwrite(filename, frame)
        cap.release()
        return jsonify(status="拍照成功")

    with lock:
        if frame is None:
            return jsonify(status="无画面")
        filename = os.path.join(save_folder, f"capture_{int(time.time())}.jpg")
        cv2.imwrite(filename, frame)
    return jsonify(status="拍照成功")

# ===================== 网页控制舵机接口 =====================
@app.route('/move', methods=['POST'])
def move():
    dir = request.json.get("dir")
    move_servo(dir)
    return jsonify(status=f"已移动：{dir}")

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)