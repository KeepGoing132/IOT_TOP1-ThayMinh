"""
blynk_notifier.py
=============================================================================
Module gửi cảnh báo và đồng bộ trạng thái báo cháy lên Blynk IoT qua REST API
- Tự động nạp BLYNK_AUTH_TOKEN từ file .env
- Không phụ thuộc vào thư viện ngoài (sử dụng urllib có sẵn của Python)
- Hỗ trợ:
  1. Cập nhật Datastream Virtual Pins (V0: Đèn/Trạng thái, V1: Text label, V2: PM2.5)
  2. Bắn thông báo đẩy Push Notification về Smartphone qua Blynk Events
  3. Chạy độc lập qua CLI để test: python blynk_notifier.py --test-fire
=============================================================================
"""

import os
import sys
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

# Mã màu ANSI hiển thị terminal
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def load_env(env_path=None):
    """
    Tự động tìm và nạp các biến môi trường từ file .env
    (Hỗ trợ nạp mà không cần cài thư viện python-dotenv)
    """
    if env_path is None:
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).resolve().parent / ".env",
            Path(__file__).resolve().parent.parent / ".env"
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                env_path = c
                break

    if env_path and Path(env_path).exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            print(f"[Warning] Không thể nạp file .env từ {env_path}: {e}")


# Tự động nạp file .env khi import module
load_env()


