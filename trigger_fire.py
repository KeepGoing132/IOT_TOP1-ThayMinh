"""
trigger_fire.py
=============================================================================
Script kích hoạt nhanh Báo Động Cháy để kiểm thử còi ESP32 & nút bấm Tắt Còi:
1. Tự động sinh ảnh ngọn lửa có Bounding Box YOLO ("fire: 98.7%")
2. Bắn dữ liệu cảm biến tăng vọt (PM2.5=650, TVOC=850, Temp=38.5) lên iot/test/request
3. Bắn lệnh BẬT CÒI (buzzer=1, cmd=BUZZER_ON) lên iot/test/response
=============================================================================
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path
import numpy as np
import cv2
import paho.mqtt.client as mqtt

BROKER = "10.156.225.221"
PORT = 1883

def main():
    print("=" * 70)
    print("🚨 ĐANG TẠO DỮ LIỆU GIẢ LẬP ĐỂ KÍCH HOẠT BÁO CHÁY & BẬT CÒI ESP32...")
    print("=" * 70)

    now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    img_name = f"fire_evidence_{now_tag}.jpg"

    # 1. Tạo ảnh ngọn lửa có bounding box YOLO
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (20, 22, 28)
    cv2.rectangle(img, (0, 380), (640, 480), (35, 38, 45), -1)
    cv2.line(img, (0, 380), (640, 380), (60, 65, 75), 2)
    cv2.ellipse(img, (320, 310), (70, 110), 0, 0, 360, (15, 70, 230), -1)
    cv2.ellipse(img, (320, 325), (45, 80), 0, 0, 360, (20, 160, 255), -1)
    cv2.ellipse(img, (320, 340), (22, 45), 0, 0, 360, (120, 235, 255), -1)
    for r in range(5):
        cv2.circle(img, (320 + np.random.randint(-25, 25), 180 - r * 25), 35 + r * 8, (60, 60, 65), -1)
    img = cv2.GaussianBlur(img, (15, 15), 0)

    box_x1, box_y1, box_x2, box_y2 = 230, 180, 410, 400
    cv2.rectangle(img, (box_x1, box_y1), (box_x2, box_y2), (0, 0, 240), 2)
    label = "fire: 98.7%"
    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
    cv2.rectangle(img, (box_x1, box_y1 - 25), (box_x1 + w + 10, box_y1), (0, 0, 240), -1)
    cv2.putText(img, label, (box_x1 + 5, box_y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    dt_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S [YOLO_NCNN Pi5]")
    cv2.putText(img, dt_text, (20, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    # Lưu ảnh vào các thư mục liên quan
    save_dirs = [
        Path("C:/Users/OS/Desktop/IOT/dashboard/evidence"),
        Path("C:/Users/OS/Desktop/IOT/pi5_deploy"),
        Path("./evidence"),
        Path("./dashboard/evidence"),
        Path("../pi5_deploy")
    ]
    for d in save_dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / img_name), img)
        except Exception:
            pass

    print(f"📸 1. Đã sinh ảnh bằng chứng: {img_name}")

    # 2. Kết nối MQTT Broker
    client = mqtt.Client()
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        time.sleep(0.5)
    except Exception as e:
        print(f"❌ Không thể kết nối MQTT Broker {BROKER}:{PORT}: {e}")
        return

    # Gói tin cảm biến nhiệt độ & khói tăng vọt
    fire_sensor_payload = {
        "elapsed_ms": 150000,
        "temperature": 38.5,
        "humidity": 45.0,
        "eCO2": 950,
        "TVOC": 850,
        "PM1_0": 340,
        "PM2_5": 650,
        "PM10": 720,
        "NC0_3": 14500,
        "NC0_5": 4600,
        "NC1_0": 1250,
        "NC2_5": 190,
        "NC5_0": 25,
        "NC10": 6
    }
    client.publish("iot/test/request", json.dumps(fire_sensor_payload))
    print("📡 2. Đã gửi Telemetry cháy lên topic: iot/test/request")

    time.sleep(0.3)

    # Gói tin báo cháy xác thực gửi về ESP32 và Dashboard
    fire_alarm_payload = {
        "status": "FIRE_CONFIRMED",
        "buzzer": 1,
        "alarm": 1,
        "cmd": "BUZZER_ON",
        "is_fire": True,
        "xgb_prediction": "fire",
        "visual_verified": True,
        "confidence": 0.987,
        "evidence_image": img_name,
        "pm25": 650,
        "tvoc": 850,
        "temp": 38.5,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    client.publish("iot/test/response", json.dumps(fire_alarm_payload))
    print("🚨 3. Đã gửi LỆNH BẬT CÒI (buzzer=1, cmd=BUZZER_ON) lên topic: iot/test/response")

    time.sleep(1)
    client.loop_stop()
    client.disconnect()

    print("=" * 70)
    print("✅ ĐÃ KÍCH HOẠT XONG!")
    print("👉 Bây giờ ESP32 đang kêu còi.")
    print("👉 Hãy mở Web: http://localhost:5000 và bấm nút [Tắt Còi] để kiểm tra tắt!")
    print("=" * 70)

if __name__ == "__main__":
    main()
