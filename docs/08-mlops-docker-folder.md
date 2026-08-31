# 08 — MLOps · Docker Architecture · Folder Structure
## 20. MLOps

MLflow được sử dụng để:

```text
Experiment Tracking
Parameter Tracking
Metric Tracking
Model Versioning
Model Registry
```

Pipeline:

```text
Data
 ↓
Feature Engineering
 ↓
Training
 ↓
Evaluation
 ↓
MLflow
 ↓
Model Registry
 ↓
Production Model
```

---

## 21. Docker Architecture

```text
docker-compose.yml

├── api
├── postgres
├── redis
├── neo4j
├── ollama
└── dashboard
```

Mục tiêu:

```bash
docker compose up
```

có thể khởi động toàn bộ hệ thống.

### Triển khai Phase 9 (đến Docker Compose)

`docker-compose.yml` hiện chạy `api`, `dashboard`, `postgres`, `redis`,
`neo4j`, `mlflow` và `prometheus`. Data/model artifacts được mount read-only vào API/dashboard thay vì
đóng vào image. Để khởi động local, copy `.env.example` thành `.env`, thay
password mặc định, rồi chạy:

```bash
docker compose up --build
```

Trước khi chạy, thêm `SENTINEL_API_KEY` dài và ngẫu nhiên vào `.env`. Gọi API
nghiệp vụ với `X-API-Key: <giá trị đó>`; không đưa key này vào source hay log.

API ở cổng `8000`, dashboard ở `8501`, MLflow ở `5000`, Prometheus ở `9090`;
PostgreSQL, Redis, Neo4j, MLflow và Prometheus dùng named volumes. API cần
`SENTINEL_API_KEY` trong `.env` cho các endpoint nghiệp vụ; `/health` và
`/metrics` không dùng key. Không dùng `.env` chứa DeepSeek key trong Docker Compose.

Khi chưa có dữ liệu mới, dùng `scripts/import_legacy_baseline.py` để tạo một
MLflow run audit-only từ model artifacts hiện có. Script không retrain, không
đọc dữ liệu giao dịch hoặc feedback, và gắn tag `retrospective_import` để không
nhầm với experiment thực nghiệm.

### Production-feedback model lifecycle

```text
POST /transactions (append-only payload)
  → deterministic investigation
  → Human Review: CONFIRM_FRAUD / FALSE_POSITIVE
  → GET /retraining/eligibility
  → scripts/retrain_from_feedback.py
  → MLflow run + Registry alias challenger
  → human metric review
  → scripts/promote_challenger.py --version N --approve
  → Registry alias champion
```

`NEED_MORE_INFORMATION` không được curate thành label. Candidate không tự động
thành Champion; người vận hành phải duyệt metrics trên holdout đã khóa theo thời
gian trước khi chạy lệnh promote.

## Registry và serving an toàn

Import baseline lịch sử chỉ để audit (không có metric được đánh giá lại), vì vậy
nó được tag `baseline_not_validated` và không được tự động phục vụ:

```powershell
rtk uv run python scripts/import_legacy_baseline.py --tracking-uri http://localhost:5000
```

Khi `/retraining/eligibility` đạt ngưỡng, tạo candidate từ các transaction đã
được reviewer giải quyết. Payload phải giữ đủ raw fields của feature pipeline,
kể cả `in_ring`, `account_degree`, và `n_shared_types`; nhãn chỉ được suy ra từ
`CONFIRM_FRAUD`/`FALSE_POSITIVE` sau review.

```powershell
rtk uv run python scripts/retrain_from_feedback.py --database-url "postgresql+psycopg://..."
rtk uv run python scripts/promote_challenger.py --version N --approve
```

Với Docker Compose, chạy các lệnh này bên trong `api` container sau khi image đã
được rebuild, để dùng đúng PostgreSQL và MLflow nội bộ. Artifact tạm chỉ cần tồn
tại đến khi MLflow upload xong:

```powershell
docker compose exec api uv run python scripts/retrain_from_feedback.py --artifact-dir /tmp/candidate
docker compose exec api uv run python scripts/promote_challenger.py --version N --approve
```

Lệnh promote chỉ đổi Registry alias `champion`; nó không đổi risk formula hay
threshold. Sau khi duyệt và promote, đặt `MODEL_SOURCE=mlflow` trong `.env` và
triển khai lại riêng service `api` để tiến trình mới nạp alias `champion` cùng
feature artifacts đã version hóa. Trước khi được duyệt, API tiếp tục dùng
`MODEL_SOURCE=local`; không có fallback âm thầm từ MLflow champion sang model
khác nếu cấu hình MLflow bị lỗi.

---

## 22. Folder Structure

```text
sentinel-ai/
│
├── app/
│   ├── api/
│   ├── agents/
│   ├── models/
│   ├── features/
│   ├── rules/
│   ├── graph/
│   ├── services/
│   ├── database/
│   └── schemas/
│
├── training/
│   ├── datasets/
│   ├── features/
│   ├── train.py
│   ├── evaluate.py
│   └── experiments/
│
├── tests/
│
├── dashboard/
│
├── notebooks/
│
├── docker/
│
├── scripts/
│
├── configs/
│
├── docs/
│
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

---
