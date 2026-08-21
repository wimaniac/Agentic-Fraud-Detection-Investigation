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

## Nhận xét / Phân tích

- Pipeline MLOps mô tả đúng luồng chuẩn (Data → Feature → Train → Evaluate → Registry → Production), nhưng chưa đề cập đến **feature store** hoặc cơ chế đảm bảo tính nhất quán giữa feature dùng lúc training và lúc serving (training-serving skew) — với các feature time-window như `transactions_last_5m`, đây là rủi ro kỹ thuật thực tế cần lưu ý khi vào Phase 9.
- Docker Compose gồm 6 service (api, postgres, redis, neo4j, ollama, dashboard) là gọn và hợp lý cho một máy dev/demo. Lưu ý: Ollama chạy LLM local có thể tốn RAM/GPU đáng kể, nên cân nhắc giới hạn tài nguyên (`mem_limit`, `deploy.resources`) trong compose file để tránh máy demo bị treo khi trình bày trực tiếp.
- Folder structure phản ánh khá sát kiến trúc: `app/agents` ↔ AI Investigation Agent, `app/rules` ↔ Rule Engine, `app/graph` ↔ Graph Fraud Detection, `training/` ↔ MLOps pipeline. Đây là điểm cộng vì cấu trúc code mapping trực tiếp với tài liệu thiết kế, giúp người review (hoặc nhà tuyển dụng xem CV) dễ đối chiếu.
- Điểm còn thiếu trong folder structure: chưa có thư mục riêng cho **feedback loop / retraining trigger** (ví dụ `app/feedback/` hoặc một scheduled job trong `scripts/`) — hiện `human_feedback` chỉ tồn tại như một bảng DB, cần có nơi chứa logic xử lý nó thành dữ liệu training.
