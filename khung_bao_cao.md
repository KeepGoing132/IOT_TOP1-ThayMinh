# BÁO CÁO TIỂU LUẬN MÔN HỌC (LẤY ĐIỂM THI HẾT MÔN)

---

## ĐỀ TÀI:
**ỨNG DỤNG GIẢI THUẬT DI TRUYỀN (GENETIC ALGORITHM) TRONG TỐI ƯU HÓA MÔ HÌNH THỊ GIÁC MÁY TÍNH VÀ XÂY DỰNG HỆ THỐNG AIoT BÁO CHÁY THÔNG MINH 2 TẦNG**

- **Học phần:** Trí tuệ nhân tạo nâng cao / Tối ưu hóa và Giải thuật tiến hóa
- **Chương lý thuyết áp dụng:** Ứng dụng Giải thuật di truyền (Genetic Algorithms - GA)
- **Độ dài quy định:** 30 – 40 trang nội dung (không tính trang bìa, mục lục và phụ lục)
- **Cấu trúc bắt buộc:** Đúng **02 Chương** theo quy chuẩn:
  - **Chương 1:** Cơ sở lý thuyết
  - **Chương 2:** Thực nghiệm và kết quả (kết hợp trình bày sản phẩm phần cứng)

---

## MA TRẬN PHÂN BỔ SỐ TRANG DỰ KIẾN (TỔNG: 35 – 40 TRANG)

| Phần | Nội dung chính | Dự kiến số trang |
| :--- | :--- | :---: |
| **Mở đầu** | Tính cấp thiết, mục tiêu nghiên cứu, đối tượng, phương pháp và đóng góp của đề tài | **2 – 3 trang** |
| **CHƯƠNG 1** | **CƠ SỞ LÝ THUYẾT** (Giải thuật di truyền, Tối ưu hóa siêu tham số, Mô hình YOLO, AIoT 2 tầng) | **14 – 16 trang** |
| **CHƯƠNG 2** | **THỰC NGHIỆM VÀ KẾT QUẢ** (Phần cứng ESP32 & Pi 5, Tiến hóa GA thực nghiệm, Triển khai pipeline, Web & Blynk, Đánh giá) | **17 – 20 trang** |
| **Kết luận** | Tóm tắt kết quả đạt được, hạn chế và hướng phát triển | **2 – 3 trang** |
| **Tổng cộng** | *(Đảm bảo chuẩn quy định 30 – 40 trang nội dung)* | **35 – 42 trang** |

---

# MỤC LỤC CHI TIẾT CỦA BÁO CÁO

---

## LỜI MỞ ĐẦU (2 – 3 trang)
1. **Lý do chọn đề tài:** Sự nguy hiểm của hỏa hoạn và bài toán nhức nhối của các hệ thống báo cháy hiện nay (tỷ lệ báo động giả cực cao do bụi, bình xịt aerosol, khói nấu nướng).
2. **Vai trò của Giải thuật di truyền (GA):** Sự bùng nổ của thị giác máy tính đòi hỏi mô hình phải có độ chính xác cao nhưng độ trễ siêu thấp để chạy được trên phần cứng biên (Edge AI). Việc dùng GA để tự động tìm kiếm bộ siêu tham số tối ưu (Hyperparameter Evolution) mang lại hiệu quả vượt trội so với tìm kiếm thủ công.
3. **Mục tiêu nghiên cứu và sản phẩm bàn giao:**
   - Xây dựng giải thuật tiến hóa GA tối ưu hóa siêu tham số cho mạng nơ-ron YOLO nhận diện ngọn lửa.
   - Chế tạo sản phẩm phần cứng AIoT hoàn chỉnh kết hợp vi điều khiển ESP32, cụm cảm biến và máy tính nhúng Raspberry Pi 5.
   - Xây dựng Web Dashboard trung tâm và đồng bộ cảnh báo đẩy về điện thoại qua Blynk IoT.

---

# CHƯƠNG 1: CƠ SỞ LÝ THUYẾT (14 – 16 trang)

