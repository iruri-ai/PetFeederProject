import RPi.GPIO as GPIO
import time

# 你用的是 BCM 引脚：17,27,22,23
IN1 = 17
IN2 = 27
IN3 = 22
IN4 = 23

# 八拍序列
seq = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1]
]

# ======================
# 这里必须改成 BCM！
# ======================
GPIO.setmode(GPIO.BCM)  # 已修复
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)

def set_step(w1, w2, w3, w4):
    GPIO.output(IN1, w1)
    GPIO.output(IN2, w2)
    GPIO.output(IN3, w3)
    GPIO.output(IN4, w4)

def rotate(angle, delay=0.0008):
    steps = int(abs(angle) * 512 / 360)
    direction = 1 if angle > 0 else -1

    for _ in range(steps):
        if direction == 1:
            for s in seq:
                set_step(*s)
                time.sleep(delay)
        else:
            for s in reversed(seq):
                set_step(*s)
                time.sleep(delay)
    set_step(0,0,0,0)

def feed():
    print("开始投喂...")
    rotate(720)
    time.sleep(0.5)

try:
    feed()
except KeyboardInterrupt:
    print("停止")
finally:
    set_step(0,0,0,0)
    GPIO.cleanup()