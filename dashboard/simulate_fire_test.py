"""
simulate_fire_test.py
=============================================================================
Kịch bản giả lập (Fake / Simulation) để kiểm thử toàn diện Dashboard:
1. Tạo ảnh giả lập ngọn lửa có Bounding Box của YOLO NCNN
2. Bắn luồng dữ liệu cảm biến tăng vọt (PM2.5, TVOC, Nhiệt độ) qua MQTT
3. Bắn bản tin cảnh báo [FIRE_CONFIRMED] để kích hoạt còi và ảnh trên Dashboard
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

# Cấu hình Broker
BROKER = os.getenv("MQTT_BROKER", "10.156.225.221")
PORT = int(os.getenv("MQTT_PORT", 1883))
REQ_TOPIC = "iot/test/request"
RES_TOPIC = "iot/test/response"

# Thư mục evidence
BASE_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE_DIR / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# Also check pi5_deploy
PI5_DEPLOY_DIR = Path("C:/Users/OS/Desktop/IOT/pi5_deploy")

def generate_fake_fire_image(filename: str):
    """Vẽ một bức ảnh giả lập ngọn lửa thật trong bóng tối kèm Bounding Box YOLO"""
    # Khung hình 640x480
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Tạo nền phòng tối mờ
    img[:] = (20, 22, 28)
    
    # Vẽ nền sàn nhà / bàn
    cv2.rectangle(img, (0, 380), (640, 480), (35, 38, 45), -1)
    cv2.line(img, (0, 380), (640, 380), (60, 65, 75), 2)
    
    # Vẽ đốm lửa bập bùng (Lớp ngoài: Đỏ cam)
    cv2.ellipse(img, (320, 310), (70, 110), 0, 0, 360, (15, 70, 230), -1)
    # Lớp giữa: Vàng cam
    cv2.ellipse(img, (320, 325), (45, 80), 0, 0, 360, (20, 160, 255), -1)
    # Lõi ngọn lửa: Vàng trắng sáng
    cv2.ellipse(img, (320, 340), (22, 45), 0, 0, 360, (120, 235, 255), -1)

    # Hiệu ứng khói mờ bốc lên phía trên
    for r in range(5):
        cv2.circle(img, (320 + np.random.randint(-25, 25), 180 - r * 25), 35 + r * 8, (60, 60, 65), -1)
    
    # Làm mờ tự nhiên (Blur)
    img = cv2.GaussianBlur(img, (15, 15), 0)

    # Vẽ Bounding Box YOLO (Màu đỏ rực)
    box_x1, box_y1, box_x2, box_y2 = 230, 180, 410, 400
    cv2.rectangle(img, (box_x1, box_y1), (box_x2, box_y2), (0, 0, 240), 2)
    
    # Vẽ nhãn nhận diện của YOLO: "fire: 97.4%"
    label = "fire: 97.4%"
    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
    cv2.rectangle(img, (box_x1, box_y1 - 25), (box_x1 + w + 10, box_y1), (0, 0, 240), -1)
    cv2.putText(img, label, (box_x1 + 5, box_y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    # Timestamp góc dưới
    dt_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S [YOLO_NCNN Pi5]")
    cv2.putText(img, dt_text, (20, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    # Lưu vào thư mục evidence của dashboard
    out_path = EVIDENCE_DIR / filename
    cv2.imwrite(str(out_path), img)
    
    # Lưu thêm vào pi5_deploy nếu có
    if PI5_DEPLOY_DIR.exists():
        cv2.imwrite(str(PI5_DEPLOY_DIR / filename), img)
        
    return str(out_path)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mô phỏng dữ liệu Cháy & Ảnh YOLO")
    parser.add_argument("--broker", type=str, default=BROKER, help="Địa chỉ MQTT Broker")
    parser.add_argument("--port", type=int, default=PORT, help="Cổng MQTT Broker")
    parser.add_argument("--reset", action="store_true", help="Reset trạng thái về AN TOÀN và tắt còi")
    args = parser.parse_args()

    client = mqtt.Client()
    try:
        client.connect(args.broker, args.port, 60)
        client.loop_start()
    except Exception as e:
        print(f"❌ Không thể kết nối tới Broker {args.broker}:{args.port}: {e}")
        return

    time.sleep(1)

    if args.reset:
        print("🟢 Đang gửi lệnh RESET về An Toàn & Tắt còi ESP32...")
        reset_payload = {
            "status": "NORMAL",
            "buzzer": 0,
            "alarm": 0,
            "cmd": "BUZZER_OFF",
            "is_fire": False,
            "visual_verified": False,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        client.publish(RES_TOPIC, json.dumps(reset_payload))
        print(f"✅ Đã gửi BUZZER_OFF tới topic '{RES_TOPIC}'. Còi đã tắt!")
        time.sleep(1)
        client.loop_stop()
        client.disconnect()
        return

    # -------------------------------------------------------------------------
    # BƯỚC 1: TRẠNG THÁI BÌNH THƯỜNG (3 MẪU)
    # -------------------------------------------------------------------------
    print("\n[GIAI ĐOẠN 1] Môi trường bình thường (An toàn)...")
    for i in range(3):
        normal_packet = {
            "elapsed_ms": 1000 * (i + 1),
            "temperature": 25.5 + np.random.uniform(-0.3, 0.3),
            "humidity": 55.0 + np.random.uniform(-1, 1),
            "eCO2": 405 + np.random.randint(-5, 5),
            "TVOC": 18 + np.random.randint(-3, 3),
            "PM1_0": 3,
            "PM2_5": 5,
            "PM10": 6,
            "NC0_3": 350 + np.random.randint(-15, 15),
            "NC0_5": 110,
            "NC1_0": 25,
            "NC2_5": 3,
            "NC5_0": 0,
            "NC10": 0
        }
        client.publish(REQ_TOPIC, json.dumps(normal_packet))
        print(f"  -> Gửi Telemetry Bình Thường #{i+1}: PM2.5=5 ug/m3, TVOC=18 ppb, Temp=25.5°C")
        time.sleep(2)

    # -------------------------------------------------------------------------
    # BƯỚC 2: KHÓI BẮT ĐẦU TĂNG ĐỘT BIẾN (XGBOOST PHÁT HIỆN NGUY CƠ)
    # -------------------------------------------------------------------------
    print("\n[GIAI ĐOẠN 2] ⚡ Bắt đầu có khói bốc lên mạnh! Các chỉ số tăng vọt...")
    smoke_packet = {
        "elapsed_ms": 7000,
        "temperature": 29.8,
        "humidity": 52.0,
        "eCO2": 680,
        "TVOC": 340,
        "PM1_0": 110,
        "PM2_5": 280,
        "PM10": 320,
        "NC0_3": 5400,
        "NC0_5": 1600,
        "NC1_0": 420,
        "NC2_5": 50,
        "NC5_0": 8,
        "NC10": 2
    }
    client.publish(REQ_TOPIC, json.dumps(smoke_packet))
    print("  -> Gửi Telemetry Khói Tăng: PM2.5=280 ug/m3, TVOC=340 ppb (XGBoost đánh thức Camera...)")
    time.sleep(2.5)

    # -------------------------------------------------------------------------
    # BƯỚC 3: TẠO ẢNH NGỌN LỬA VÀ BẮN BÁO ĐỘNG ĐỎ CỦA YOLO NCNN
    # -------------------------------------------------------------------------
    now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    fake_img_name = f"fire_evidence_{now_tag}.jpg"
    print(f"\n[GIAI ĐOẠN 3] 📸 Đang sinh ảnh giả lập ngọn lửa: {fake_img_name}...")
    saved_path = generate_fake_fire_image(fake_img_name)
    print(f"  ✅ Đã lưu ảnh bằng chứng vào: {saved_path}")

    # Gói tin cảm biến đỉnh điểm của đám cháy
    fire_packet = {
        "elapsed_ms": 10000,
        "temperature": 38.6,
        "humidity": 45.0,
        "eCO2": 950,
        "TVOC": 890,
        "PM1_0": 350,
        "PM2_5": 620,
        "PM10": 710,
        "NC0_3": 14200,
        "NC0_5": 4800,
        "NC1_0": 1200,
        "NC2_5": 190,
        "NC5_0": 25,
        "NC10": 6
    }
    client.publish(REQ_TOPIC, json.dumps(fire_packet))

    # Gói tin phản hồi chính thức từ Tầng 2 YOLO kích hoạt còi ESP32
    fire_alarm_response = {
        "status": "FIRE_CONFIRMED",
        "buzzer": 1,
        "alarm": 1,
        "cmd": "BUZZER_ON",
        "is_fire": True,
        "xgb_prediction": "fire",
        "visual_verified": True,
        "confidence": 0.974,
        "evidence_image": fake_img_name,
        "pm25": 620,
        "tvoc": 890,
        "temp": 38.6,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    client.publish(RES_TOPIC, json.dumps(fire_alarm_response))
    print(f"\n🚨🚨 [ĐÃ GỬI BÁO ĐỘNG ĐỎ VỀ TOPIC {RES_TOPIC}]")
    print(f"  👉 Còi ESP32: BẬT (buzzer=1, cmd=BUZZER_ON)")
    print(f"  👉 Ảnh bằng chứng: {fake_img_name}")
    print(f"  👉 Độ tin cậy YOLO: 97.4%")
    print(f"  👉 PM2.5: 620 ug/m3, TVOC: 890 ppb, Temp: 38.6°C")

    print("\n" + "=" * 75)
    print("✨ XONG! Bây giờ bạn hãy mở trình duyệt: http://localhost:5000")
    print("   -> Xem thẻ Báo Động viền đỏ nhấp nháy")
    print("   -> Xem khung camera hiển thị ảnh ngọn lửa vừa tạo")
    print("   -> Xem biểu đồ PM2.5 và TVOC vọt đỉnh")
    print("   -> Xem bảng Audit Log ghi nhận báo động đỏ!")
    print("=" * 75)

    time.sleep(3)
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
