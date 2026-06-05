from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import RPi.GPIO as GPIO
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
import json
import os
from queue import Queue
import config 
class Hx711_data_queue:
    def __init__(self,
                 max_size: int = 10,
                 ):
        self.q = Queue(maxsize=max_size)

    def put(self, t: datetime, weight: float):
        if t and weight:
            if self.q.full():
                try:
                    self.q.get_nowait()  # 扔掉最旧的
                except:
                    pass
            self.q.put((t, weight))

    def get(self):
        try:
            return self.q.get_nowait()  # 非阻塞，空则抛异常
        except:
            return None


class Hx711:
    def __init__(self, 
                 sck_pin: int = 40,
                 dt_pin: int = 38, 
                 reference_unit: float = 413,
                 sample_delay: float = 1.0,
                 sampe_times: int = 2,
                 tare_offset: int = -137503.9,
                 garmmar: int = 2,
                 expect_times: int = 2,
                 ordinary_times: int = 3,
                 measure_interval: float = 2.0,
                 db:'maoDB' = None):
        # 基础参数
        self.SCK = sck_pin 
        self.DT = dt_pin 
        self.reference_unit = reference_unit 
        self.delay = sample_delay 
        self.sample_times = sampe_times 
        self.tare_offset = tare_offset
        self.db = db
        self.queue = Hx711_data_queue(10)

        # 异常
        self.garmmar = garmmar
        self.expect_times = expect_times
        self.expect_happen_times = 0
        self.ordinary_times = ordinary_times
        self.ordinary_happen_times = 0
        self.measure_interval = measure_interval
        self.log_enabled = True
        self._is_in_anomaly = False
        self._last_normal_weight = 0.0 

        # 状态变量
        self.gpio_initialized = False  
        self.weight = 0.0  # 初始化重量
        # db与camera
        self.result = None
        self.img_path = None
        self.begin_t = None
        self.begin_w = None
        self.end_t = None
        self.end_w = None
        # 定时器
        self.scheduler = None
        
        # 初始化硬件
        self.setup()
        
        # 启动定时器
        self._start_scheduler()
    
    def _start_scheduler(self):
        """启动定时器"""
        if self.scheduler is not None:
            return
        
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            func=self._auto_measure,
            trigger=IntervalTrigger(seconds=self.measure_interval),
            misfire_grace_time=1,
            coalesce=True,
            max_instances=1
        )
        self.scheduler.start()
        
        if self.log_enabled:
            print(f"[HX711] 定时器已启动，间隔: {self.measure_interval}s")
    
    def stop_scheduler(self):
        """停止定时器"""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
            if self.log_enabled:
                print("[HX711] 定时器已停止")
    
    def __del__(self):
        try:
            # 只有当 scheduler 存在且正在运行时才停止
            if hasattr(self, 'scheduler') and self.scheduler is not None:
                try:
                    if self.scheduler.running:
                        self.scheduler.shutdown(wait=False)
                except:
                    pass
        except:
            pass
        
        try:
            if self.gpio_initialized:
                GPIO.cleanup()
                if self.log_enabled:
                    print("[HX711] 已清理所有GPIO引脚")
                self.gpio_initialized = False
        except:
            pass
    
    def setup(self):
        if self.gpio_initialized:
            return
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.SCK, GPIO.OUT)
        GPIO.setup(self.DT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.output(self.SCK, GPIO.LOW)
        self.gpio_initialized = True
        if self.log_enabled:
            print(f"[HX711] GPIO初始化完成，SCK={self.SCK}, DT={self.DT}")
    
    def _read_raw_value(self) -> int:
        if not self.gpio_initialized:
            self.setup()
            
        timeout = 1.0
        start_time = time.time()
        while GPIO.input(self.DT):
            time.sleep(0.001)
            if time.time() - start_time > timeout:
                raise TimeoutError("传感器数据读取超时")
        
        value = 0
        for _ in range(24):
            GPIO.output(self.SCK, GPIO.HIGH)
            for _ in range(5):
                pass
            value = (value << 1) | GPIO.input(self.DT)
            GPIO.output(self.SCK, GPIO.LOW)
            for _ in range(5):
                pass

        GPIO.output(self.SCK, GPIO.HIGH)
        for _ in range(5):
            pass
        GPIO.output(self.SCK, GPIO.LOW)
        
        if value & 0x800000:
            value = value - 0x1000000
            
        return value
    
    def _read_weight_once(self) -> float:
        """单次测量，返回重量"""       
        total = 0
        for _ in range(self.sample_times):
            raw_value = self._read_raw_value()
            total += raw_value
            for _ in range(10):
                pass
        
        avg_raw = total / self.sample_times
        print(self.reference_unit)
        weight = (avg_raw - self.tare_offset) / self.reference_unit
        self.queue.put(datetime.now(), weight)
        return max(0.0, weight)
        
    def _auto_measure(self):
        """定时器调用的自动测量"""
        print("try measure",config.enable_hx711)
        if not config.enable_hx711:
            return 
        try:
            new_weight = self._read_weight_once()
            change = abs(new_weight - self.weight) if hasattr(self, 'weight') else 0
            self._detect_anomaly(change, new_weight)
            self.weight = new_weight
            
            if self.log_enabled:
                print(f"[HX711] 测量: {new_weight:.1f}g, 变化: {change:.1f}g, 异常计数: {self.expect_happen_times}")
        except Exception as e:
            if self.log_enabled:
                print(f"[HX711] 测量错误: {e}")

    def _detect_anomaly(self, change, new_weight):
        if change > self.garmmar:
            # 出现异常变化
            if self.expect_happen_times == 0:
                # 首次异常，保存当前重量为异常前最后一次正常重量
                self._last_normal_weight = self.weight
            self.expect_happen_times += 1
            self.ordinary_happen_times = 0
            
            if self.expect_happen_times >= self.expect_times and not self._is_in_anomaly:
                self._is_in_anomaly = True
                self.begin_t = datetime.now()
                self.begin_w = self._last_normal_weight
                self._expect_process_start()
        else:
            # 正常变化（没有异常）
            if self._is_in_anomaly:
                self.ordinary_happen_times += 1
                if self.ordinary_happen_times >= self.ordinary_times:
                    # 连续正常足够次数，恢复
                    self._is_in_anomaly = False
                    self.ordinary_happen_times = 0
                    self.expect_happen_times = 0
                    self.end_t = datetime.now()
                    self.end_w = new_weight  # 恢复时的重量
                    self._expect_process_end()
            else:
                # 不在异常状态，重置所有计数
                self.expect_happen_times = 0
                self.ordinary_happen_times = 0
                self._last_normal_weight = new_weight

    def _expect_process_end(self):
        """异常结束回调"""
        print(f"[HX711] 恢复正常，已连续 {self.ordinary_times} 次正常")
        
        if self.db:
            try:
                # 处理识别结果
                result_str = self.result
                if isinstance(self.result, list):
                    # 如果还是列表，取第一个
                    result_str = self.result[0] if self.result else "unknown"
                elif self.result is None:
                    result_str = "unknown"
                
                # 处理图片路径：列表转空格分隔的字符串
                if isinstance(self.img_path, list):
                    img_path_str = " ".join(self.img_path)  # 空格分隔
                elif self.img_path is None:
                    img_path_str = ""
                else:
                    img_path_str = str(self.img_path)
                
                # 时间转字符串
                begin_time_str = self.begin_t.isoformat() if self.begin_t else ""
                end_time_str = self.end_t.isoformat() if self.end_t else ""
                
                self.db.insert_record(  # 注意方法名改了
                    result=result_str,
                    img_path=img_path_str,
                    begin_time=begin_time_str,
                    begin_weight=float(self.begin_w) if self.begin_w else 0,
                    end_time=end_time_str,
                    end_weight=float(self.end_w) if self.end_w else 0
                )
                print(f"[HX711] 已保存到数据库")
                print(f"  识别结果: {result_str}")
                print(f"  图片路径: {img_path_str}")
                
            except Exception as e:
                print(f"[HX711] 数据库保存失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 清空本次记录数据
        self.result = None
        self.img_path = None
        self.begin_t = None
        self.begin_w = None
        self.end_t = None
        self.end_w = None
    def _expect_process_start(self):
        """异常开始回调"""
        print(f"[HX711] 检测到异常变化！已连续 {self.expect_times} 次超过 {self.garmmar}g")
        # 这里可以触发外部回调
        from camera.camera import open_camera, close_camera
        from camera.recognize import recognize_pet
        print("开始测试宠物识别...")
        self.result, self.img_path = recognize_pet(capture_count=4)
        print(self.result)
        print(self.img_path)