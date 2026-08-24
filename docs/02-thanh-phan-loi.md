# 02 — Các thành phần lõi: Feature Engine · ML · Anomaly · Rule Engine

> Xem [README.md](./README.md) để có mục lục đầy đủ. **Ghi chú nhỏ đã
> thêm vào cuối mục 8 (Rule Engine)** — nội dung chính không đổi.

## 5. Transaction & Feature Engine

Input dự kiến:

```text
transaction_id
user_id
merchant_id
device_id
ip_address
timestamp
amount
payment_method
location
account_age
```

Feature có thể bao gồm:

```text
transaction_amount
transaction_frequency
transaction_velocity
average_transaction_amount
amount_deviation
account_age
number_of_devices
number_of_ips
number_of_merchants
previous_fraud_count
transactions_last_5m
transactions_last_1h
transactions_last_24h
distance_from_previous_location
```

Mục tiêu:

> Chuyển dữ liệu giao dịch thô thành các tín hiệu có ý nghĩa cho fraud detection.

---

## 6. Machine Learning Fraud Detection

Bắt đầu với các baseline model:

```text
Random Forest
XGBoost 
```

Model đầu tiên nên ưu tiên:

> XGBoost

vì phù hợp với dữ liệu dạng tabular và dễ đánh giá feature importance.

### Metrics

Không chỉ sử dụng Accuracy.

Các metrics chính:

```text
Precision
Recall
F1-score
ROC-AUC
PR-AUC
False Positive Rate
```

Đặc biệt chú ý:

> PR-AUC + Recall + False Positive Rate

vì fraud detection thường có dữ liệu mất cân bằng nghiêm trọng.

Ví dụ:

```text
Normal = 99.5%
Fraud  = 0.5%
```

Một model đoán toàn bộ giao dịch là Normal có thể đạt Accuracy rất cao nhưng hoàn toàn không hữu ích.

---

## 7. Anomaly Detection

Machine Learning supervised không phải lúc nào cũng phát hiện được các pattern gian lận mới.

Do đó bổ sung:

```text
Isolation Forest
Autoencoder
```

Mục tiêu:

> Tìm các giao dịch khác biệt đáng kể so với hành vi thông thường.

Ví dụ:

```text
User bình thường:

Average amount = 300,000₫
Transactions/day = 3

Giao dịch hiện tại:

Amount = 4,500,000₫
Transactions/5min = 8
```

→ Anomaly Score cao.

---

## 8. Rule Engine

Một số pattern có thể phát hiện hiệu quả bằng rule.

Ví dụ:

### Rule 1 — Transaction Velocity

```text
Nếu số giao dịch của một user trong 5 phút > N
→ tăng Risk Score
```

### Rule 2 — Device Sharing

```text
Nếu một device được sử dụng bởi nhiều user
→ tăng Risk Score
```

### Rule 3 — IP Reputation

```text
Nếu IP từng liên quan đến fraud
→ tăng Risk Score
```

### Rule 4 — Amount Deviation

```text
Nếu amount hiện tại >> historical average
→ tăng Risk Score
```

### Rule 5 — Impossible Travel

```text
Nếu user xuất hiện tại hai location cách rất xa
trong khoảng thời gian không hợp lý
→ tăng Risk Score
```

Rule Engine không thay thế ML mà cung cấp thêm tín hiệu.

