# =========================
# 摄像头配置
# =========================

CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240
CAMERA_FPS = 15

# =========================
# GPIO 配置
# =========================

# 出粮舵机
FEED_SERVO_PIN = 17

# 云台舵机
SERVO_HORIZONTAL_PIN = 24
SERVO_VERTICAL_PIN = 23

# 按钮
BUTTON_PIN = 25

# =========================
# 图片保存
# =========================

SAVE_FOLDER = "captures"

# =========================
# Flask
# =========================

HOST = "0.0.0.0"
PORT = 5000
DEBUG = False

# =========================
# 舵机参数
# =========================

SERVO_STEP = 0.1

# =========================
# 投喂参数
# =========================

DEFAULT_FEED_DURATION = 0.5  # 出粮持续时间，单位秒

# =========================
# 自动投喂默认状态
# =========================

AUTO_FEED_DEFAULT = False
MODEL_PATH = "mobilenet_v1_1.0_224_quant.tflite"
LABEL_PATH = "labels_mobilenet_quant_v1_224.txt"
enable_hx711=False
def set_enable_hx711():
    global enable_hx711
    enable_hx711 = True
def unset_enable_hx711():
    global enable_hx711
    enable_hx711 = False