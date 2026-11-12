"""
send_fake_sensor_fire.py
=============================================================================
Bắn 1 gói tin cảm biến CỰC NÓNG & NHIỀU KHÓI lên topic "iot/test/request"
Mục đích:
- Để XGBoost trên Raspberry Pi 5 chẩn đoán là [FIRE HAZARD]
- Kích hoạt Camera Picamera2 thức dậy và chụp quét ngọn lửa qua YOLO NCNN!
=============================================================================
"""

import time
import json
import paho.mqtt.client as mqtt

BROKER = "10.156.225.221"
PORT = 1883
TOPIC = "iot/test/request"

def main():
    print("=" * 70)
    print("🚀 ĐANG GỬI GÓI TIN CẢM BIẾN CHÁY ĐỂ KÍCH HOẠT CAMERA PI 5...")
    print(f"📡 Broker: {BROKER}:{PORT} | Topic: {TOPIC}")
    print("=" * 70)

    client = mqtt.Client()
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        time.sleep(0.5)
    except Exception as e:
        print(f"❌ Không thể kết nối tới Broker {BROKER}: {e}")
        return

    # Dữ liệu khói & bụi siêu mịn vọt đỉnh mô phỏng đám cháy thật
    fire_sensor_payload = {
        "elapsed_ms": 999999,
        "temperature": 37.8,
        "humidity": 42.0,
        "eCO2": 950,
        "TVOC": 780,
        "PM1_0": 310,
        "PM2_5": 620,
        "PM10": 690,
        "NC0_3": 14200,
        "NC0_5": 4500,
        "NC1_0": 1150,
        "NC2_5": 180,
        "NC5_0": 24,
        "NC10": 6
    }

    client.publish(TOPIC, json.dumps(fire_sensor_payload))
    print("✅ ĐÃ GỬI XONG BẢN TIN CẢM BIẾN CHÁY:")
    print(f"   -> PM2.5: 620 ug/m3 | NC0.3: 14,200 | TVOC: 780 ppb | Temp: 37.8°C")
    print("\n👀 HÃY NHÌN VÀO MÀN HÌNH TERMINAL CỦA PI 5:")
    print("   -> Bạn sẽ thấy log màu đỏ: '⚡ [ĐÁNH THỨC CAMERA] XGBoost phát hiện nguy cơ!...'")
    print("   -> Camera Picamera2 trên Pi 5 sẽ bật sáng và chụp các khung hình để kiểm tra!")

    time.sleep(1)
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
