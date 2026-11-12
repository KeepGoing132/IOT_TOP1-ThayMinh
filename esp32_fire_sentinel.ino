#include <Wire.h>
#include <Adafruit_SGP30.h>
#include <DHT.h>
#include <WiFi.h>
#include <PubSubClient.h>

// ==================== PIN CONFIG ====================

// SGP30 I2C
#define I2C_SDA 21
#define I2C_SCL 22

// DHT11
#define DHT_PIN 4
#define DHT_TYPE DHT11

// PMS5003 UART2
#define PMS_RX 16
#define PMS_TX 17

// Buzzer PWM (GPIO 27)
#define BUZZER_PIN 27

// ==================== WIFI CONFIG ====================

const char* ssid = "ruby-chan";
const char* password = "stayu0603";

// ==================== MQTT CONFIG ====================

// Raspberry Pi broker
const char* mqtt_server = "10.156.225.221";
const int mqtt_port = 1883;

// Topic gửi dữ liệu cảm biến
const char* MQTT_TOPIC_REQUEST = "iot/test/request";

// Topic nhận kết quả AI & lệnh còi từ Raspberry Pi 5
const char* MQTT_TOPIC_RESPONSE = "iot/test/response";

WiFiClient espClient;
PubSubClient client(espClient);

// ==================== SENSOR OBJECTS ====================

Adafruit_SGP30 sgp;
DHT dht(DHT_PIN, DHT_TYPE);

HardwareSerial pmsSerial(2);

// ==================== BUZZER STATE ====================

bool isBuzzerActive = false;
unsigned long lastBuzzerToggle = 0;
bool buzzerBeepState = false;

// ==================== PMS DATA ====================

uint8_t pmsFrame[32];
int pmsIndex = 0;

uint16_t latestPM1 = 0;
uint16_t latestPM25 = 0;
uint16_t latestPM10 = 0;

uint16_t latestNC03 = 0;
uint16_t latestNC05 = 0;
uint16_t latestNC10 = 0;
uint16_t latestNC25 = 0;
uint16_t latestNC50 = 0;
uint16_t latestNC100 = 0;

bool pmsDataAvailable = false;

// ==================== SGP30 DATA ====================

uint16_t latestECO2 = 0;
uint16_t latestTVOC = 0;

// ==================== TIMERS ====================

unsigned long lastOutputTime = 0;
unsigned long lastSGPTime = 0;

const unsigned long OUTPUT_INTERVAL = 3000;
const unsigned long SGP_INTERVAL = 1000;
unsigned long lastMqttAttempt = 0;

const unsigned long MQTT_RETRY_INTERVAL = 5000;

// ==================== PMS FUNCTIONS ====================

uint16_t readPMS16(int position) {
  return ((uint16_t)pmsFrame[position] << 8) |
         pmsFrame[position + 1];
}

void readPMS() {
  while (pmsSerial.available()) {
    uint8_t data = pmsSerial.read();

    // Find frame header 0x42 0x4D
    if (pmsIndex == 0 && data != 0x42) {
      continue;
    }

    if (pmsIndex == 1 && data != 0x4D) {
      pmsIndex = 0;
      continue;
    }

    pmsFrame[pmsIndex++] = data;

    if (pmsIndex == 32) {
      uint16_t frameLength = readPMS16(2);
      uint16_t checksum = 0;

      for (int i = 0; i < 30; i++) {
        checksum += pmsFrame[i];
      }

      uint16_t receivedChecksum = readPMS16(30);

      if (frameLength == 28 && checksum == receivedChecksum) {
        // Atmospheric environment PM concentrations
        latestPM1 = readPMS16(10);
        latestPM25 = readPMS16(12);
        latestPM10 = readPMS16(14);

        // Particle number concentrations
        latestNC03 = readPMS16(16);
        latestNC05 = readPMS16(18);
        latestNC10 = readPMS16(20);
        latestNC25 = readPMS16(22);
        latestNC50 = readPMS16(24);
        latestNC100 = readPMS16(26);

        pmsDataAvailable = true;
      }

      pmsIndex = 0;
    }
  }
}

