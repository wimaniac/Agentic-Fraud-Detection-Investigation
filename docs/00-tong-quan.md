# 00 — Tổng quan dự án SentinelAI
## 1. Tổng quan dự án

**SentinelAI** là một nền tảng AI end-to-end nhằm phát hiện, đánh giá rủi ro, điều tra và giải thích các giao dịch tài chính đáng ngờ.

Khác với hệ thống fraud detection chỉ trả về `fraud = true/false`, SentinelAI kết hợp:

- Machine Learning (Supervised)
- Anomaly Detection (Unsupervised) - dùng làm cờ escalation riêng biệt
- Rule-based Detection - dùng làm cờ escalation riêng biệt và giải thích
- Graph Analysis - tính năng sẵn có trong ML features
- AI Agent / Agentic AI (phase sắp tới)
- Human-in-the-Loop (phase sắp tới)
- Explainable AI (đã có qua Rule Engine)
- MLOps (phase sắp tới)

Mục tiêu là xây dựng một hệ thống gần với quy trình thực tế:

```text
Giao dịch
   ↓
Feature Engineering
   ↓
ML Score ──┐
           ├──→ Risk Score (0-100) ──┐
Anomaly Score ─┘                     ↓
Rule Score  ───────────────────────→ Escalation Flags + Explainability ──→ Investigation Agent
                                                                   ↓
                                                            Human Review
```

---

## 2. Bài toán thực tế

Trong hệ thống thanh toán, số lượng giao dịch có thể rất lớn. Không phải giao dịch bất thường nào cũng là gian lận, và không phải gian lận nào cũng có thể phát hiện bằng một rule đơn giản.

Ví dụ:

```text
User A
 │
 ├── 10:01 → 500,000₫ → Shop X
 ├── 10:03 → 490,000₫ → Shop Y
 ├── 10:04 → 495,000₫ → Shop Z
 └── 10:05 → 480,000₫ → Shop X

Device: DEV-999
IP: 103.xxx.xxx
```

Hệ thống cần trả lời:

> Giao dịch này có đáng ngờ không? Nếu có, tại sao?

Kết quả mong muốn không chỉ là:

```json
{
  "fraud": true
}
```

mà phải có khả năng giải thích:

```text
Risk Score: 92/100

Lý do:
- 7 giao dịch xảy ra trong 5 phút
- Tần suất giao dịch cao bất thường
- Thiết bị mới
- IP từng liên quan đến tài khoản bị đánh dấu
- Giá trị giao dịch khác đáng kể so với lịch sử người dùng
- Tài khoản có liên kết với nhiều tài khoản đáng ngờ

Quyết định:
HIGH RISK → Human Review
```

---

## 3. Mục tiêu dự án

### 3.1. Mục tiêu chính

Xây dựng một hệ thống có khả năng:

1. Nhận dữ liệu giao dịch.
2. Tạo các đặc trưng phục vụ fraud detection.
3. Phát hiện gian lận bằng Machine Learning.
4. Phát hiện bất thường bằng Anomaly Detection.
5. Áp dụng Rule Engine để phát hiện các mẫu gian lận rõ ràng.
6. Phân tích mối quan hệ giữa User, Device, IP, Merchant bằng Graph.
7. Kết hợp nhiều tín hiệu thành một Risk Score.
8. Tự động điều tra các giao dịch có rủi ro cao bằng AI Agent.
9. Sinh báo cáo điều tra có giải thích.
10. Cho phép Human Reviewer xác nhận hoặc bác bỏ kết quả.
11. Lưu feedback để phục vụ cải thiện model.


