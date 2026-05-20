from flask import Flask, render_template, Response, request, jsonify
import cv2
import threading
import time
import os

app = Flask(__name__, template_folder="web")

# 全局变量
cap = None
lock = threading.Lock()
camera_on = False
frame = None

# 拍照目录
save_folder = "captures"
os.makedirs(save_folder, exist_ok=True)

# 持续取帧
def capture_frames():
    global cap, frame, camera_on
    while camera_on:
        ret, img = cap.read()
        if ret:
            with lock:
                frame = img.copy()
        time.sleep(0.01)

# 视频流
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

# 首页
@app.route('/')
def index():
    return render_template('index.html')

# 打开摄像头
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

# 关闭摄像头
@app.route('/close_camera', methods=['POST'])
def close_camera():
    global cap, camera_on
    if camera_on:
        camera_on = False
        time.sleep(0.1)
        cap.release()
        return jsonify(status="视频已关闭")
    return jsonify(status="视频未开启")

# 拍照（核心逻辑在这里！）
@app.route('/capture', methods=['POST'])
def capture():
    global frame, camera_on, cap

    # 如果摄像头没开，临时打开拍照
    if not camera_on or cap is None or not cap.isOpened():
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        time.sleep(0.1)
        ret, frame = cap.read()
        if ret:
            filename = os.path.join(save_folder, f"capture_{int(time.time())}.jpg")
            cv2.imwrite(filename, frame)
        cap.release()  # 拍完立刻关
        return jsonify(status="拍照成功（视频已关闭）")

    # 如果摄像头本来就是开的 → 只拍照，不关闭
    with lock:
        if frame is None:
            return jsonify(status="无画面")
        filename = os.path.join(save_folder, f"capture_{int(time.time())}.jpg")
        cv2.imwrite(filename, frame)

    return jsonify(status="拍照成功（继续视频）")

# 视频流
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)