// ==================== WIFI ====================

void setup_wifi() {
  Serial.print("Connecting WiFi");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

// ==================== MQTT CALLBACK (NHẬN LỆNH BẬT/TẮT CÒI) ====================

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Chuyển payload byte sang String
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("[MQTT Callback] Nhận từ topic: ");
  Serial.println(topic);
  Serial.print("Payload: ");
  Serial.println(message);

  // Kiểm tra nếu đúng topic response
  if (strcmp(topic, MQTT_TOPIC_RESPONSE) == 0) {
    // 1. Kiểm tra cờ BẬT CÒI
    if (message.indexOf("\"buzzer\": 1") >= 0 || 
        message.indexOf("\"buzzer\":1") >= 0 ||
        message.indexOf("BUZZER_ON") >= 0 ||
        message.indexOf("FIRE_CONFIRMED") >= 0) {
      
      isBuzzerActive = true;
      Serial.println("🚨🚨 [BÁO ĐỘNG ĐỎ] KÍCH HOẠT CÒI HÚ GPIO27!");
    }
    // 2. Kiểm tra cờ TẮT CÒI (Bình thường hoặc Reset từ Dashboard)
    else if (message.indexOf("\"buzzer\": 0") >= 0 || 
             message.indexOf("\"buzzer\":0") >= 0 ||
             message.indexOf("BUZZER_OFF") >= 0 ||
             message.indexOf("NORMAL") >= 0 ||
             message.indexOf("FALSE_ALARM_SUPPRESSED") >= 0) {
      
      isBuzzerActive = false;
      ledcWriteTone(BUZZER_PIN, 0); // Ngắt âm ngay lập tức
      Serial.println("🟢 [AN TOÀN / ĐÃ RESET] ĐÃ TẮT CÒI BÁO ĐỘNG.");
    }
  }
}

// ==================== MQTT RECONNECT ====================

void reconnect_mqtt() {
  unsigned long now = millis();

  // Chỉ thử kết nối lại sau mỗi 5 giây
  if (now - lastMqttAttempt < MQTT_RETRY_INTERVAL) {
    return;
  }

  lastMqttAttempt = now;

  Serial.print("Connecting MQTT...");

  String clientId = "ESP32_Sensor_";
  clientId += String((uint32_t)ESP.getEfuseMac(), HEX);

  if (client.connect(clientId.c_str())) {
    Serial.println("connected!");
    
    // Subscribe topic response để nhận lệnh điều khiển còi
    client.subscribe(MQTT_TOPIC_RESPONSE);
    Serial.print("Subscribed to: ");
    Serial.println(MQTT_TOPIC_RESPONSE);
  } else {
    Serial.print("failed, rc=");
    Serial.println(client.state());
    Serial.println("Retry in 5 seconds");
  }
}

// ==================== SEND SENSOR DATA ====================

void publishSensorData(
  unsigned long elapsed,
  float temperature,
  float humidity
) {
  char payload[400];

  char temperatureStr[16];
  char humidityStr[16];

  if (isnan(temperature)) {
    strcpy(temperatureStr, "null");
  } else {
    snprintf(temperatureStr, sizeof(temperatureStr), "%.1f", temperature);
  }

  if (isnan(humidity)) {
    strcpy(humidityStr, "null");
  } else {
    snprintf(humidityStr, sizeof(humidityStr), "%.1f", humidity);
  }

  snprintf(
    payload,
    sizeof(payload),
    "{"
      "\"elapsed_ms\":%lu,"
      "\"temperature\":%s,"
      "\"humidity\":%s,"
      "\"eCO2\":%u,"
      "\"TVOC\":%u,"
      "\"PM1_0\":%u,"
      "\"PM2_5\":%u,"
      "\"PM10\":%u,"
      "\"NC0_3\":%u,"
      "\"NC0_5\":%u,"
      "\"NC1_0\":%u,"
      "\"NC2_5\":%u,"
      "\"NC5_0\":%u,"
      "\"NC10\":%u"
    "}",
    elapsed,
    temperatureStr,
    humidityStr,
    latestECO2,
    latestTVOC,
    latestPM1,
    latestPM25,
    latestPM10,
    latestNC03,
    latestNC05,
    latestNC10,
    latestNC25,
    latestNC50,
    latestNC100
  );

  if (client.publish(MQTT_TOPIC_REQUEST, payload)) {
    Serial.println("MQTT published:");
    Serial.println(payload);
  } else {
    Serial.println("MQTT publish failed!");
  }
}

