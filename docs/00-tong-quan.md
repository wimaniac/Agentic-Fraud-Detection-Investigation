# 00 — Tổng quan dự án SentinelAI
## 1. Tổng quan dự án

**SentinelAI** là một nền tảng AI end-to-end nhằm phát hiện, đánh giá rủi ro, điều tra và giải thích các giao dịch tài chính đáng ngờ.

Khác với hệ thống fraud detection chỉ trả về `fraud = true/false`, SentinelAI kết hợp:

- Machine Learning
- Anomaly Detection
- Rule-based Detection
- Graph Analysis
- AI Agent / Agentic AI
- Human-in-the-Loop
- Explainable AI
- MLOps

Mục tiêu là xây dựng một hệ thống gần với quy trình thực tế:

```text
Giao dịch
   ↓
Feature Engineering
   ↓
ML + Anomaly + Rules + Graph
   ↓
Risk Score
   ↓
┌───────────────┬────────────────────┐
│ Low Risk      │ High Risk          │
│               │                    │
│ Auto Approve  │ AI Investigation   │
│               │        ↓           │
│               │ Human Review       │
└───────────────┴────────────────────┘
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

---

## Nhận xét / Phân tích

- Đây là một project **rất tham vọng**: nó không chỉ là một mô hình ML đơn lẻ mà là một hệ thống tích hợp 5 lớp phát hiện (ML, Anomaly, Rule, Graph, Agent) cộng với vòng lặp con người. Về mặt phạm vi, đây gần với sản phẩm cấp doanh nghiệp hơn là một đồ án cá nhân thông thường.
- Mục tiêu 11 gạch đầu dòng ở mục 3.1 thực chất tương ứng gần như 1-1 với 8-9 phần kiến trúc phía sau — điều này cho thấy tài liệu được viết có hệ thống, nhưng cũng có nghĩa là khối lượng công việc thực thi rất lớn so với một cá nhân làm trong thời gian ngắn.
- Điểm mạnh nhất về mặt định vị: SentinelAI không dừng ở "phát hiện" mà đi đến "giải thích" và "học lại" — đây chính là điểm khác biệt so với các project fraud-detection phổ biến trên GitHub, và nên được nhấn mạnh khi trình bày dự án.
- Rủi ro cần lưu ý sớm: với scope lớn thế này, nên xác định ngay từ đầu đâu là "MVP thực sự chạy được" và đâu là phần "nice-to-have" để tránh việc dự án bị dở dang. Phần [Roadmap](./09-roadmap.md) đã có cấu trúc theo phase, có thể dùng làm cơ sở để cắt giảm nếu cần.
