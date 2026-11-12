# Dockerfile cho AIoT Fire Sentinel Dashboard
# Hỗ trợ đa kiến trúc (ARM64 cho Raspberry Pi 5 và AMD64 cho PC)

FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt các gói phụ trợ tối thiểu
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn ứng dụng
COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/

# Tạo thư mục chứa ảnh bằng chứng
RUN mkdir -p /app/evidence

# Khai báo cổng
EXPOSE 5000

# Biến môi trường mặc định
ENV MQTT_BROKER="localhost"
ENV MQTT_PORT="1883"
ENV REQ_TOPIC="iot/test/request"
ENV RES_TOPIC="iot/test/response"
ENV DASHBOARD_PORT="5000"

# Khởi chạy server FastAPI
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "5000"]
