# HỆ THỐNG AIoT CẢNH BÁO CHÁY THÔNG MINH (XGBOOST & RASPBERRY PI 5)

## 📁 Cấu Trúc Thư Mục Dự Án (Đã Tối Ưu Hóa)

```text
IOT/
├── data/                               # Dữ liệu cảm biến thực tế từ phần cứng ESP32
│   ├── sensor_data.csv                 # Dữ liệu đợt cháy (Fire session)
│   └── sensor_data_1.csv               # Dữ liệu khói dư & bình thường (Normal session)
│
├── pi5_deploy/                         # Gói triển khai hoàn chỉnh cho Raspberry Pi 5
│   ├── infer_pi5_xgb.py                # Script suy luận MQTT nhận dữ liệu từ ESP32
│   ├── fire_xgb_model.json             # Mô hình XGBoost (Set E - 36 features)
│   ├── fire_pipeline_config.json       # Cấu hình 36 features thời gian
│   ├── requirements.txt                # Danh sách thư viện cho Pi 5
│   ├── test_sample.csv                 # Dữ liệu mẫu test offline
│   └── README.md                       # Hướng dẫn chạy trên Pi 5
│
├── tools_and_scripts/                  # Các script công cụ phụ trợ
│   ├── save_data.py                    # Script thu thập dữ liệu qua cổng Serial
│   ├── build_notebook.py               # Script tự động tạo notebook fire_det.ipynb
│   └── run_notebook_cells.py           # Script chạy notebook
│
├── legacy_mlp_model/                   # Lưu trữ dự án cũ (PyTorch MLP từ Kaggle)
│   ├── aiot-fire-alarm-detection.ipynb
│   ├── smoke_detection_iot.csv
│   ├── best_mlp_fire_alarm.pt
│   └── ...
│
├── fire_det.ipynb                      # [FILE CHÍNH] Toàn bộ quy trình EDA, Feature Engineering & Huấn luyện
└── GUIDE.md                            # Hướng dẫn 10 bước thực nghiệm
```

---

## 🚀 Các Dịch Vụ Đang Chạy

### 1. MQTT Explorer (Docker Web UI)
Đang chạy trên máy tính tại cổng **4000**:
* **URL:** [http://localhost:4000](http://localhost:4000)
* Dùng để theo dõi trực quan dữ liệu MQTT từ Raspberry Pi 5 và ESP32.

### 2. Suy Luận Trên Raspberry Pi 5
* **Topic nhận từ ESP32:** `iot/test/request`
* **Topic gửi kết quả cảnh báo:** `iot/test/response`