class BlynkNotifier:
    def __init__(self, token=None, server=None, event_code=None):
        # Ưu tiên tham số truyền vào, nếu không thì lấy từ .env
        self.token = token or os.getenv("BLYNK_AUTH_TOKEN", "").strip()
        self.server = server or os.getenv("BLYNK_SERVER", "blynk.cloud").strip()
        self.event_code = event_code or os.getenv("BLYNK_EVENT_CODE", "fire_alert").strip()

        self.pin_status = os.getenv("BLYNK_PIN_STATUS", "v0").strip().lower()
        self.pin_label = os.getenv("BLYNK_PIN_LABEL", "").strip().lower()
        self.pin_pm25 = os.getenv("BLYNK_PIN_PM25", "").strip().lower()

        self.base_url = f"https://{self.server}/external/api"

    def is_configured(self) -> bool:
        """Kiểm tra xem Auth Token đã được cấu hình hợp lệ chưa"""
        return bool(self.token and self.token != "your_blynk_auth_token_here")

    def _http_get(self, endpoint: str, params: dict, timeout: float = 4.0):
        """Hàm phụ trợ gửi HTTP GET request với urllib"""
        if not self.is_configured():
            print(f"{YELLOW}[Blynk Skip]{RESET} BLYNK_AUTH_TOKEN chưa được cấu hình trong file .env")
            return False, "Token not configured"

        params["token"] = self.token
        query_str = urllib.parse.urlencode(params)
        full_url = f"{self.base_url}/{endpoint}?{query_str}"

        try:
            req = urllib.request.Request(
                full_url,
                headers={"User-Agent": "AIoT-Fire-Sentinel-Pi5/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.getcode()
                body = response.read().decode("utf-8", errors="ignore")
                return True, body
        except urllib.error.HTTPError as e:
            return False, f"HTTP Error {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            return False, f"URL Error: {e.reason}"
        except Exception as e:
            return False, str(e)

    def update_pin(self, pin: str, value):
        """
        Cập nhật giá trị vào 1 Virtual Pin (Datastream)
        Ví dụ: update_pin("v0", 1) hoặc update_pin("v1", "CHÁY ĐÃ XÁC THỰC")
        """
        pin = pin.lower()
        params = {pin: str(value)}
        ok, res = self._http_get("update", params)
        if ok:
            print(f"📱 {GREEN}[Blynk Pin]{RESET} Đã cập nhật chân {pin.upper()} = {value}")
        else:
            print(f"⚠️ {RED}[Blynk Pin Lỗi]{RESET} Không thể cập nhật chân {pin.upper()}: {res}")
        return ok

    def log_event(self, event_code: str = None, description: str = None):
        """
        Kích hoạt một Event trên Blynk Cloud
        -> Blynk sẽ gửi Push Notification rung chuông về điện thoại người dùng
        """
        code = event_code or self.event_code
        params = {"code": code}
        if description:
            params["description"] = description

        ok, res = self._http_get("logEvent", params)
        if ok:
            print(f"🚨 {RED}{BOLD}[Blynk Push Notification]{RESET} Đã bắn sự kiện khẩn cấp '{code}' về điện thoại thành công!")
        else:
            print(f"⚠️ {YELLOW}[Blynk Event Lỗi]{RESET} Không thể gửi sự kiện '{code}': {res}")
        return ok

    def send_fire_alert(self, status: str, is_fire: bool, pm25: float = None, note: str = None):
        """
        Hàm tích hợp hoàn chỉnh dành cho hệ thống báo cháy:
        - status: 'FIRE_CONFIRMED', 'FALSE_ALARM_SUPPRESSED', 'NORMAL', ...
        - is_fire: True nếu có cháy thật, False nếu an toàn / hủy báo động
        - pm25: Nồng độ khói PM2.5 hiện tại
        """
        now_str = datetime.now().strftime("%H:%M:%S")

        if is_fire or status == "FIRE_CONFIRMED":
            # 1. Trạng thái CHÁY THỰC SỰ
            label_text = f"🔥 CHÁY ĐÃ XÁC THỰC! ({now_str})"
            self.update_pin(self.pin_status, 1)
            if self.pin_label:
                self.update_pin(self.pin_label, label_text)

            desc = f"Phát hiện ngọn lửa xác thực bởi YOLO NCNN lúc {now_str}."
            if pm25 is not None:
                desc += f" PM2.5: {pm25:.0f} ug/m3."
            if note:
                desc += f" {note}"

            self.log_event(self.event_code, description=desc)

        elif status == "FALSE_ALARM_SUPPRESSED":
            # 2. HỦY BÁO ĐỘNG GIẢ (Không có lửa)
            label_text = f"🛡️ HỦY BÁO ĐỘNG GIẢ ({now_str})"
            self.update_pin(self.pin_status, 0)
            if self.pin_label:
                self.update_pin(self.pin_label, label_text)

        else:
            # 3. AN TOÀN BÌNH THƯỜNG
            label_text = f"✅ AN TOÀN ({now_str})"
            self.update_pin(self.pin_status, 0)
            if self.pin_label:
                self.update_pin(self.pin_label, label_text)

        # Cập nhật PM2.5 nếu có cấu hình chân pin_pm25
        if self.pin_pm25 and pm25 is not None:
            self.update_pin(self.pin_pm25, round(pm25, 1))

    def send_simple_message(self, message: str, is_alert: bool = False):
        """Gửi nhanh một thông điệp text lên Blynk"""
        self.update_pin(self.pin_label, message)
        if is_alert:
            self.update_pin(self.pin_status, 1)
            self.log_event(self.event_code, description=message)
        else:
            self.update_pin(self.pin_status, 0)


# =============================================================================
# CLI DÙNG ĐỂ TEST ĐỘC LẬP TỪ DÒNG LỆNH
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Công cụ gửi thông báo Blynk IoT cho Hệ thống Báo Cháy")
    parser.add_argument("--test-fire", action="store_true", help="Gửi thử nghiệm trạng thái BÁO CHÁY KHẨN CẤP")
    parser.add_argument("--test-safe", action="store_true", help="Gửi thử nghiệm trạng thái AN TOÀN")
    parser.add_argument("--test-false", action="store_true", help="Gửi thử nghiệm trạng thái HỦY BÁO ĐỘNG GIẢ")
    parser.add_argument("--msg", type=str, help="Gửi tin nhắn tùy chỉnh lên chân V1")
    parser.add_argument("--pin", type=str, default="v0", help="Chân ảo muốn cập nhật (mặc định: v0)")
    parser.add_argument("--val", type=str, default="1", help="Giá trị muốn gán cho chân ảo")
    parser.add_argument("--event", type=str, help="Gửi thử nghiệm 1 Event code cụ thể")
    parser.add_argument("--token", type=str, help="Ghi đè BLYNK_AUTH_TOKEN nếu không dùng .env")

    args = parser.parse_args()

    notifier = BlynkNotifier(token=args.token)

    print("=" * 70)
    print(f"{BOLD}📱 BLYNK IOT NOTIFIER CLIENT{RESET}")
    print(f"📡 Máy chủ:    {notifier.server}")
    print(f"🔑 Auth Token: {notifier.token[:6]}...{notifier.token[-4:] if len(notifier.token) > 10 else notifier.token}")
    print(f"⚙️ Trạng thái:  {'ĐÃ CẤU HÌNH' if notifier.is_configured() else RED + 'CHƯA CẤU HÌNH TOKEN TRONG .env' + RESET}")
    print("=" * 70)

    if not notifier.is_configured():
        print(f"\n{RED}❌ Vui lòng mở file .env và điền mã BLYNK_AUTH_TOKEN của bạn vào!{RESET}")
        print("Ví dụ trong file .env:")
        print("BLYNK_AUTH_TOKEN=9xAbC12345DefGhIjKlMnOpQrStUv\n")
        sys.exit(1)

    if args.test_fire:
        print(f"\n🚀 Đang gửi thử nghiệm {RED}{BOLD}[BÁO ĐỘNG CHÁY]{RESET} lên Blynk...")
        notifier.send_fire_alert(status="FIRE_CONFIRMED", is_fire=True, pm25=620.0, note="[TEST THỬ NGHIỆM]")
        print("👉 Hãy kiểm tra điện thoại xem đã nhận được Push Notification và đèn V0 đã đỏ chưa!")

    elif args.test_safe:
        print(f"\n🚀 Đang gửi thử nghiệm {GREEN}{BOLD}[AN TOÀN]{RESET} lên Blynk...")
        notifier.send_fire_alert(status="NORMAL", is_fire=False, pm25=25.0)

    elif args.test_false:
        print(f"\n🚀 Đang gửi thử nghiệm {YELLOW}{BOLD}[HỦY BÁO ĐỘNG GIẢ]{RESET} lên Blynk...")
        notifier.send_fire_alert(status="FALSE_ALARM_SUPPRESSED", is_fire=False, pm25=120.0)

    elif args.msg:
        print(f"\n🚀 Đang gửi tin nhắn '{args.msg}' lên Blynk...")
        notifier.send_simple_message(args.msg, is_alert=False)

    elif args.event:
        print(f"\n🚀 Đang kích hoạt event '{args.event}'...")
        notifier.log_event(args.event, description="Test event từ CLI")

    else:
        print(f"\n🚀 Cập nhật chân {args.pin.upper()} = {args.val}...")
        notifier.update_pin(args.pin, args.val)


if __name__ == "__main__":
    main()