### 1.1. TỔNG QUAN VỀ GIẢI THUẬT DI TRUYỀN (GENETIC ALGORITHM - GA) *(4 – 5 trang)*
* **1.1.1. Nguồn gốc sinh học và Tư tưởng cốt lõi của GA:**
  - Thuyết tiến hóa tự nhiên của Charles Darwin (Đấu tranh sinh tồn, chọn lọc tự nhiên và sự sống sót của cá thể thích nghi nhất - *Survival of the Fittest*).
  - Không gian tìm kiếm lời giải (Search Space) và bài toán tối ưu hóa đa biến, phi tuyến tính.
* **1.1.2. Cấu trúc và Các thành phần cơ bản của một giải thuật di truyền:**
  - **Mã hóa nhiễm sắc thể (Chromosome / Representation):**
    - Mã hóa nhị phân (Binary Encoding).
    - Mã hóa số thực (Real-valued / Floating-point Encoding) - cơ chế biểu diễn các siêu tham số học máy liên tục.
  - **Quần thể khởi tạo (Initial Population):** Kích thước quần thể ($N$), phân bố đa dạng ban đầu.
  - **Hàm thích nghi (Fitness Function):** Tiêu chuẩn định lượng để đo lường mức độ ưu tú của cá thể trong quần thể.
  - **Toán tử Chọn lọc tự nhiên (Selection Operator):**
    - Phương pháp vòng quay Roulette (Roulette Wheel Selection).
    - Phương pháp chọn lọc giải đấu (Tournament Selection).
    - Xếp hạng thích nghi (Rank Selection).
  - **Toán tử Lai ghép (Crossover Operator):**
    - Lai ghép một điểm cắt, đa điểm cắt.
    - Lai ghép số thực (Blend Crossover - BLX-$\alpha$, Simulated Binary Crossover - SBX).
    - Xác suất lai ghép ($P_c$).
  - **Toán tử Đột biến (Mutation Operator):**
    - Đột biến đảo bit, đột biến ngẫu nhiên đồng đều (Uniform Mutation).
    - Đột biến phân phối chuẩn Gaussian (Gaussian Mutation) dùng trong hiệu chỉnh tinh chỉnh siêu tham số liên tục.
    - Xác suất đột biến ($P_m$).
  - **Cơ chế giữ lại cá thể ưu tú (Elitism Strategy):** Bảo toàn nghiệm tốt nhất qua các thế hệ.
  - **Điều kiện dừng giải thuật:** Đạt số thế hệ tối đa, hàm thích nghi hội tụ.
* **1.1.3. Lưu đồ thuật toán tổng quát của Giải thuật di truyền (Flowchart GA).**

---

### 1.2. ỨNG DỤNG GIẢI THUẬT DI TRUYỀN TRONG TỐI ƯU HÓA SIÊU THAM SỐ HỌC SÂU (HYPERPARAMETER EVOLUTION) *(4 – 5 trang)*
* **1.2.1. Khái niệm Siêu tham số (Hyperparameters) trong Mạng Nơ-ron:**
  - Phân biệt giữa Tham số mô hình (Weights, Biases - học qua Gradient Descent) và Siêu tham số (Learning rate, Loss weights, Augmentations - cấu hình trước khi huấn luyện).
  - Tác động sống còn của siêu tham số đến khả năng hội tụ và độ chính xác của mạng nơ-ron.
* **1.2.2. So sánh các phương pháp dò tìm Siêu tham số:**
  - Dò tìm dạng lưới (Grid Search): Bùng nổ tổ hợp, chi phí tính toán cực lớn.
  - Dò ngẫu nhiên (Random Search): Thiếu tính kế thừa thông tin từ các thử nghiệm trước.
  - Tối ưu hóa tiến hóa di truyền (Genetic Algorithm Optimization): Khả năng cân bằng xuất sắc giữa Thăm dò (Exploration) vùng không gian mới và Khai thác (Exploitation) các cá thể tiềm năng.
