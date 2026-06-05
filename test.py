# 测试摄像头 + 拍照 + TFLite识别 + 投票 是否正常
import sys
sys.path.append(".")

from camera.camera import open_camera, close_camera
from camera.recognize import recognize_pet

# ======================
# 简单测试
# ======================
if __name__ == '__main__':
    print("开始测试宠物识别...")

    # 直接调用识别（内部自动按需开关摄像头）
    result, img_paths = recognize_pet(capture_count=4)

    # 输出结果
    print("\n===== 测试结果 =====")
    print(f"最终识别：{result}")
    print(f"图片路径：{img_paths}")

    # 如果是手动打开过摄像头，这里不会关闭，保持原状
    print("\n测试完成！")