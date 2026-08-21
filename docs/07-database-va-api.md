# 07 — Database Design & API Design
## 18. Database Design

### PostgreSQL

Các bảng chính:

```text
users
transactions
merchants
devices
ip_addresses
fraud_cases
risk_scores
investigation_reports
human_feedback
```

### Neo4j

Nodes:

```text
User
Device
IP
Merchant
Transaction
```

Relationships:

```text
USES
CONNECTED_TO
PURCHASED_FROM
LOCATED_AT
SHARED_WITH
INVOLVED_IN
```

---

## 19. API Design

### Transaction

```http
POST /transactions
```

### Fraud Prediction

```http
POST /fraud/predict
```

### Investigation

```http
POST /investigations/{transaction_id}
```

### Risk

```http
GET /transactions/{transaction_id}/risk
```

### Graph

```http
GET /transactions/{transaction_id}/network
```

### Human Review

```http
POST /investigations/{id}/feedback
```

---

## Nhận xét / Phân tích

- Việc dùng song song PostgreSQL (dữ liệu quan hệ, giao dịch, feedback) và Neo4j (quan hệ mạng lưới) là kiến trúc **polyglot persistence** chuẩn cho bài toán fraud — mỗi công cụ giải quyết đúng loại truy vấn nó mạnh nhất (Postgres: giao dịch/ACID, Neo4j: truy vấn đồ thị nhiều bước như "tìm tất cả user cách nhau 2 hop qua thiết bị chung").
- Danh sách bảng Postgres còn thiếu một bảng trung gian quan trọng để đồng bộ hai hệ CSDL, ví dụ bảng ánh xạ `graph_sync_log` hoặc cơ chế event (outbox pattern) để đảm bảo dữ liệu giao dịch mới luôn được phản ánh sang Neo4j — nếu không, graph sẽ bị "trễ" so với dữ liệu giao dịch thực.
- API design hiện tại là RESTful cơ bản và đủ dùng cho MVP. Một vài điểm có thể bổ sung khi triển khai thực tế:
  - `POST /fraud/predict` nên trả về đồng thời risk score **và** breakdown theo từng thành phần (ML/Anomaly/Rule/Graph) để dashboard hiển thị được thanh "Reasons" như mục 15.
  - Có thể cần thêm endpoint dạng `GET /investigations/{id}` để lấy lại báo cáo đã sinh (không phải lúc nào cũng cần `POST` để tạo mới).
  - Endpoint feedback (`POST /investigations/{id}/feedback`) nên validate chặt theo 3 giá trị cố định (Confirm Fraud / False Positive / Need More Information) để đảm bảo chất lượng dữ liệu dùng cho retraining.
