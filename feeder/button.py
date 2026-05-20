from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Device

# 全局设置，所有GPIO都用pigpio驱动
Device.pin_factory = PiGPIOFactory()

# 然后才导入 Button
from gpiozero import Button

from config import *
from feeder.motor import feed

# GPIO按钮
button = Button(BUTTON_PIN, bounce_time=0.1, pull_up=False)

def setup_button():
    button.when_pressed = feed
    print("✅ 硬件按钮已启动")