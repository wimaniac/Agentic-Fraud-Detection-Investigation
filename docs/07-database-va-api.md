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

