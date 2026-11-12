"""
app.py
=============================================================================
AIoT Fire Sentinel - Tabler Web Dashboard Server
- Backend: FastAPI + WebSockets + Paho-MQTT
- Frontend: Tabler UI (Dark/Light mode, ApexCharts, Evidence Gallery)
- Khả năng chạy:
  + Trực tiếp trên Windows: python app.py --broker 10.156.225.221
  + Hoặc trên Raspberry Pi 5 (Direct hoặc Docker container)
=============================================================================
"""

import os
import sys
import json
import time
import base64
import asyncio
from datetime import datetime
from collections import deque
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import paho.mqtt.client as mqtt
import uvicorn

# =============================================================================
# 1. CẤU HÌNH HỆ THỐNG
# =============================================================================
MQTT_BROKER = os.getenv("MQTT_BROKER", "10.156.225.221")  # Mặc định IP Pi 5 nếu chạy từ PC
# =============================================================================
# 1. CẤU HÌNH HỆ THỐNG VÀ ĐƯỜNG DẪN BẰNG CHỨNG
# =============================================================================
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
REQ_TOPIC = os.getenv("REQ_TOPIC", "iot/test/request")
RES_TOPIC = os.getenv("RES_TOPIC", "iot/test/response")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 5000))

BASE_DIR = Path(__file__).resolve().parent

def get_candidate_evidence_dirs() -> List[Path]:
    """Tìm tất cả các thư mục có khả năng chứa ảnh bằng chứng trên Pi 5 và PC"""
    candidates = [
        Path("/home/khoapi5/yolo/pi5_deploy/evidence"),
        BASE_DIR.parent / "pi5_deploy" / "evidence",
        BASE_DIR.parent / "evidence",
        BASE_DIR / "evidence",
        Path.cwd() / "pi5_deploy" / "evidence",
        Path.cwd() / "evidence",
        Path.cwd().parent / "pi5_deploy" / "evidence",
        Path("/home/khoapi5/yolo/evidence"),
        Path("/home/khoapi5/yolo/dashboard/evidence"),
        Path("C:/Users/OS/Desktop/IOT/pi5_deploy/evidence"),
        Path("C:/Users/OS/Desktop/IOT/evidence"),
        Path("C:/Users/OS/Desktop/IOT/dashboard/evidence"),
    ]
    valid_dirs = []
    seen = set()
    for d in candidates:
        try:
            r = d.resolve()
            if r not in seen:
                seen.add(r)
                if r.exists() and r.is_dir():
                    valid_dirs.append(r)
        except Exception:
            pass
    # Nếu chưa có thư mục nào tồn tại, tạo thư mục mặc định
    if not valid_dirs:
        default_dir = BASE_DIR.parent / "pi5_deploy" / "evidence" if (BASE_DIR.parent / "pi5_deploy").exists() else BASE_DIR / "evidence"
        default_dir.mkdir(parents=True, exist_ok=True)
        valid_dirs.append(default_dir.resolve())
    return valid_dirs

EVIDENCE_DIR = get_candidate_evidence_dirs()[0]
print(f"[Dashboard] Thư mục ảnh bằng chứng ưu tiên: {EVIDENCE_DIR}")
print(f"[Dashboard] Toàn bộ thư mục ảnh được quét: {[str(d) for d in get_candidate_evidence_dirs()]}")

# Bộ nhớ đệm dữ liệu thời gian thực
MAX_HISTORY = 40
telemetry_history: deque = deque(maxlen=MAX_HISTORY)
latest_alarm_state: Dict[str, Any] = {
    "status": "NORMAL",
    "buzzer": 0,
    "cmd": "BUZZER_OFF",
    "is_fire": False,
    "visual_verified": False,
    "confidence": 0.0,
    "evidence_image": None,
    "timestamp": None,
    "last_updated": None
}

# =============================================================================
# 2. KHỞI TẠO FASTAPI VÀ QUẢN LÝ WEBSOCKET
# =============================================================================
app = FastAPI(title="AIoT Fire Sentinel Dashboard")

# Cấu hình templates và static
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/evidence/{filename}")
async def serve_evidence_image(filename: str):
    """Phục vụ ảnh bằng chứng từ bất kỳ thư mục candidate nào có ảnh này"""
    for d in get_candidate_evidence_dirs():
        img_path = d / filename
        if img_path.exists() and img_path.is_file():
            return FileResponse(
                path=str(img_path),
                media_type="image/jpeg",
                headers={"Cache-Control": "no-cache, must-revalidate"}
            )
    raise HTTPException(status_code=404, detail=f"Image {filename} not found")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
