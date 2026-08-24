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
