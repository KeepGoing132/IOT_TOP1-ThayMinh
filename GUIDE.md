1. Feature Engineering
1.1. Xác định các feature đầu vào
Trước tiên, tạo một baseline chỉ sử dụng các giá trị cảm biến hiện tại.
Nhóm	Feature
PMS5003	PM1.0, PM2.5, PM10
PMS5003	NC0.3, NC0.5, NC1.0, NC2.5, NC5.0, NC10
SGP30	eCO₂, TVOC
DHT11	Temperature, Humidity

Đây là nhóm current features.

Ví dụ một mẫu:
pm1_0       = 150
pm2_5       = 300
pm10        = 350
tvoc        = 150
eco2        = 450
temperature = 32.4
humidity    = 61


Sau đó mới bổ sung temporal features để xem chúng có cải thiện mô hình hay không.
1.2. Tạo lag features
Lag features lưu giá trị cảm biến ở các thời điểm trước đó.

Với dữ liệu mỗi 3 giây:
pm2_5_lag_3s
pm2_5_lag_6s
pm2_5_lag_9s

tvoc_lag_3s
tvoc_lag_6s

eco2_lag_3s


Ví dụ:
Thời điểm	PM2.5
t-6s	100
t-3s	180
t	300

Mẫu tại thời điểm t sẽ có:
pm2_5      = 300
pm2_5_lag_3s = 180
pm2_5_lag_6s = 100


XGBoost có thể học rằng PM2.5 đang tăng.
1.3. Tạo delta features
Delta thể hiện mức thay đổi của cảm biến.
\[
\Delta PM_{2.5}(t)=PM_{2.5}(t)-PM_{2.5}(t-3s)
\]

Ví dụ:
PM2.5(t-3s) = 180
PM2.5(t)    = 300

pm2_5_delta_3s = 120


Nên tạo:
pm1_0_delta_3s
pm2_5_delta_3s
pm10_delta_3s

tvoc_delta_3s
eco2_delta_3s

temperature_delta_3s
humidity_delta_3s


Bạn cũng có thể tạo delta trên cửa sổ dài hơn:
pm2_5_delta_6s
tvoc_delta_6s


Delta giúp phân biệt:
- PM2.5 cao và đang tăng.
- PM2.5 cao nhưng đang giảm.
- PM2.5 thấp và ổn định.
Đây là thông tin rất hữu ích với trường hợp lửa đã tắt nhưng bụi chưa giảm ngay.
1.4. Tạo rolling features
Rolling features là thống kê trên một cửa sổ thời gian gần nhất.

Ví dụ cửa sổ 10 giây:
pm2_5_mean_10s
pm2_5_max_10s
pm2_5_std_10s
pm2_5_slope_10s

tvoc_mean_10s
tvoc_max_10s
tvoc_slope_10s

eco2_mean_10s


Ý nghĩa:
Feature	Ý nghĩa
mean	Mức trung bình trong cửa sổ
max	Giá trị cao nhất
std	Độ dao động
slope	Xu hướng tăng hoặc giảm

Với dữ liệu 3 giây/mẫu, cửa sổ 10 giây có khoảng 4 mẫu. Cửa sổ 30 giây có khoảng 10 mẫu.

Mình đề xuất bắt đầu với cửa sổ 10 giây, sau đó thử 30 giây để so sánh.
Slope
Slope có thể được tính bằng hồi quy tuyến tính trên các mẫu trong cửa sổ.

Ví dụ:
PM2.5: 100 → 150 → 220 → 300


Slope dương thể hiện xu hướng tăng.

Ngược lại:
PM2.5: 500 → 450 → 350 → 300


Slope âm thể hiện xu hướng giảm.

Không nên chỉ dùng delta giữa hai điểm đầu/cuối nếu dữ liệu nhiễu nhiều; slope sử dụng toàn bộ các mẫu trong cửa sổ sẽ ổn định hơn.
1.5. Tạo feature theo tỷ lệ
Có thể thử thêm một số tỷ lệ:
pm1_0_to_pm2_5
pm2_5_to_pm10
nc0_3_to_nc0_5


Ví dụ:
\[
r=\frac{PM_{1.0}}{PM_{2.5}+\epsilon}
\]

Các tỷ lệ này có thể phản ánh sự phân bố kích thước hạt.

Tuy nhiên, đây là nhóm feature thử nghiệm. Không nên mặc định rằng chúng sẽ cải thiện kết quả. Cần kiểm tra bằng validation.
1.6. Không tạo feature từ tương lai
Khi dự đoán ở thời điểm \(t\), chỉ được sử dụng:
\[
X_t=f(x_t,x_{t-1},x_{t-2},\ldots)
\]

Không được dùng dữ liệu \(x_{t+1}\) hoặc những mẫu sau thời điểm \(t\).

Ví dụ, nếu tính pm2_5_mean_10s, phải dùng các mẫu trong 10 giây trước và tính đến thời điểm hiện tại.

Nếu sử dụng rolling window có tâm (center=True) thì có thể vô tình đưa dữ liệu tương lai vào feature, gây leakage.