loop: asyncio.AbstractEventLoop = None

# =============================================================================
# 3. GIẢI MÃ PAYLOAD TỪ SENSOR ESP32
# =============================================================================
def parse_sensor_payload(payload_str: str) -> Dict[str, float]:
    try:
        data = json.loads(payload_str)
        mapping = {
            "PM1_0": ["PM1_0_ug_m3", "pm1_0", "pm1", "PM1_0"],
            "PM2_5": ["PM2_5_ug_m3", "pm2_5", "pm25", "PM2_5"],
            "PM10": ["PM10_ug_m3", "pm10", "PM10"],
            "NC0_3": ["NC0_3_per_0.1L", "nc0_3", "nc03", "NC0_3"],
            "NC0_5": ["NC0_5_per_0.1L", "nc0_5", "nc05", "NC0_5"],
            "TVOC": ["TVOC_ppb", "tvoc", "tvoc_ppb", "TVOC"],
            "eCO2": ["eCO2_ppm", "eco2", "eco2_ppm", "eCO2"],
            "Temperature": ["Temperature_C", "temperature", "temp", "temp_c"],
            "Humidity": ["Humidity_percent", "humidity", "hum"]
        }
        res = {}
        for std_k, alt_keys in mapping.items():
            for alt in alt_keys:
                if alt in data:
                    res[std_k] = float(data[alt])
                    break
        if "PM2_5" in res and "TVOC" in res:
            return res
    except Exception:
        pass
    return None

# =============================================================================
# 4. MQTT CLIENT BACKGROUND WORKER
# =============================================================================
def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[Dashboard MQTT] Đã kết nối thành công Broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe([(REQ_TOPIC, 0), (RES_TOPIC, 0)])
        print(f"[Dashboard MQTT] Đang lắng nghe: '{REQ_TOPIC}' và '{RES_TOPIC}'")
    else:
        print(f"[Dashboard MQTT] Kết nối thất bại (rc={rc})")

def on_mqtt_message(client, userdata, msg):
    global latest_alarm_state, loop
    try:
        payload_str = msg.payload.decode("utf-8", errors="ignore")
        topic = msg.topic

        now_time = datetime.now().strftime("%H:%M:%S")

        if topic == REQ_TOPIC:
            sensor_data = parse_sensor_payload(payload_str)
            if sensor_data:
                sensor_data["time"] = now_time
                telemetry_history.append(sensor_data)

                packet = {
                    "type": "telemetry",
                    "data": sensor_data,
                    "history_len": len(telemetry_history)
                }
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(manager.broadcast(packet), loop)

        elif topic == RES_TOPIC:
            try:
                res_data = json.loads(payload_str)

                # Tự động lưu ảnh chụp từ Pi 5 về Dashboard PC nếu có base64
                if res_data.get("image_base64") and res_data.get("evidence_image"):
                    try:
                        img_bytes = base64.b64decode(res_data["image_base64"])
                        img_path = EVIDENCE_DIR / res_data["evidence_image"]
                        with open(img_path, "wb") as f:
                            f.write(img_bytes)
                        print(f"📸 [Dashboard Sync] Đã nhận và lưu ảnh từ Pi 5: {res_data['evidence_image']}")
                    except Exception as err:
                        print(f"⚠️ [Lỗi lưu ảnh Base64] {err}")

                latest_alarm_state.update(res_data)
                latest_alarm_state["last_updated"] = now_time

                packet = {
                    "type": "alarm",
                    "data": latest_alarm_state
                }
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(manager.broadcast(packet), loop)
            except Exception as e:
                print(f"[Lỗi parse response JSON] {e}")

    except Exception as e:
        print(f"[Lỗi xử lý MQTT] {e}")

mqtt_client_instance = None

def start_mqtt_client():
    global mqtt_client_instance
    mqtt_client_instance = mqtt.Client()
    mqtt_client_instance.on_connect = on_mqtt_connect
    mqtt_client_instance.on_message = on_mqtt_message
    try:
        mqtt_client_instance.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client_instance.loop_start()
        print(f"[Dashboard MQTT] Khởi động background loop tới {MQTT_BROKER}...")
    except Exception as e:
        print(f"[Dashboard MQTT Cảnh báo] Không thể kết nối ngay tới Broker {MQTT_BROKER}: {e}")
    return mqtt_client_instance

