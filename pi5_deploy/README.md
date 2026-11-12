# HƯỚNG DẪN TRIỂN KHAI AIoT BÁO CHÁY 2 TẦNG (PI 5 + ESP32)

Hệ thống kết hợp:
- **Tầng 1 (Sensor Fusion 24/7):** XGBoost Set E (36 đặc trưng động) xử lý dữ liệu từ ESP32 qua MQTT `iot/test/request`.
- **Tầng 2 (Xác thực trực quan):** Picamera2 + YOLO NCNN (`ncnn_fire_flame`) quét ngắt quãng theo từng giây với cơ chế Early Exit.
- **Phản hồi điều khiển còi:** Gửi tín hiệu kích hoạt còi về `iot/test/response` cho ESP32.

---

## 1. Cấu trúc gói tin gửi về ESP32 (`iot/test/response`)

Khi **YOLO xác thực có ngọn lửa thật**:
```json
{
  "buzzer": 1,
  "alarm": 1,
  "cmd": "BUZZER_ON",
  "status": "FIRE_CONFIRMED",
  "is_fire": true,
  "visual_verified": true,
  "confidence": 0.9985,
  "evidence_image": "fire_evidence_20261110_144500.jpg",
  "pm25": 256.0,
  "tvoc": 85.0,
  "temp": 32.5,
  "timestamp": "2026-11-10 14:45:00"
}
```

Khi **An toàn hoặc Hủy cảnh báo giả** (ví dụ bình xịt làm tăng chỉ số nhưng không có lửa):
```json
{
  "buzzer": 0,
  "alarm": 0,
  "cmd": "BUZZER_OFF",
  "status": "NORMAL",
  "is_fire": false,
  "visual_verified": false
}
```

---

## 2. Đoạn mã mẫu trên ESP32 để nhận lệnh bật còi

### Cách 1: Sử dụng thư viện ArduinoJson
```cpp
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<512> doc;
  deserializeJson(doc, payload, length);

  int buzzerState = doc["buzzer"] | 0;

  if (buzzerState == 1) {
    digitalWrite(BUZZER_PIN, HIGH); // BẬT CÒI BÁO ĐỘNG
    Serial.println("🚨 BÁO ĐỘNG CHÁY XÁC THỰC! ĐÃ BẬT CÒI!");
  } else {
    digitalWrite(BUZZER_PIN, LOW);  // TẮT CÒI
  }
}
```

### Cách 2: Tìm chuỗi trực tiếp (Không cần thư viện JSON)
```cpp
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  if (message.indexOf("BUZZER_ON") >= 0 || message.indexOf("\"buzzer\": 1") >= 0) {
    digitalWrite(BUZZER_PIN, HIGH); // BẬT CÒI
  } else {
    digitalWrite(BUZZER_PIN, LOW);  // TẮT CÒI
  }
}
```

---

## 3. Khởi chạy trên Raspberry Pi 5

```bash
cd ~/yolo/pi5_deploy

# Chạy với cấu hình tiêu chuẩn:
python infer_pi5_xgb.py

# Tuỳ chỉnh thêm số frame và khoảng cách giây nếu muốn:
# python infer_pi5_xgb.py --frames 5 --interval 1.0 --req-positives 3
```