2. Tạo các bộ feature để thử nghiệm
Mình đề xuất không tạo tất cả feature ngay từ đầu. Hãy chia thành các phiên bản:
Bộ feature	Thành phần
Feature Set A	Giá trị cảm biến hiện tại
Feature Set B	A + lag features
Feature Set C	A + delta features
Feature Set D	A + rolling features
Feature Set E	A + lag + delta + rolling
Feature Set F	E + các feature tỷ lệ

Như vậy, bạn có thể trả lời được:
- Temporal features có cải thiện mô hình không?
- Delta có hữu ích hơn lag không?
- Rolling window 10 giây hay 30 giây tốt hơn?
- Các feature NC có đóng góp đáng kể không?

3. Training XGBoost
3.1. Xác định X và y
Sau khi feature engineering:
X = df[feature_columns]y = df["label"]



Ví dụ:
X:
    pm2_5
    tvoc
    eco2
    pm2_5_delta_3s
    tvoc_delta_3s
    pm2_5_slope_10s
    ...

y:
    normal
    fire
    residual_smoke


Nếu dùng XGBoost multiclass, nên mã hóa nhãn:
from sklearn.preprocessing import LabelEncoderencoder = LabelEncoder()y_encoded = encoder.fit_transform(y)



Giữ lại encoder để chuyển kết quả dự đoán về tên class.
3.2. Chia train / validation / test
Với dữ liệu thời gian, không nên chia ngẫu nhiên từng dòng.

Hãy chia theo session hoặc lần thu thập dữ liệu:
Train:
    fire_session_01
    fire_session_02
    normal_session_01

Validation:
    fire_session_03
    normal_session_02

Test:
    fire_session_04
    normal_session_03


Các feature lag và rolling phải được tạo trong từng session riêng. Không được để lịch sử của session này nối sang session khác.
3.3. Xây dựng baseline
Bắt đầu với một cấu hình XGBoost đơn giản:
from xgboost import XGBClassifiermodel = XGBClassifier(    objective="multi:softprob",    num_class=3,    n_estimators=300,    max_depth=4,    learning_rate=0.05,    subsample=0.8,    colsample_bytree=0.8,    eval_metric="mlogloss",    random_state=42)model.fit(X_train, y_train)



Các tham số trên chỉ là baseline để bắt đầu, không phải tham số tối ưu.
3.4. Tuning hyperparameters
Sau khi baseline chạy được, thử các nhóm tham số:
Tham số	Giá trị thử
max_depth	3, 4, 5, 6
learning_rate	0.01, 0.03, 0.05, 0.1
n_estimators	100, 300, 500, 800
min_child_weight	1, 3, 5
subsample	0.7, 0.8, 1.0
colsample_bytree	0.7, 0.8, 1.0
reg_lambda	1, 5, 10

Không cần thử tất cả tổ hợp bằng grid search ngay. Có thể dùng RandomizedSearchCV hoặc Optuna sau khi có baseline.

4. Đánh giá mô hình
Không chỉ đánh giá accuracy.

Các metric nên có:
- Precision.
- Recall.
- F1-score.
- Confusion matrix.
- False positive rate.
Với bài toán cháy, cần đặc biệt chú ý:
- fire bị dự đoán thành normal.
- fire bị dự đoán thành residual_smoke.
- normal bị dự đoán thành fire.
Bạn cũng nên so sánh kết quả giữa các feature set:
Model	Feature set	Macro F1
Model A	Current features	...
Model B	Current + lag	...
Model C	Current + delta	...
Model D	Current + rolling	...
Model E	Full temporal features	...

Macro F1 hữu ích khi số lượng mẫu giữa các class không cân bằng.

Nếu class fire ít hơn normal, có thể thử sample_weight để cân bằng đóng góp của từng class trong quá trình training.

5. Phân tích feature importance
Sau khi train, kiểm tra feature nào đóng góp nhiều:
import pandas as pdimportance = pd.DataFrame({    "feature": model.feature_names_in_,    "importance": model.feature_importances_})importance = importance.sort_values(    "importance",    ascending=False)print(importance)



Ví dụ, nếu các feature quan trọng nhất là:
pm2_5_slope_10s
tvoc_delta_3s
pm2_5_mean_10s


thì xu hướng cảm biến có thể hữu ích hơn chỉ nhìn giá trị tức thời.

Tuy nhiên, feature_importances_ của XGBoost chỉ là phân tích ban đầu. Nếu cần giải thích sâu hơn, có thể dùng SHAP.

6. Thứ tự thực hiện thực tế
[ ] 1. Tạo current features từ các cột cảm biến
[ ] 2. Tạo lag features
[ ] 3. Tạo delta features
[ ] 4. Tạo rolling mean / max / std / slope
[ ] 5. Tạo các feature set A–F để so sánh
[ ] 6. Chia train / validation / test theo session
[ ] 7. Train XGBoost baseline
[ ] 8. Tuning hyperparameters
[ ] 9. So sánh Macro F1 và confusion matrix
[ ] 10. Phân tích feature importance
0/10 bước hoàn thành