# =============================================================================
# 5. REST APIS & WEBSOCKET ROUTE
# =============================================================================
@app.on_event("startup")
async def startup_event():
    global loop
    loop = asyncio.get_running_loop()
    start_mqtt_client()

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "broker": MQTT_BROKER,
            "req_topic": REQ_TOPIC,
            "res_topic": RES_TOPIC,
            "evidence_dir": str(EVIDENCE_DIR.resolve())
        }
    )

@app.post("/api/reset_alarm")
async def reset_alarm():
    """Reset trạng thái báo động và gửi lệnh tắt còi (BUZZER_OFF) tới ESP32 qua MQTT"""
    global latest_alarm_state
    now_time = datetime.now().strftime("%H:%M:%S")
    latest_alarm_state.update({
        "status": "NORMAL",
        "buzzer": 0,
        "alarm": 0,
        "cmd": "BUZZER_OFF",
        "is_fire": False,
        "visual_verified": False,
        "confidence": 0.0,
        "last_updated": now_time,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    # Publish về MQTT topic response để ESP32 tắt còi thật
    if mqtt_client_instance:
        try:
            mqtt_client_instance.publish(RES_TOPIC, json.dumps(latest_alarm_state))
            print(f"[Dashboard Reset] Đã gửi lệnh TẮT CÒI (BUZZER_OFF) tới {RES_TOPIC}")
        except Exception as e:
            print(f"[Dashboard Reset Lỗi] {e}")

    # Broadcast tới tất cả WebSocket client trên giao diện
    await manager.broadcast({
        "type": "alarm",
        "data": latest_alarm_state
    })
    return {"success": True, "message": "Đã reset về AN TOÀN và gửi lệnh tắt còi"}

@app.get("/api/status")
async def get_status():
    latest_sensor = telemetry_history[-1] if len(telemetry_history) > 0 else {}
    return {
        "alarm": latest_alarm_state,
        "latest_sensor": latest_sensor,
        "history_count": len(telemetry_history),
        "evidence_dir": str(EVIDENCE_DIR.resolve())
    }

@app.get("/api/history")
async def get_history():
    return list(telemetry_history)

@app.get("/api/evidence")
async def list_evidence():
    """Liệt kê toàn bộ các ảnh chụp bằng chứng cháy theo thời gian mới nhất trước từ TẤT CẢ các thư mục"""
    images_dict = {}
    for d in get_candidate_evidence_dirs():
        if d.exists() and d.is_dir():
            for file in list(d.glob("*.jpg")) + list(d.glob("*.png")):
                if file.name not in images_dict:
                    try:
                        stat = file.stat()
                        dt_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        is_flame = "flame" in file.name.lower() or "fire" in file.name.lower()
                        images_dict[file.name] = {
                            "filename": file.name,
                            "url": f"/evidence/{file.name}",
                            "timestamp": dt_str,
                            "mtime": stat.st_mtime,
                            "size_kb": round(stat.st_size / 1024, 1),
                            "is_flame": is_flame,
                            "dir": str(d)
                        }
                    except Exception:
                        pass
    sorted_images = sorted(images_dict.values(), key=lambda x: x["mtime"], reverse=True)
    return {"count": len(sorted_images), "images": sorted_images}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Gửi ngay trạng thái ban đầu và lịch sử khi client vừa kết nối
        await websocket.send_json({
            "type": "init",
            "alarm": latest_alarm_state,
            "history": list(telemetry_history)
        })
        while True:
            # Lắng nghe ping từ client để giữ kết nối
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# =============================================================================
# 6. KHỞI CHẠY TRỰC TIẾP
# =============================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AIoT Fire Sentinel Tabler Dashboard")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Địa chỉ bind web server")
    parser.add_argument("--port", type=int, default=DASHBOARD_PORT, help="Cổng web server (mặc định: 5000)")
    parser.add_argument("--broker", type=str, default=MQTT_BROKER, help="Địa chỉ MQTT Broker")
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT, help="Cổng MQTT Broker")

    cli_args = parser.parse_args()
    MQTT_BROKER = cli_args.broker
    MQTT_PORT = cli_args.mqtt_port

    print("=" * 80)
    print(f"🚀 AIoT Fire Sentinel Dashboard đang khởi động...")
    print(f"🌐 Web UI: http://localhost:{cli_args.port} hoặc http://<IP-may-tinh>:{cli_args.port}")
    print(f"📡 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"📸 Thư mục ảnh bằng chứng: {EVIDENCE_DIR.resolve()}")
    print("=" * 80)

    uvicorn.run(app, host=cli_args.host, port=cli_args.port)
