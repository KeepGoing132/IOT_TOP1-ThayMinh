"""
infer_pi5_xgb.py
=============================================================================
Hệ Thống AIoT Cảnh Báo Cháy 2 Tầng Trên Raspberry Pi 5
  - Tầng 1 (Sensor Fusion 24/7): XGBoost (Set E - 36 features) nhận MQTT
  - Tầng 2 (Visual Verification): Picamera2 + YOLO NCNN ("ncnn_fire_flame")

Cơ chế xác thực Camera thông minh:
  Quét đa khung hình giãn cách theo từng giây (mặc định 5 frame, 1s/frame):
  -> Cơ chế Early Exit: Đủ 3 frame xác nhận có lửa -> BÁO ĐỘNG NGAY
  -> Loại trừ hoàn toàn báo động giả (bình xịt khí, đèn xe quét qua, áo màu cam)
  -> Gửi tín hiệu kích hoạt còi ({"buzzer": 1, "alarm": 1, "cmd": "BUZZER_ON"})
     về topic MQTT "iot/test/response" để ESP32 bật còi báo động!
=============================================================================
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
import numpy as np
import pandas as pd
import xgboost as xgb
import paho.mqtt.client as mqtt
import cv2

# Thử import Picamera2 và YOLO NCNN
HAVE_YOLO = False
try:
    from picamera2 import Picamera2
    from yolo_ncnn import YOLO_ncnn
    HAVE_YOLO = True
except ImportError:
    pass

# Mã màu ANSI
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"

def calc_slope(window):
    n = len(window)
    if n < 2:
        return 0.0
    x = np.arange(n)
    x_mean = (n - 1) / 2.0
    y_mean = np.mean(window)
    denom = np.sum((x - x_mean) ** 2)
    if denom == 0:
        return 0.0
    return float(np.sum((x - x_mean) * (window - y_mean)) / denom)

class FeatureExtractorSetE:
    def __init__(self, model_features, max_buffer=10):
        self.model_features = model_features
        self.max_buffer = max_buffer
        self.buffer = []

    def push(self, raw_dict):
        self.buffer.append(raw_dict)
        if len(self.buffer) > self.max_buffer:
            self.buffer.pop(0)

        df = pd.DataFrame(self.buffer)

        # 1. Lag Features (Set B)
        df['pm2_5_lag_3s'] = df['PM2_5_ug_m3'].shift(1)
        df['pm2_5_lag_6s'] = df['PM2_5_ug_m3'].shift(2)
        df['pm2_5_lag_9s'] = df['PM2_5_ug_m3'].shift(3)
        df['tvoc_lag_3s'] = df['TVOC_ppb'].shift(1)
        df['tvoc_lag_6s'] = df['TVOC_ppb'].shift(2)
        df['eco2_lag_3s'] = df['eCO2_ppm'].shift(1)

        # 2. Delta Features (Set C)
        df['pm1_0_delta_3s'] = df['PM1_0_ug_m3'].diff(1)
        df['pm2_5_delta_3s'] = df['PM2_5_ug_m3'].diff(1)
        df['pm10_delta_3s'] = df['PM10_ug_m3'].diff(1)
        df['tvoc_delta_3s'] = df['TVOC_ppb'].diff(1)
        df['eco2_delta_3s'] = df['eCO2_ppm'].diff(1)
        df['temperature_delta_3s'] = df['Temperature_C'].diff(1)
        df['humidity_delta_3s'] = df['Humidity_percent'].diff(1)
        df['pm2_5_delta_6s'] = df['PM2_5_ug_m3'].diff(2)
        df['tvoc_delta_6s'] = df['TVOC_ppb'].diff(2)

        # 3. Rolling Features 10s (Set D)
        win = 4
        df['pm2_5_mean_10s'] = df['PM2_5_ug_m3'].rolling(win, min_periods=1).mean()
        df['pm2_5_max_10s'] = df['PM2_5_ug_m3'].rolling(win, min_periods=1).max()
        df['pm2_5_std_10s'] = df['PM2_5_ug_m3'].rolling(win, min_periods=1).std().fillna(0)
        df['pm2_5_slope_10s'] = df['PM2_5_ug_m3'].rolling(win, min_periods=1).apply(calc_slope, raw=False).fillna(0)

        df['tvoc_mean_10s'] = df['TVOC_ppb'].rolling(win, min_periods=1).mean()
        df['tvoc_max_10s'] = df['TVOC_ppb'].rolling(win, min_periods=1).max()
        df['tvoc_slope_10s'] = df['TVOC_ppb'].rolling(win, min_periods=1).apply(calc_slope, raw=False).fillna(0)

        df['eco2_mean_10s'] = df['eCO2_ppm'].rolling(win, min_periods=1).mean()

        df = df.bfill()
        latest_sample = df[self.model_features].iloc[[-1]]
        return latest_sample

class YOLOCameraVerifier:
    def __init__(self, model_name="ncnn_fire_flame", enable_cam=True):
        self.enabled = enable_cam and HAVE_YOLO
        self.model = None
        self.picam2 = None

        if not self.enabled:
            if not HAVE_YOLO:
                print(f"{YELLOW}[Cảnh báo]{RESET} Chưa cài picamera2 hoặc yolo_ncnn. Chạy chế độ Cảm biến.")
            return

        try:
            print(f"{BOLD}[TẦNG 2]{RESET} Đang nạp model YOLO NCNN: '{model_name}'...")
            self.model = YOLO_ncnn(model_name)
            
            print(f"{BOLD}[TẦNG 2]{RESET} Đang khởi động Picamera2 (640x480 RGB888)...")
            self.picam2 = Picamera2()
            self.picam2.configure(
                self.picam2.create_video_configuration(
                    main={"size": (640, 480), "format": "RGB888"}
                )
            )
            self.picam2.start()
            print(f"{GREEN}{BOLD}[OK]{RESET} Tầng 2 (Camera YOLO NCNN) đã ở chế độ sẵn sàng đánh thức!\n")
        except Exception as e:
            print(f"{RED}[LỖI KHỞI ĐỘNG CAMERA/YOLO]{RESET} {e}")
            self.enabled = False

    def verify_fire_temporal(self, num_frames=5, delay_between_frames=1.0, required_positives=3, evidence_dir="evidence"):
        """
        Quét đa khung hình giãn cách theo từng giây (mặc định 5 frame, 1s/frame):
        - LƯU TOÀN BỘ 5 KHUNG HÌNH VÀO THƯ MỤC evidence/ (KỂ CẢ CÓ CHÁY HAY KHÔNG)
        - Nếu phát hiện ngọn lửa: vẽ bounding box đỏ của YOLO
        - Trả về: (is_confirmed, positive_count, frames_scanned, main_image, scanned_files, avg_lat_ms)
        """
        os.makedirs(evidence_dir, exist_ok=True)
        if not self.enabled:
            return False, 0, 0, None, [], 0.0

        positive_frames = 0
        best_results = None
        latencies = []
        frames_scanned = 0
        scanned_files = []
        now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

        for i in range(num_frames):
            frames_scanned += 1
            t0 = time.perf_counter()
            frame = self.picam2.capture_array()
            results = self.model.predict(frame)
            t1 = time.perf_counter()

            latencies.append((t1 - t0) * 1000.0)

            has_flame = bool(results and len(results) > 0)
            if has_flame:
                positive_frames += 1
                best_results = results
                # Vẽ bounding box lên frame
                self.model.draw(frame, results)
                tag_label = "flame"
                print(f"    {RED}🔥 [Frame {i+1}/{num_frames}]{RESET} PHÁT HIỆN LỬA ({len(results)} mục tiêu) | +{positive_frames}/{required_positives}")
            else:
                tag_label = "safe"
                print(f"    {GREEN}🛡️ [Frame {i+1}/{num_frames}]{RESET} Không phát hiện lửa")

            # Lưu từng frame vào thư mục evidence/
            frame_filename = f"scan_{now_tag}_f{i+1}_{tag_label}.jpg"
            frame_filepath = os.path.join(evidence_dir, frame_filename)
            bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cv2.imwrite(frame_filepath, bgr_frame)
            scanned_files.append(frame_filename)

            # Nghỉ giữa các frame (trừ frame cuối)
            if i < num_frames - 1:
                time.sleep(delay_between_frames)

        avg_lat_ms = float(np.mean(latencies)) if latencies else 0.0
        is_confirmed = bool(positive_frames >= required_positives)

        # Chọn ảnh đại diện chính để hiển thị to trên Dashboard:
        # Nếu có frame phát hiện lửa -> chọn frame có lửa
        # Nếu không có frame nào có lửa -> chọn frame cuối cùng vừa chụp
        main_image = None
        for fn in scanned_files:
            if "flame" in fn:
                main_image = fn
                break
        if not main_image and len(scanned_files) > 0:
            main_image = scanned_files[-1]

        return is_confirmed, positive_frames, frames_scanned, main_image, scanned_files, avg_lat_ms

class Pi5FireInferenceEngine:
    def __init__(self, model_file="fire_xgb_model.json", config_file="fire_pipeline_config.json"):
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Không tìm thấy file mô hình: {model_file}")
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình: {config_file}")

        print(f"{BOLD}[INIT]{RESET} Nạp cấu hình từ: {config_file}")
        with open(config_file, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)

        self.model_features = self.cfg["model_features"]
        self.classes = self.cfg["classes"]

        print(f"{BOLD}[INIT]{RESET} Nạp mô hình XGBoost: {model_file}")
        self.model = xgb.XGBClassifier()
        self.model.load_model(model_file)

        self.extractor = FeatureExtractorSetE(self.model_features)
        print(f"{GREEN}{BOLD}[OK]{RESET} Khởi tạo Engine thành công ({len(self.model_features)} features - Set E)\n")

    def predict(self, raw_dict):
        t0 = time.perf_counter()
        feat_df = self.extractor.push(raw_dict)
        probs = self.model.predict_proba(feat_df)[0]
        pred_idx = int(np.argmax(probs))
        pred_class = self.classes[pred_idx]
        conf = float(probs[pred_idx])
        t1 = time.perf_counter()
        latency_ms = (t1 - t0) * 1000.0

        prob_dict = {cls: float(p) for cls, p in zip(self.classes, probs)}
        return pred_class, conf, prob_dict, latency_ms

def parse_payload(payload_str):
    payload_str = payload_str.strip()
    try:
        data = json.loads(payload_str)
        mapping = {
            "PM1_0_ug_m3": ["PM1_0_ug_m3", "pm1_0", "pm10_ug", "pm1", "PM1_0"],
            "PM2_5_ug_m3": ["PM2_5_ug_m3", "pm2_5", "pm25", "pm2_5_ug", "PM2_5"],
            "PM10_ug_m3": ["PM10_ug_m3", "pm10", "pm10_0", "PM10"],
            "NC0_3_per_0.1L": ["NC0_3_per_0.1L", "nc0_3", "nc03", "NC0_3"],
            "NC0_5_per_0.1L": ["NC0_5_per_0.1L", "nc0_5", "nc05", "NC0_5"],
            "NC1_0_per_0.1L": ["NC1_0_per_0.1L", "nc1_0", "nc10", "NC1_0"],
            "NC2_5_per_0.1L": ["NC2_5_per_0.1L", "nc2_5", "nc25", "NC2_5"],
            "NC5_0_per_0.1L": ["NC5_0_per_0.1L", "nc5_0", "nc50", "NC5_0"],
            "NC10_per_0.1L": ["NC10_per_0.1L", "nc10", "nc100", "NC10"],
            "TVOC_ppb": ["TVOC_ppb", "tvoc", "tvoc_ppb", "TVOC"],
            "eCO2_ppm": ["eCO2_ppm", "eco2", "eco2_ppm", "eCO2"],
            "Temperature_C": ["Temperature_C", "temperature", "temp", "temp_c", "Temperature"],
            "Humidity_percent": ["Humidity_percent", "humidity", "hum", "humid", "Humidity"]
        }
        raw_dict = {}
        for std_key, alt_keys in mapping.items():
            for alt in alt_keys:
                if alt in data:
                    raw_dict[std_key] = float(data[alt])
                    break
        if len(raw_dict) == 13:
            return raw_dict
    except:
        pass

    try:
        parts = payload_str.split(",")
        if len(parts) >= 14:
            v = [float(x) for x in parts[1:14]]
        elif len(parts) == 13:
            v = [float(x) for x in parts]
        else:
            return None

        return {
            "Temperature_C": v[0], "Humidity_percent": v[1], "eCO2_ppm": v[2], "TVOC_ppb": v[3],
            "PM1_0_ug_m3": v[4], "PM2_5_ug_m3": v[5], "PM10_ug_m3": v[6], "NC0_3_per_0.1L": v[7],
            "NC0_5_per_0.1L": v[8], "NC1_0_per_0.1L": v[9], "NC2_5_per_0.1L": v[10],
            "NC5_0_per_0.1L": v[11], "NC10_per_0.1L": v[12]
        }
    except:
        return None


def print_full_telemetry(timestamp, pred_class, conf, raw, lat_ms):
    if pred_class == "fire":
        status_banner = f"{RED}{BOLD}[FIRE HAZARD - NGUY CƠ CHÁY]{RESET}"
    elif pred_class == "residual_smoke":
        status_banner = f"{YELLOW}{BOLD}[RESIDUAL SMOKE - KHÓI DƯ]{RESET}"
    else:
        status_banner = f"{GREEN}{BOLD}[NORMAL - AN TOÀN]{RESET}"

    print(f"[{timestamp}] {status_banner} | XGB Conf: {conf*100:.1f}% | Latency: {lat_ms:.2f}ms")
    pm_info = f"PM1.0:{raw['PM1_0_ug_m3']:.0f}  PM2.5:{raw['PM2_5_ug_m3']:.0f}  PM10:{raw['PM10_ug_m3']:.0f} (ug/m3)"
    nc_info = f"NC0.3:{raw['NC0_3_per_0.1L']:.0f}  NC0.5:{raw['NC0_5_per_0.1L']:.0f}  NC1.0:{raw['NC1_0_per_0.1L']:.0f}  NC2.5:{raw['NC2_5_per_0.1L']:.0f}  NC5.0:{raw['NC5_0_per_0.1L']:.0f}  NC10:{raw['NC10_per_0.1L']:.0f}"
    print(f"  {CYAN}[PMS5003]{RESET} {pm_info} | {nc_info}")

    sgp_info = f"TVOC:{raw['TVOC_ppb']:.0f} ppb | eCO2:{raw['eCO2_ppm']:.0f} ppm"
    dht_info = f"Temp:{raw['Temperature_C']:.1f}°C | Humid:{raw['Humidity_percent']:.1f}%"
    print(f"  {MAGENTA}[SGP30]{RESET}   {sgp_info}   ---   {YELLOW}[DHT11]{RESET}  {dht_info}")

def main():
    parser = argparse.ArgumentParser(description="Hệ thống AIoT Báo cháy 2 tầng: XGBoost + YOLO NCNN")
    parser.add_argument("--broker", type=str, default="localhost", help="Địa chỉ MQTT Broker")
    parser.add_argument("--port", type=int, default=1883, help="Cổng MQTT Broker")
    parser.add_argument("--req-topic", type=str, default="iot/test/request", help="Topic nhận từ ESP32")
    parser.add_argument("--res-topic", type=str, default="iot/test/response", help="Topic gửi kết quả điều khiển còi")
    parser.add_argument("--yolo-model", type=str, default="ncnn_fire_flame", help="Tên model YOLO NCNN")
    parser.add_argument("--frames", type=int, default=5, help="Số khung hình camera quét (mặc định: 5)")
    parser.add_argument("--interval", type=float, default=1.0, help="Khoảng giãn cách giữa các frame (giây, mặc định: 1.0s)")
    parser.add_argument("--req-positives", type=int, default=3, help="Số frame phát hiện lửa tối thiểu để xác nhận (mặc định: 3)")
    parser.add_argument("--no-cam", action="store_true", help="Tắt camera nếu chưa cắm")

    args = parser.parse_args()

    engine = Pi5FireInferenceEngine(
        model_file="fire_xgb_model.json",
        config_file="fire_pipeline_config.json"
    )

    yolo_verifier = YOLOCameraVerifier(
        model_name=args.yolo_model,
        enable_cam=not args.no_cam
    )

    client = mqtt.Client()

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            print(f"{GREEN}{BOLD}[MQTT CONNECTED]{RESET} Đã kết nối Broker: {args.broker}:{args.port}")
            c.subscribe(args.req_topic)
            print(f"{CYAN}👉 Nhận từ ESP32: {args.req_topic}{RESET}")
            print(f"{CYAN}👉 Gửi phản hồi:  {args.res_topic} (Kích hoạt còi ESP32){RESET}\n")
            print("Đang giám sát 2 tầng (XGBoost + YOLO Temporal Verification)...\n" + "=" * 88)
        else:
            print(f"{RED}[LỖI]{RESET} Kết nối MQTT thất bại: rc={rc}")

    def on_message(c, userdata, msg):
        raw_msg = msg.payload.decode("utf-8", errors="ignore")
        raw_dict = parse_payload(raw_msg)
        if raw_dict is None:
            return

        # --- BƯỚC 1: XỬ LÝ TẦNG 1 BẰNG XGBOOST ---
        pred_class, conf, prob_dict, lat_ms = engine.predict(raw_dict)
        now_str = datetime.now().strftime("%H:%M:%S")

        print_full_telemetry(now_str, pred_class, conf, raw_dict, lat_ms)

        visual_verified = False
        final_alert = False
        saved_img = None
        scanned_frames = []

        # --- BƯỚC 2: KÍCH HOẠT TẦNG 2 NẾU XGBOOST BÁO [FIRE] ---
        if pred_class == "fire":
            if yolo_verifier.enabled:
                print(f"  {RED}{BOLD}⚡ [ĐÁNH THỨC CAMERA]{RESET} XGBoost phát hiện nguy cơ! Đang xác thực {args.frames} frames ({args.interval}s/frame, cần {args.req_positives} frames có lửa)...")
                is_confirmed, pos_count, scanned, saved_img, scanned_frames, yolo_lat = yolo_verifier.verify_fire_temporal(
                    num_frames=args.frames,
                    delay_between_frames=args.interval,
                    required_positives=args.req_positives,
                    evidence_dir="evidence"
                )

                if is_confirmed:
                    final_alert = True
                    visual_verified = True
                    print(f"  {RED}{BOLD}🚨🚨 [BÁO ĐỘNG ĐỎ CẤP CAO NHẤT] XÁC THỰC {pos_count}/{scanned} FRAMES CÓ LỬA CHÁY LIÊN TỤC! (YOLO: {yolo_lat:.1f}ms/frame){RESET}")
                else:
                    final_alert = False
                    visual_verified = False
                    print(f"  {YELLOW}{BOLD}🛡️ [HỦY BÁO ĐỘNG GIẢ] Chỉ có {pos_count}/{scanned} frame nghi vấn (Loại trừ: Ánh đèn xe / Bình xịt aerosol)! KHÔNG BẬT CÒI.{RESET}")

                print(f"  📸 Đã lưu toàn bộ {scanned} frames vào thư mục: evidence/")
            else:
                # Nếu không bật camera (chạy sensor fallback)
                final_alert = True
                print(f"  {RED}{BOLD}⚠️ [CẢNH BÁO CẢM BIẾN - KHÔNG CÓ CAMERA]{RESET} XGBoost phát hiện cháy!")

        # --- BƯỚC 3: XÂY DỰNG GÓI TIN ĐIỀU KHIỂN CÒI GỬI VỀ ESP32 QUA TOPIC iot/test/response ---
        buzzer_val = 1 if final_alert else 0
        cmd_val = "BUZZER_ON" if final_alert else "BUZZER_OFF"

        if final_alert:
            system_status = "FIRE_CONFIRMED"
        elif pred_class == "fire" and not visual_verified:
            system_status = "FALSE_ALARM_SUPPRESSED"
        elif pred_class == "residual_smoke":
            system_status = "RESIDUAL_SMOKE"
        else:
            system_status = "NORMAL"

        response_payload = {
            "buzzer": buzzer_val,
            "alarm": buzzer_val,
            "cmd": cmd_val,
            "status": system_status,
            "is_fire": final_alert,
            "xgb_prediction": pred_class,
            "visual_verified": visual_verified,
            "confidence": round(conf, 4),
            "evidence_image": saved_img,
            "scanned_frames": scanned_frames,
            "pm25": raw_dict["PM2_5_ug_m3"],
            "tvoc": raw_dict["TVOC_ppb"],
            "temp": raw_dict["Temperature_C"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        json_payload = json.dumps(response_payload)
        c.publish(args.res_topic, json_payload)

        if final_alert:
            print(f"  {RED}{BOLD}🔔 [MQTT -> {args.res_topic}] ĐÃ GỬI LỆNH BẬT CÒI TỚI ESP32! [buzzer=1, cmd=BUZZER_ON]{RESET}")
        elif pred_class == "fire" and not visual_verified:
            print(f"  {GREEN}{BOLD}🔔 [MQTT -> {args.res_topic}] Gửi lệnh giữ còi TẮT do hủy báo động giả [buzzer=0]{RESET}")

        print("-" * 88)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(args.broker, args.port, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nĐã ngắt kết nối.")
    except Exception as e:
        print(f"{RED}[LỖI]{RESET} {e}")

if __name__ == "__main__":
    main()