* **1.2.3. Cơ chế Tiến hóa Siêu tham số của họ mô hình YOLO:**
  - **Không gian cá thể gen của YOLO:**
    - Tốc độ học ban đầu (`lr0`), tốc độ học cuối (`lrf`), Momentum, Weight Decay.
    - Trọng số các hàm mất mát: Hộp giới hạn (`box`), Phân loại (`cls`), Điểm đặc trưng (`dfl`).
    - Tham số tăng cường dữ liệu ảnh (Data Augmentation): Độ xoay ảnh (`degrees`), tỷ lệ dịch chuyển (`translate`), hệ số co giãn (`scale`), Mosaic, Mixup.
  - **Thiết lập Hàm Thích nghi Đa mục tiêu (Multi-objective Fitness Function):**
    $$\text{Fitness} = w_1 \cdot \text{mAP}_{50} + w_2 \cdot \text{mAP}_{50-95}$$
    Trong đó $w_1 = 0.1, w_2 = 0.9$ nhằm ưu tiên các mô hình có độ chuẩn xác cao ở ngưỡng IoU ngặt.
  - **Đột biến tiến hóa theo phân phối chuẩn:** Thế hệ con được sinh ra từ các đột biến ngẫu nhiên xung quanh các cá thể cha mẹ ưu tú nhất.

---

### 1.3. CƠ SỞ THỊ GIÁC MÁY TÍNH VÀ TỐI ƯU HÓA BIÊN NCNN *(3 – 4 trang)*
* **1.3.1. Kiến trúc mạng nơ-ron tích chập YOLO (You Only Look Once):**
  - Cơ chế nhận diện đối tượng một giai đoạn (One-stage object detector).
  - Cấu trúc: Cốt mạng (Backbone), Cổ mạng (Neck - FPN/PAN), Đầu phân loại và dự đoán hộp biên (Detection Head).
* **1.3.2. Framework Tăng tốc phần cứng NCNN (Tencent NCNN):**
  - Tại sao mô hình PyTorch (`.pt`) không thể chạy thời gian thực trên Raspberry Pi nếu không tối ưu.
  - Nguyên lý tối ưu hóa tính toán của NCNN: Tối ưu hóa tập lệnh SIMD ARM Neon trên vi xử lý ARM Cortex-A76 của Raspberry Pi 5.
  - Quy trình chuyển đổi mô hình: PyTorch (`.pt`) $\rightarrow$ ONNX $\rightarrow$ NCNN (`.param` và `.bin`).

---

### 1.4. KIẾN TRÚC HỆ THỐNG AIoT BÁO CHÁY 2 TẦNG VÀ GIAO THỨC TRUYỀN THÔNG *(3 – 4 trang)*
* **1.4.1. Phân loại Cấp độ Kiến trúc IoT của Hệ thống (Mô hình 6 Cấp độ IoT Levels):**
  - **Giới thiệu mô hình 6 Cấp độ Triển khai IoT chuẩn quốc tế (Arshdeep Bahga & Vijay Madisetti):**
    - *IoT Level-1:* Đơn node, lưu trữ và xử lý dữ liệu cục bộ, ứng dụng cục bộ (thích hợp cho các bài toán đơn giản, chi phí thấp).
    - *IoT Level-2:* Đơn node, xử lý cục bộ nhưng lưu trữ dữ liệu và ứng dụng trên Đám mây (Cloud).
    - *IoT Level-3:* Đơn node, toàn bộ việc lưu trữ và phân tích dữ liệu chuyên sâu được thực hiện trên Đám mây.
    - *IoT Level-4:* Đa node đầu cuối (Multiple End Nodes), phân tích và lưu trữ tập trung trên Cloud, có các Node quan sát (Observer Nodes).
    - *IoT Level-5 (CẤP ĐỘ CỦA HỆ THỐNG ĐỀ TÀI):* Mô hình Đa Node đầu cuối kết hợp Node điều phối biên (**Coordinator / Edge Node**) và Đám mây (**Cloud**):
      + Các Node đầu cuối (**End Nodes - ESP32**) đảm nhận việc đo đạc cảm biến và kích hoạt cơ cấu chấp hành (còi buzzer).
      + Node điều phối trung tâm (**Coordinator Node - Raspberry Pi 5**) thu thập dữ liệu từ các node con, thực hiện tính toán và phân tích Trí tuệ nhân tạo biên (**Edge AI Analytics: XGBoost + YOLO NCNN**) với độ trễ thấp, đồng thời điều phối quyết định cục bộ và đồng bộ dữ liệu lên Đám mây.
      + Thành phần Đám mây (**Cloud - Blynk IoT**) quản lý dữ liệu sự cố, tài khoản và dịch vụ thông báo đẩy (Push Notification).
      + Các Node quan sát (**Observer Nodes - Web Dashboard & Mobile App**) nhận dữ liệu giám sát và hỗ trợ điều khiển can thiệp từ xa.
    - *IoT Level-6:* Hệ thống phân tán quy mô lớn (Big Data), nhiều cụm Cloud Server và Controller điều phối độc lập.
  - **Đánh giá Cấp độ Trưởng thành Thông minh (IoT Intelligence Maturity):**
    - Hệ thống đạt **Cấp độ 4 (Autonomous & Predictive - Tự hành và Dự báo thông minh)**: Tự động phân tích đa chiều, dự báo nguy cơ cháy và tự đưa ra quyết định xử lý (bật còi, đánh thức camera, tự hủy báo động giả) mà không phụ thuộc vào sự can thiệp thủ công của con người.

