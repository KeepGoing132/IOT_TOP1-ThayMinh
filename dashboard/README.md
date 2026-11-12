# AIoT FIRE SENTINEL - TABLER WEB DASHBOARD

Hệ thống Dashboard giám sát trung tâm (SOC) thời gian thực cho hệ thống Cảnh báo cháy 2 tầng (XGBoost + YOLO NCNN).

---

## 1. Tính Năng Nổi Bật
- **Giao diện Tabler Core UI hiện đại:** Chuẩn thiết kế Security Operations Center với chế độ Sáng/Tối (Dark/Light mode).
- **Kết nối WebSocket trực tiếp:** Dữ liệu cảm biến từ ESP32 (`iot/test/request`) và quyết định AI (`iot/test/response`) cập nhật tức thì không cần reload trang.
- **Biểu đồ thời gian thực (ApexCharts):** Vẽ luồng sóng biến thiên của PM2.5, TVOC và Nhiệt độ theo từng giây.
- **Khung xem ảnh bằng chứng Tầng 2:** Tự động hiển thị khung hình có bounding box ngọn lửa khi YOLO xác thực có cháy.
- **Thư viện ảnh (Evidence Gallery):** Lưu trữ và xem lại tất cả các lần phát hiện cháy, hỗ trợ phóng to toàn màn hình (Modal Lightbox).
- **Cảnh báo nhấp nháy còi:** Hiệu ứng viền đỏ phát sáng (Pulse effect) và thông báo khi còi ESP32 đang hú.

---

## 2. Cách 1: Chạy Thử Trực Tiếp Trên Máy Tính (PC)

### Bước 1: Khởi động server Dashboard
Mở PowerShell tại thư mục `dashboard` và chạy:
```powershell
cd C:\Users\OS\Desktop\IOT\dashboard
python app.py --broker 10.156.225.221 --port 5000
```

### Bước 2: Mở trình duyệt xem
Truy cập: [http://localhost:5000](http://localhost:5000)

*(Server sẽ tự động kết nối tới MQTT Broker `10.156.225.221:1883` trên Pi 5 để nhận dữ liệu từ ESP32).*

---

## 3. Cách 2: Chạy Bằng Docker Trên Máy Tính (PC)

Nếu bạn muốn chạy dạng container trên máy tính:
```bash
cd dashboard
docker compose up -d --build
```
Mở trình duyệt: `http://localhost:5000`

---

## 4. Cách 3: Đóng Gói Và Triển Khai Lên Raspberry Pi 5

### Bước 1: Chuyển thư mục `dashboard` sang Pi 5
Trên máy tính của bạn, mở terminal gõ lệnh `scp`:
```bash
scp -r C:\Users\OS\Desktop\IOT\dashboard khoapi5@10.156.225.221:~/yolo/
```

### Bước 2: Chạy trên Pi 5 bằng Docker (Khuyên dùng)
Đăng nhập SSH vào Pi 5:
```bash
ssh khoapi5@10.156.225.221
cd ~/yolo/dashboard

# Build và chạy container trực tiếp trên nền chip ARM64 của Pi 5:
sudo docker compose up -d --build
```

*(Hoặc nếu chạy Python trực tiếp trên Pi 5: `python app.py --broker localhost --port 5000`)*

### Bước 3: Truy cập Dashboard từ bất kỳ máy nào trong mạng LAN
Mở trình duyệt trên máy tính hoặc điện thoại:
```
http://10.156.225.221:5000
```
