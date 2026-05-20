from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory

from config import *

# 硬件PWM
factory = PiGPIOFactory()

# 水平舵机
servo_horizontal = Servo(
    SERVO_HORIZONTAL_PIN,
    pin_factory=factory,
    min_pulse_width=0.5/1000,
    max_pulse_width=2.5/1000
)

# 垂直舵机
servo_vertical = Servo(
    SERVO_VERTICAL_PIN,
    pin_factory=factory,
    min_pulse_width=0.5/1000,
    max_pulse_width=2.5/1000
)

# 当前位置
current_h = 0.0
current_v = 0.0

# 步长
STEP = SERVO_STEP

def move_servo(direction):

    global current_h
    global current_v

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