* **1.4.2. Khái niệm AIoT (Artificial Intelligence of Things) và Cơ chế Phán quyết 2 tầng:**
  - Tầng 1: Lắng nghe liên tục bằng học máy XGBoost trên chuỗi dữ liệu cảm biến đa chiều (PM2.5, TVOC, eCO2, Nhiệt/Ẩm).
  - Tầng 2: Đánh thức Camera xác thực ngọn lửa bằng YOLO NCNN (Wake-up on Demand).

* **1.4.3. Giao thức truyền thông nội bộ MQTT:**
  - Cơ chế Publish / Subscribe, Broker Mosquitto, định dạng bản tin JSON.
  - Topic nhận dữ liệu: `iot/test/request` (ESP32 $\rightarrow$ Pi 5).
  - Topic điều khiển còi: `iot/test/response` (Pi 5 $\rightarrow$ ESP32).

* **1.4.4. Nền tảng Giám sát Web Dashboard (Tabler UI, WebSockets) và Blynk IoT Cloud.**

---

# CHƯƠNG 2: THỰC NGHIỆM VÀ KẾT QUẢ (17 – 20 trang)

### 2.1. THIẾT KẾ VÀ CHẾ TẠO SẢN PHẨM PHẦN CỨNG AIoT *(4 – 5 trang)*
* **2.1.1. Sơ đồ khối và Nguyên lý hoạt động phần cứng:**
  - Sơ đồ kết nối liên kết giữa ESP32, cụm cảm biến, mạch còi và trạm xử lý trung tâm Raspberry Pi 5.
* **2.1.2. Chi tiết các module phần cứng:**
  - **Khối thu thập dữ liệu & Báo động (ESP32):**
    - Cảm biến bụi siêu mịn laser **PMS5003** (giao tiếp UART qua GPIO 16, 17) đo các hạt bụi $PM_{1.0}, PM_{2.5}, PM_{10}$ và mật độ hạt $NC_{0.3} \rightarrow NC_{10}$.
    - Cảm biến khí độc và mùi cháy **SGP30** (giao tiếp I2C qua GPIO 21, 22) đo TVOC và $eCO_2$.
    - Cảm biến môi trường **DHT11** (chân dữ liệu GPIO 4) đo Nhiệt độ và Độ ẩm.
    - Còi báo động Buzzer điều khiển phát tần số 2000Hz bằng bộ điều chế xung **LEDC PWM** trên GPIO 27.
  - **Khối xử lý biên và Thị giác máy tính (Raspberry Pi 5):**
    - Bộ vi xử lý Broadcom BCM2712 Quad-Core ARM Cortex-A76 2.4GHz, RAM 8GB.
    - Camera CSI Picamera2 góc rộng góc quan sát khu vực giám sát.
