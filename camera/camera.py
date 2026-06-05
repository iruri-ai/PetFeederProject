from flask import Response

import cv2
import threading
import time
import os

from config import *
from .servo_control import servo_horizontal, servo_vertical

# 全局变量

cap = None

frame = None

camera_on = False

lock = threading.Lock()

# 图片保存目录

save_folder = SAVE_FOLDER

os.makedirs(save_folder, exist_ok=True)

# 后台线程持续读取摄像头

def capture_frames():

    global cap
    global frame
    global camera_on

    while camera_on:

        ret, img = cap.read()

        if ret:

            with lock:

                frame = img.copy()

        time.sleep(0.01)

# 打开摄像头

def open_camera():

    global cap
    global camera_on
    global frame

    if camera_on:

        return "摄像头已经开启"

    cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)

    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)

    if not cap.isOpened():

        return "摄像头打开失败"

    camera_on = True

    frame = None

    threading.Thread(
        target=capture_frames,
        daemon=True
    ).start()

    print("摄像头已打开")

    return "摄像头已打开"

# 关闭摄像头

def close_camera():

    global cap
    global camera_on

    if not camera_on:

        return "摄像头未开启"

    camera_on = False

    time.sleep(0.1)

    if cap is not None:
        cap.release()

    # ======================
    # 【关闭摄像头 → 云台自动归位】
    # ======================
    servo_horizontal.value = 0.0
    servo_vertical.value = 0.0
    time.sleep(0.2)

    print("摄像头已关闭 | 云台已归位")
    return "摄像头已关闭 | 云台已归位"

# 拍照

def capture_image():

    global frame
    global camera_on
    global cap

    if not camera_on or cap is None or not cap.isOpened():

        return "请先打开摄像头"

    with lock:

        if frame is None:

            return "无画面"

        filename = os.path.join(
            save_folder,
            f"capture_{int(time.time())}.jpg"
        )

        cv2.imwrite(filename, frame)

        print(f"图片已保存：{filename}")

        return "拍照成功"

# 视频流

def gen_frames():

    global frame
    global camera_on

    while True:

        if not camera_on:

            time.sleep(0.1)

            continue

        with lock:

            if frame is None:

                continue

            ret, buffer = cv2.imencode('.jpg', frame)

            jpg = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + jpg +
            b'\r\n'
        )

# Flask视频流接口

def video_feed():

    return Response(
        gen_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# 专为AI识别批量拍照
def capture_for_recognize(count=4):
    global frame, camera_on, cap

    if not camera_on or cap is None or not cap.isOpened():
        return []

    image_paths = []

    while len(image_paths) < count:
        with lock:
            if frame is not None:
                filename = os.path.join(
                    save_folder,
                    f"rec_{int(time.time())}_{len(image_paths)}.jpg"
                )
                cv2.imwrite(filename, frame)
                image_paths.append(filename)
        time.sleep(0.2)

    return image_paths