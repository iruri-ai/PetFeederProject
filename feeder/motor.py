# 投喂舵机驱动（无抖动 + 无权限报错）
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep
from config import *

# 全局强制使用硬件 PWM 驱动（无抖动）
factory = PiGPIOFactory()

# 出粮舵机（加了 pin_factory，彻底不抖）
feed_servo = Servo(
    FEED_SERVO_PIN,
    pin_factory=factory,          # 关键：硬件驱动
    min_pulse_width=0.5/1000,     # 标准舵机参数
    max_pulse_width=2.5/1000
)

def feed():
    print("开始投喂")
    unset_enable_hx711()
    # 转45°（无抖动）
    feed_servo.value = 0.5
    sleep(DEFAULT_FEED_DURATION)
    
    # 回位
    feed_servo.value = 0
    sleep(1)
    set_enable_hx711()
    print("投喂完成")