* **2.1.3. Hình ảnh sản phẩm phần cứng thực tế và Sơ đồ đấu dây chi tiết.**

---

### 2.2. THỰC NGHIỆM TỐI ƯU HÓA MÔ HÌNH YOLO BẰNG GIẢI THUẬT DI TRUYỀN *(5 – 6 trang)*
*(Trình bày chi tiết dữ liệu thực nghiệm lưu tại thư mục: `C:\Users\OS\Desktop\train_model\YOLO_train_detection_GUI\runs\detect\fire_flame_tune`)*

* **2.2.1. Thiết lập bài toán Thực nghiệm Tiến hóa Siêu tham số:**
  - Tập dữ liệu hình ảnh ngọn lửa và khói (Fire & Flame Dataset).
  - Các nhiễm sắc thể siêu tham số được chọn tiến hóa:
    - `lr0`: Tốc độ học ban đầu (Khám phá biên độ $0.001 \rightarrow 0.01$).
    - `cls`: Trọng số hàm mất mát phân loại đối tượng ($0.4 \rightarrow 0.7$).
    - `degrees`: Góc xoay ngẫu nhiên tăng cường hình ảnh ngọn lửa ($0^\circ \rightarrow 1.0^\circ$).
  - Số lượng thế hệ/lần lặp: 10 thế hệ (Iterations), tổng thời gian tiến hóa: **14,779.41 giây (~4.11 giờ)**.
* **2.2.2. Phân tích Quá trình Tiến hóa qua từng Thế hệ (Dựa trên `tune_results.ndjson`):**
  - **Bảng theo dõi tiến hóa qua 10 thế hệ:**

