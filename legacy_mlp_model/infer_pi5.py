"""
infer_pi5.py
Script chạy suy luận (Inference) mô hình Cảnh báo cháy MLP trên Raspberry Pi 5 bằng PyTorch (TorchScript).
Không phụ thuộc vào bất kỳ backend phức tạp nào (chỉ cần: pip install torch numpy).

Mô hình: fire_alarm_model_jit.pt (được sinh bởi TorchScript, tối ưu hóa cấu trúc 4 tầng ẩn từ Giải thuật di truyền GA)
Bộ chuẩn hóa: scaler_params.json
"""

import os
import sys
import time
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import torch

# 1. Cấu hình thiết bị & nạp mô hình TorchScript
device = torch.device('cpu')  # Raspberry Pi 5 sử dụng CPU ARM Cortex-A76 4 nhân
MODEL_PATH = 'fire_alarm_model_jit.pt'
SCALER_PATH = 'scaler_params.json'

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Không tìm thấy file mô hình '{MODEL_PATH}'. Hãy đặt cùng thư mục với script này.")

if not os.path.exists(SCALER_PATH):
    raise FileNotFoundError(f"Không tìm thấy file chuẩn hóa '{SCALER_PATH}'. Hãy đặt cùng thư mục với script này.")

print("=" * 70)
print("KHỞI TẠO ENGINE SUY LUẬN PYTORCH TRÊN RASPBERRY PI 5")
print("=" * 70)

# Nạp mô hình TorchScript (Không cần định nghĩa class Python, tự chứa toàn bộ kiến trúc)
model = torch.jit.load(MODEL_PATH, map_location=device)
model.eval()
print(f"[OK] Đã nạp thành công mô hình TorchScript: '{MODEL_PATH}'")

# Nạp thông số chuẩn hóa StandardScaler
with open(SCALER_PATH, 'r', encoding='utf-8') as f:
    scaler_info = json.load(f)

FEATURE_NAMES = scaler_info['features']
SCALER_MEAN = np.array(scaler_info['mean'], dtype=np.float32)
SCALER_SCALE = np.array(scaler_info['scale'], dtype=np.float32)
print(f"[OK] Đã nạp thông số chuẩn hóa cho {len(FEATURE_NAMES)} đặc trưng cảm biến.")
print("=" * 70)

def preprocess_sensor_data(raw_features):
    """
    Chuẩn hóa dữ liệu thô từ cảm biến IoT theo thang đo StandardScaler.
    raw_features: list hoặc numpy array gồm 12 giá trị cảm biến
    """
    raw_arr = np.array(raw_features, dtype=np.float32)
    scaled_arr = (raw_arr - SCALER_MEAN) / SCALER_SCALE
    tensor_input = torch.tensor(scaled_arr, dtype=torch.float32).unsqueeze(0).to(device)
    return tensor_input

def predict_fire(sensor_readings):
    """
    Dự đoán nguy cơ cháy từ dữ liệu cảm biến:
    Trả về:
        is_fire (bool): True nếu có cháy, False nếu an toàn
        prob_fire (float): Xác suất cháy (0.0 đến 1.0)
        latency_ms (float): Thời gian suy luận tính bằng mili-giây
    """
    input_tensor = preprocess_sensor_data(sensor_readings)
    
    t0 = time.perf_counter()
    with torch.no_grad():
        logits = model(input_tensor)
        probs = torch.softmax(logits, dim=1)
        prob_fire = probs[0, 1].item()
        pred_class = logits.argmax(dim=1).item()
    t1 = time.perf_counter()
    
    latency_ms = (t1 - t0) * 1000.0
    return bool(pred_class == 1), prob_fire, latency_ms

# ==============================================================================
# DEMO THỬ NGHIỆM TRÊN CÁC MẪU DỮ LIỆU CẢM BIẾN
# ==============================================================================
if __name__ == '__main__':
    print("\n--- THỬ NGHIỆM DỰ ĐOÁN MẪU THỰC TẾ ---")
    
    # Thứ tự 12 đặc trưng:
    # ['Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]', 'Raw H2', 'Raw Ethanol',
    #  'Pressure[hPa]', 'PM1.0', 'PM2.5', 'NC0.5', 'NC1.0', 'NC2.5']
    
    # Mẫu 1: Dữ liệu thực tế khi an toàn (Không cháy)
    sample_safe = [20.0, 57.36, 0.0, 400.0, 12306.0, 18520.0, 939.735, 0.0, 0.0, 0.0, 0.0, 0.0]
    # Mẫu 2: Dữ liệu thực tế khi có cháy
    sample_fire = [9.38, 56.86, 11.0, 400.0, 13347.0, 20160.0, 939.575, 1.78, 1.85, 12.25, 1.91, 0.04]

    for title, sample in [("Mẫu Môi trường Bình thường (Safe)", sample_safe),
                          ("Mẫu Khói / Nhiệt độ cao (Fire Hazard)", sample_fire)]:
        is_fire, prob, latency = predict_fire(sample)
        status_text = "[CẢNH BÁO CHÁY NGUY HIỂM!]" if is_fire else "[AN TOÀN - KHÔNG CÓ CHÁY]"
        print(f"\n{title}:")
        print(f"  > Trạng thái     : {status_text}")
        print(f"  > Xác suất cháy  : {prob * 100:.2f}%")
        print(f"  > Độ trễ suy luận: {latency:.3f} ms")

    # Benchmark tốc độ suy luận trên 1,000 lượt
    print("\n" + "=" * 70)
    print("BENCHMARK HIỆU NĂNG SUY LUẬN (1,000 LƯỢT TIẾP TỤC):")
    print("=" * 70)
    test_input = preprocess_sensor_data(sample_fire)
    
    # Warmup
    for _ in range(50):
        _ = model(test_input)
        
    runs = 1000
    start_time = time.perf_counter()
    with torch.no_grad():
        for _ in range(runs):
            _ = model(test_input)
    total_time = time.perf_counter() - start_time
    
    avg_latency = (total_time / runs) * 1000.0
    throughput = runs / total_time
    
    print(f"  > Tổng thời gian cho {runs:,} lần suy luận: {total_time:.3f} s")
    print(f"  > Độ trễ trung bình mỗi mẫu (Latency)  : {avg_latency:.4f} ms")
    print(f"  > Tốc độ xử lý (Throughput)            : {throughput:,.1f} mẫu/giây (FPS)")
    print("=" * 70)
