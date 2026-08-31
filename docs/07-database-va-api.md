# 07 — Database Design & API Design

> Xem [README.md](./README.md) để có mục lục đầy đủ. **Phần "Nhận xét"
> cuối file đã cập nhật 1 đoạn** liên quan đến response của
> `/fraud/predict` — xem đánh dấu bên dưới.

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

### Triển khai Phase 9 (phần PostgreSQL + API)

Production API dùng `DATABASE_URL` với dialect `postgresql+psycopg`. Hai bảng
đầu tiên đã được triển khai qua SQLAlchemy:

- `investigation_reports`: immutable snapshot của một investigation
  deterministic, kèm score/tier để audit và truy vấn API;
- `human_feedback`: append-only reviewer decisions, bắt buộc tham chiếu đến một
  investigation đã persist. `NEED_MORE_INFORMATION` vẫn yêu cầu notes.

`Database.create_schema()` chỉ tạo bảng còn thiếu và không xoá/ghi đè audit
records. SQLite chỉ được hỗ trợ cho integration tests; runtime production dùng
PostgreSQL.

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

Các endpoint hiện có:

```http
GET  /health
POST /investigations/{transaction_id}
GET  /transactions/{transaction_id}/risk
GET  /transactions/{transaction_id}/network
POST /investigations/{investigation_id}/feedback
```

`POST /investigations` luôn khởi tạo workflow không có LLM model; vì vậy API
không biến request thành DeepSeek call có chi phí. Score/tier/action vẫn do
pipeline deterministic quyết định.

### Redis cache

Redis chỉ cache response đọc nhiều (`risk`, `network`) trong 5 phút và giữ
idempotency key của `POST /investigations` tối đa 24 giờ. Cache là fail-open:
nếu Redis không khả dụng, API vẫn dùng PostgreSQL và workflow deterministic;
Redis không được dùng cho audit record, feedback chính thức hoặc Risk Score.

### Authentication · logging · monitoring

Các endpoint nghiệp vụ yêu cầu header `X-API-Key` khi `SENTINEL_API_KEY` được
cấu hình. Docker Compose chạy `APP_ENV=production`, nên thiếu key sẽ fail-closed
thay vì công khai API. `/health` và `/metrics` được giữ riêng cho health check
và Prometheus scrape.

Request log ở stdout là JSON gồm request ID, route template, status và latency;
không log body, transaction ID hoặc snapshot. Prometheus chỉ dùng label route
template/risk tier để tránh high-cardinality và PII.