| Thế hệ (Gen) | Siêu tham số `lr0` | Siêu tham số `cls` | Siêu tham số `degrees` | Độ thích nghi (Fitness) | Precision (%) | Recall (%) | mAP50 (%) | mAP50-95 (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gen 1** | 0.01000 | 0.50000 | 0.0000 | 0.46895 | 78.49% | 72.58% | 79.51% | 46.90% |
| **Gen 2** | 0.01000 | 0.50000 | 0.5718 | 0.46451 | 79.25% | 73.16% | 79.94% | 46.45% |
| **Gen 3** | 0.01000 | 0.50000 | 0.8974 | 0.46710 | 80.35% | 72.46% | 80.31% | 46.71% |
| **Gen 4** | 0.00986 | 0.50000 | 0.8974 | 0.46849 | 78.41% | 72.97% | 80.12% | 46.85% |
| **Gen 5** | 0.01000 | 0.45806 | 0.0000 | 0.46949 | 80.90% | 72.14% | 79.88% | 46.95% |
| <b style="color:red">Gen 6 (TỐI ƯU)</b> | <b style="color:red">0.00963</b> | <b style="color:red">0.64678</b> | <b style="color:red">0.8974</b> | <b style="color:red">0.47532</b> | <b style="color:red">82.24%</b> | <b style="color:red">71.88%</b> | <b style="color:red">81.05%</b> | <b style="color:red">47.53%</b> |
| **Gen 7** | 0.01000 | 0.69008 | 0.8974 | 0.47232 | 80.42% | 72.72% | 80.14% | 47.23% |
| **Gen 8** | 0.00985 | 0.65714 | 0.8974 | 0.46902 | 80.11% | 73.01% | 80.41% | 46.90% |
| **Gen 9** | 0.01000 | 0.50000 | 0.1128 | 0.47073 | 80.45% | 71.96% | 80.07% | 47.07% |
| **Gen 10** | 0.00977 | 0.53903 | 0.1047 | 0.46943 | 80.96% | 73.25% | 80.29% | 46.94% |

* **2.2.3. Đánh giá Kết quả Tối ưu của Cá thể Xuất sắc nhất (`best_hyperparameters.yaml`):**
  - Cá thể ưu tú nhất xuất hiện ở **Thế hệ thứ 6 (Iteration 6)** với hàm mục tiêu đạt **`Fitness = 0.47532`**.
  - Bộ gen siêu tham số tối ưu:
    - $\text{lr0} = 0.00963$
    - $\text{cls} = 0.64678$
    - $\text{degrees} = 0.8974$
  - So sánh trước và sau khi áp dụng GA:
    - Độ chính xác Precision tăng từ **$78.49\%$ lên $82.24\%$** (tăng $+3.75\%$).
    - Chỉ số $mAP_{50}$ tăng từ **$79.51\%$ lên $81.05\%$** (tăng $+1.54\%$).
    - Chỉ số $mAP_{50-95}$ tăng từ **$46.90\%$ lên $47.53\%$**.
  - **Phân tích các biểu đồ thực nghiệm:**
    - Biểu đồ biến thiên hàm thích nghi: `tune_fitness.png`.
    - Biểu đồ phân tán mức độ tương quan siêu tham số: `tune_scatter_plots.png`.
* **2.2.4. Đóng gói mô hình tối ưu sang NCNN (`best_ncnn_model`):**
  - Chuyển đổi trọng số `best.pt` của thế hệ 6 sang định dạng NCNN (`model.ncnn.param` và `model.ncnn.bin`).
  - Triển khai trực tiếp lên Raspberry Pi 5 để phục vụ suy luận thời gian thực.

---

### 2.3. TRIỂN KHAI PHẦN MỀM VÀ TÍCH HỢP HỆ THỐNG BIÊN PI 5 *(3 – 4 trang)*
* **2.3.1. Firmware C++ trên ESP32:**
  - Xây dựng vòng lặp non-blocking đa cảm biến, tính toán và đóng gói JSON gửi MQTT mỗi 3 giây.
  - Xử lý nhận bản tin phản hồi `iot/test/response` và kích hoạt ngắt còi an toàn.
* **2.3.2. Pipeline Xử lý 2 Tầng trên Raspberry Pi 5 (`infer_pi5_xgb.py`):**
  - **Tầng 1 (XGBoost Engine - Set E):**
    - Sử dụng bộ đệm trượt FIFO (`win=4`), trích xuất độ biến thiên khói và khí độc ($\Delta, shift$).
    - Độ trễ suy luận siêu tốc: **$\approx 15\text{ms} – 20\text{ms}$**.
  - **Tầng 2 (YOLO NCNN tối ưu bởi GA):**
    - Camera ở chế độ ngủ (Standby) tiết kiệm điện năng, chỉ thức dậy khi Tầng 1 báo nguy cơ.
    - Thời gian suy luận YOLO trên Pi 5: **$\approx 15\text{ms} – 20\text{ms}/frame$**.
    - **Cơ chế quản lý bộ nhớ thông minh:** Khung hình xử lý trực tiếp trên RAM; **chỉ lưu file vào thư mục `evidence/` khi xác thực có ngọn lửa thật**; nếu là báo động giả thì lập tức giải phóng bộ nhớ, không ghi đĩa tránh làm đầy thẻ nhớ SD.

---

### 2.4. XÂY DỰNG GIAO DIỆN GIÁM SÁT REAL-TIME VÀ CẢNH BÁO TỪ XA *(3 – 4 trang)*
* **2.4.1. Web Dashboard Giám sát Trung tâm (Tabler UI):**
  - Công nghệ FastAPI + WebSockets truyền số liệu cảm biến tức thời không cần tải lại trang.
  - Biểu đồ ApexCharts trực quan hóa đường cong biến thiên của PM2.5, TVOC và Nhiệt độ.
  - Khung xem ảnh bằng chứng trực tiếp và Thư viện ảnh (Evidence Gallery) hiển thị ảnh ngọn lửa có đóng khung đỏ Bounding Box.
  - Nút bấm điều khiển ngắt còi và reset hệ thống từ xa (`/api/reset_alarm`).
* **2.4.2. Tích hợp Cảnh báo Di động qua Blynk IoT Cloud (`blynk_notifier.py`):**
  - Cơ chế đồng bộ hóa qua REST API với mã bảo mật nạp từ file cấu hình `.env`.
  - Cập nhật Datastream chân ảo `V0` (Trạng thái an toàn: 0 / Cháy: 1).
  - Kích hoạt sự kiện khẩn cấp `fire_alert` loại *Critical/Warning* bắn thông báo đẩy (Push Notification) rung chuông điện thoại ngay lập tức khi phát hiện ngọn lửa.

---

### 2.5. KẾT QUẢ THỬ NGHIỆM THỰC TẾ VÀ ĐÁNH GIÁ ĐỘC LẬP *(3 – 4 trang)*
* **2.5.1. Kịch bản thử nghiệm 1: Môi trường bình thường và Tác nhân gây nhiễu (Báo động giả):**
  - Thử nghiệm xịt bình xịt khử trùng aerosol, đốt khói thuốc lá, bật đèn pin rọi vào camera.
  - Kết quả: Tầng 1 XGBoost phát hiện nồng độ hạt tăng $\rightarrow$ Đánh thức camera $\rightarrow$ Tầng 2 YOLO xác định 0/1 frame có lửa $\rightarrow$ Hủy báo động giả thành công, còi không kêu, không lưu ảnh rác vào bộ nhớ.
* **2.5.2. Kịch bản thử nghiệm 2: Đám cháy thực tế:**
  - Đốt lửa thực nghiệm (giấy, cồn, bật lửa).
  - Kết quả: XGBoost báo cháy $\rightarrow$ YOLO NCNN bắt được ngọn lửa với độ tin cậy $>80\%$ $\rightarrow$ Bật còi ESP32 tức thì, lưu ảnh bằng chứng vào `evidence/`, bắn Push Notification về điện thoại và Web Dashboard báo động đỏ.
* **2.5.3. Đánh giá Tổng hợp Hiệu năng Hệ thống:**
  - Bảng tổng hợp độ trễ từng khối (ESP32 $\rightarrow$ MQTT $\rightarrow$ XGBoost $\rightarrow$ YOLO NCNN $\rightarrow$ Còi/App).
  - Đánh giá khả năng tiết kiệm tài nguyên và độ ổn định khi chạy dài ngày.

---

## KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN (2 trang)
1. **Kết luận:**
   - Ứng dụng thành công **Giải thuật di truyền (GA)** vào bài toán tối ưu siêu tham số cho mạng nơ-ron nhận diện ngọn lửa, giúp nâng cao độ chính xác mAP lên $81.05\%$ và Precision đạt $82.24\%$.
   - Sản phẩm phần cứng AIoT 2 tầng hoạt động hoàn chỉnh, đáp ứng thời gian thực với độ trễ tổng thể dưới 100ms.
   - Giải quyết triệt để vấn đề báo động giả và bảo toàn bộ nhớ thiết bị nhúng.
2. **Hướng phát triển:**
   - Mở rộng thêm quần thể GA với nhiều siêu tham số mạng nơ-ron hơn (như kiến trúc backbone, anchor boxes).
   - Tích hợp thêm cảm biến ảnh nhiệt (Thermal Camera) phục vụ ban đêm.

---

## TÀI LIỆU THAM KHẢO & PHỤ LỤC (3 – 5 trang)
- **Tài liệu tham khảo:** Giáo trình Giải thuật di truyền, các bài báo IEEE/Scopus về Genetic Algorithm Hyperparameter Tuning, YOLOv8/NCNN, ESP32 và Edge AI.
- **Phụ lục mã nguồn:**
  - Toàn bộ file cấu hình tối ưu siêu tham số `best_hyperparameters.yaml` và log tiến hóa `tune_results.ndjson`.
  - Mã nguồn Firmware C++ ESP32 (`esp32_fire_sentinel.ino`).
  - Mã nguồn xử lý AI Pi 5 (`infer_pi5_xgb.py`, `blynk_notifier.py`, `dashboard/app.py`).
