import time
import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite
from config import MODEL_PATH, LABEL_PATH
from .camera import open_camera, close_camera, capture_for_recognize, camera_on
from .servo_control import servo_horizontal, servo_vertical, current_h, current_v

# 加载标签
def load_labels(path):
    with open(path, "r") as f:
        label_list = [line.strip() for line in f.readlines()]

    def get_main_class(idx):
        if 281 <= idx <= 287:
            return "cat"
        elif 151 <= idx <= 157:
            return "dog"
        else:
            return "other"
    return label_list, get_main_class

# 加载TFLite模型
def load_model(model_path):
    interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter

# 全局初始化（只加载一次）
_, get_main_class = load_labels(LABEL_PATH)
interpreter = load_model(MODEL_PATH)
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
input_index = input_details[0]['index']
output_index = output_details[0]['index']

# 单张图片识别
def recognize_image(img_path):
    image = Image.open(img_path).convert("RGB")
    h = input_details[0]['shape'][1]
    w = input_details[0]['shape'][2]
    image = image.resize((w, h))

    input_data = np.expand_dims(image, axis=0)
    interpreter.set_tensor(input_index, input_data)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_index)
    output_data = np.squeeze(output_data)
    top_index = np.argmax(output_data)
    score = float(output_data[top_index] / 255.0)
    label = get_main_class(top_index)

    return label, score
'''
# 重量触发 → 自动识别宠物（主函数）
def recognize_pet(capture_count=4):
    was_on = camera_on
    img_paths = []

    try:
        # 1. 记住用户当前云台位置
        old_h = current_h
        old_v = current_v

        # 2. 识别专用位置（正中间，最准）
        servo_horizontal.value = 0.0
        servo_vertical.value = 0.0
        time.sleep(0.3)  # 等舵机稳
        # 只有关闭时才打开
        if not was_on:
            open_camera()
            time.sleep(0.8)
        

        # 批量拍照
        img_paths = capture_for_recognize(count=capture_count)

        if not img_paths:
            return "unknown", []

    finally:
        # 【拍完立刻还原云台】
        # ======================
        servo_horizontal.value = old_h
        servo_vertical.value = old_v
        time.sleep(0.2)
        # 只有原本关闭才关闭
        if not was_on:
            close_camera()

    # 逐张识别
    labels = []
    for path in img_paths:
        lab, _ = recognize_image(path)
        labels.append(lab)

    # 投票
    if not labels:
        final_label = "unknown"
    else:
        final_label = max(labels, key=labels.count)

    print(f"单帧结果：{labels}")
    print(f"最终识别：{final_label}")

    return final_label, img_paths
'''



def recognize_pet(capture_count=4):
    was_on = camera_on
    img_paths = []

    # 识别中心位置
    CENTER_H = 0.0
    CENTER_V = 0.0
    # 允许误差：±0.1 以内都算“已经在正确位置”
    ALLOW_ERROR = 0.01

    try:
        # 1. 记住当前位置
        old_h = current_h
        old_v = current_v

        # 2. 判断是否已经在正确位置
        need_reset = (
            abs(current_h - CENTER_H) > ALLOW_ERROR
            or
            abs(current_v - CENTER_V) > ALLOW_ERROR
        )

        # 3. 只有偏了才归位
        if need_reset:
            servo_horizontal.value = CENTER_H
            servo_vertical.value = CENTER_V
            time.sleep(0.3)

        # 4. 摄像头按需打开
        if not was_on:
            open_camera()
            time.sleep(0.8)

        # 5. 拍照
        time.sleep(1)
        img_paths = capture_for_recognize(count=capture_count)

        if not img_paths:
            return "unknown", []

    finally:
        # 6. 只有之前归位过，才恢复原来角度
        if need_reset:
            servo_horizontal.value = old_h
            servo_vertical.value = old_v
            time.sleep(0.2)

        # 摄像头恢复
        if not was_on:
            close_camera()

    # 识别投票
    labels = []
    for path in img_paths:
        lab, _ = recognize_image(path)
        labels.append(lab)

    if not labels:
        final_label = "unknown"
    else:
        final_label = max(labels, key=labels.count)

    print(f"单帧结果：{labels}")
    print(f"最终识别：{final_label}")

    return final_label, img_paths