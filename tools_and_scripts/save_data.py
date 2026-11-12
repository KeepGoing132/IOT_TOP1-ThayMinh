
import serial
import csv
import os
from datetime import datetime

# ==================== CONFIG ====================

SERIAL_PORT = "COM3"  # Thay bằng COM của ESP32
BAUD_RATE = 115200

CSV_FILE = "sensor_data_1.csv"

# ==================== SERIAL ====================

ser = serial.Serial(
    SERIAL_PORT,
    BAUD_RATE,
    timeout=2
)

# Clear old buffered data
ser.reset_input_buffer()

# ==================== CSV ====================

file_exists = os.path.exists(CSV_FILE)

write_header = (
    not file_exists
    or os.path.getsize(CSV_FILE) == 0
)

with open(
    CSV_FILE,
    "a",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.writer(file)

    if write_header:
        writer.writerow([
            "Timestamp",
            "Elapsed_ms",
            "Temperature_C",
            "Humidity_percent",
            "eCO2_ppm",
            "TVOC_ppb",
            "PM1_0_ug_m3",
            "PM2_5_ug_m3",
            "PM10_ug_m3",
            "NC0_3_per_0.1L",
            "NC0_5_per_0.1L",
            "NC1_0_per_0.1L",
            "NC2_5_per_0.1L",
            "NC5_0_per_0.1L",
            "NC10_per_0.1L"
        ])

    print("Recording to:", CSV_FILE)
    print("Press Ctrl+C to stop.")

    try:
        while True:

            line = ser.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if not line:
                continue

            # Skip CSV header
            if line.startswith("elapsed_ms"):
                continue

            values = line.split(",")

            # Expected 14 values from ESP32
            if len(values) != 14:
                print("Invalid line:", line)
                continue

            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            writer.writerow([
                timestamp
            ] + values)

            # Flush data to disk
            file.flush()

            print(timestamp, line)

    except KeyboardInterrupt:
        print("\nRecording stopped.")

    finally:
        ser.close()