// ==================== CÒI BÁO ĐỘNG KHÔNG BLOCK LUỒNG (NON-BLOCKING) ====================

void updateBuzzer() {
  if (!isBuzzerActive) {
    ledcWriteTone(BUZZER_PIN, 0);
    return;
  }

  // Khi đang báo động: hú ngắt quãng (Bíp - Bíp) mỗi 250ms không làm đơ hệ thống
  unsigned long now = millis();
  if (now - lastBuzzerToggle >= 250) {
    lastBuzzerToggle = now;
    buzzerBeepState = !buzzerBeepState;

    if (buzzerBeepState) {
      ledcWriteTone(BUZZER_PIN, 2000); // Tần số báo động 2000 Hz
    } else {
      ledcWriteTone(BUZZER_PIN, 0);    // Tắt tạm thời tạo tiếng bíp
    }
  }
}

// ==================== SETUP ====================

void setup() {
  Serial.begin(115200);

  // 1. Cấu hình còi PWM LEDC trên ESP32 Core 3.x (GPIO 27)
  ledcAttach(BUZZER_PIN, 2000, 8);
  ledcWriteTone(BUZZER_PIN, 0); // Đảm bảo lúc mới bật còi không kêu

  // 2. Initialize I2C
  Wire.begin(I2C_SDA, I2C_SCL);

  // 3. Initialize DHT11
  dht.begin();

  // 4. Initialize PMS5003
  pmsSerial.begin(
    9600,
    SERIAL_8N1,
    PMS_RX,
    PMS_TX
  );

  // 5. Initialize SGP30
  if (!sgp.begin()) {
    Serial.println("ERROR: SGP30 not found");
    while (1) {
      delay(100);
    }
  }

  // 6. Initialize WiFi
  setup_wifi();

  // 7. Initialize MQTT & Callback
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback); // Đăng ký hàm nhận tin
  client.setBufferSize(512);

  Serial.println("Sensor + Buzzer + MQTT system started");
}

// ==================== LOOP ====================

void loop() {
  unsigned long now = millis();

  // 1. Cập nhật âm thanh còi báo động (Không dùng delay để không làm trễ cảm biến)
  updateBuzzer();

  // 2. Đọc PMS5003 liên tục
  readPMS();

  // 3. Đọc SGP30 mỗi 1 giây
  if (now - lastSGPTime >= SGP_INTERVAL) {
    lastSGPTime = now;

    if (sgp.IAQmeasure()) {
      latestECO2 = sgp.eCO2;
      latestTVOC = sgp.TVOC;
    }
  }

  // 4. Đọc DHT11 và publish mỗi 3 giây
  if (now - lastOutputTime >= OUTPUT_INTERVAL) {
    lastOutputTime = now;

    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();

    if (client.connected()) {
      publishSensorData(
        now,
        temperature,
        humidity
      );
    } else {
      Serial.println("MQTT disconnected - skip publish");
    }
  }

  // 5. Thử kết nối lại MQTT nếu mất kết nối
  if (!client.connected()) {
    reconnect_mqtt();
  }

  // 6. Xử lý nhận/gửi MQTT
  client.loop();
}
