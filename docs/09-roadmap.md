# 09 — Roadmap phát triển

> Xem [README.md](./README.md) để có mục lục đầy đủ. **Phase 5 đã được
> cập nhật** — xem ghi chú trong mục đó để biết vì sao khác bản gốc.

## Phase 1 — Baseline Fraud Detection

- [x] Download dataset.
- [x] Data cleaning.
- [x] Exploratory Data Analysis.
- [x] Feature Engineering.
- [x] Train Logistic Regression. *(có thể bổ sung sau nếu cần baseline tham chiếu — hiện chưa làm)*
- [x] Train Random Forest.
- [x] Train XGBoost/LightGBM.
- [x] Evaluate Precision, Recall, F1, ROC-AUC, PR-AUC.
- [x] Chọn baseline production model. *(XGBoost, đã calibrate bằng Sigmoid)*
- [x] Time-based train/calib/test split (đã sửa từ random split ban đầu).
- [x] Kiểm tra và sửa 2 nguồn leakage (account-aggregate, calibration fit/eval).

## Phase 2 — Anomaly Detection

- [x] Implement Isolation Forest.
- [x] Xây dựng anomaly score (0-100, sigmoid normalization từ tập train).
- [x] So sánh supervised model với anomaly model (4-Quadrant Analysis).
- [ ] ~~Kết hợp anomaly score vào Risk Score~~ — **ĐÃ HỦY**, xem Phase 5.
- [x] Thay bằng: `flag_novel_anomaly()` — cờ escalation độc lập, ngưỡng
      percentile 98 tính từ tập train.

## Phase 3 — Rule Engine

- [x] Transaction velocity.
- [x] Device sharing.
- [x] IP reputation.
- [x] Amount deviation.
- [x] Impossible travel.
- [x] Xây dựng Rule Score.
- [ ] ~~Kết hợp Rule Score vào Risk Score~~ — **ĐÃ HỦY**, xem Phase 5.
- [x] Thay bằng: `flag_extreme_rule()` — cờ escalation độc lập.
- [x] `get_rule_details()` — breakdown theo từng nhóm luật, dùng cho
      Investigation Report (Phase 6) thay vì cộng điểm.

## Phase 4 — Graph Fraud Detection

- [x] Xây dựng transaction graph.
- [x] Implement NetworkX prototype (`graph_analysis.py`).
- [x] Xây dựng Neo4j database (`neo4j_ingest.py` + docker-compose).
- [x] Query suspicious connections.
- [x] Detect shared device/IP.
- [x] Detect fraud rings.
- [x] Tạo Graph Score (`graph_score.py`, leave-one-out chống leakage).
- [x] **Quyết định tích hợp**: nhúng feature đồ thị (`in_ring`,
      `account_degree`, `n_shared_types`) vào Feature Engine (mục 5)
      thay vì dùng Graph Score như 1 nhánh cộng điểm độc lập — xem
      [03-graph-va-risk-score.md](./03-graph-va-risk-score.md) mục
      "Vai trò của Graph trong kiến trúc hiện tại".

## Phase 5 — Risk Engine

> ⚠️ **Checklist gốc mô tả "combine 4 score" — đã thay đổi sau khi kiểm
> chứng bằng số liệu thật.** Xem
> [03-graph-va-risk-score.md](./03-graph-va-risk-score.md) mục 10 để có
> giải thích đầy đủ.

- [x] ~~Combine ML Score + Anomaly Score + Rule Score + Graph Score~~
      **ĐÃ THAY ĐỔI** → Risk Score = 100% ML Score (weight_ml=1.0).
- [x] Kiểm chứng thực nghiệm: đo PR-AUC khi trộn từng nguồn phụ (Anomaly,
      Rule) — cả 2 đều làm giảm PR-AUC, quyết định không trộn.
- [x] Xây dựng cơ chế **Cờ Escalation** thay thế: `flag_novel_anomaly()`,
      `flag_extreme_rule()` — độc lập với Risk Score, có thể ép escalate.
- [x] Normalize Risk Score về 0–100.
- [x] Xây dựng risk thresholds (30/70), kiểm chứng bằng bảng phân tầng
      thực tế trên test set 100K giao dịch (~2% volume bắt ~80% fraud).
- [x] Ngưỡng cờ escalation dùng percentile tính từ train (98), không
      dùng số cố định đoán tay.


## Phase 6 — AI Investigation Agent

- [x] Thiết kế LangGraph workflow.
- [x] User History Tool.
- [x] Transaction History Tool.
- [x] Device History Tool.
- [x] IP History Tool.
- [x] Graph Query Tool. *(có thể tái dùng Neo4j đã build ở Phase 4)*
- [x] Rule Analysis Tool. *(dùng `RuleEngine.get_rule_details()` đã có sẵn — không cần viết lại)*
- [x] Similar Case Tool.
- [x] Investigation Agent.
- [x] Structured Investigation Report.

## Phase 7 — Human-in-the-Loop

- [x] Human Review UI (Streamlit).
- [x] Confirm Fraud.
- [x] False Positive.
- [x] Need More Information.
- [x] Lưu feedback (append-only SQLite adapter).
- [x] Chuẩn bị feedback dataset/export cho retraining.

## Phase 8 — Explainability

- [x] SHAP. *(native TreeSHAP của XGBoost qua `pred_contribs`; không thêm dependency)*
- [x] Feature importance. *(tái sử dụng `feature_importances_` của XGBoost)*
- [x] Rule evidence. *(`get_rule_details()` đã làm xong ở Phase 3)*
- [x] Graph evidence. *(structural + historical-label provenance, investigation-only)*
- [x] AI-generated explanation. *(DeepSeek chỉ diễn đạt deterministic evidence khi opt-in)*

## Phase 9 — Productionization

- [x] Cấu trúc package `src/` (features, anomaly, risk_engine, rule_engine).
- [x] FastAPI. *(health, investigation, risk, graph evidence và feedback API)*
- [x] Feature pipeline dùng chung train/infer (`mode="train"/"infer"`,
      chặn leakage khi thiếu artifact).
- [x] PostgreSQL. *(SQLAlchemy + psycopg, immutable investigation snapshots và append-only feedback)*
- [x] Redis. *(optional fail-open cache cho risk/network và idempotency key; không phải audit/score store)*
- [x] Neo4j (đã setup ở Phase 4).
- [x] GPT. *(DeepSeek chỉ viết evidence-grounded report khi opt-in)*
- [x] Streamlit. *(Human Review UI dùng SQLite local hoặc PostgreSQL khi có `DATABASE_URL`)*
- [x] Docker Compose. *(API, dashboard, PostgreSQL, Redis, Neo4j)*
- [x] MLflow. *(best-effort tracking cho train/evaluation; server + artifact volume trong Compose)*
- [x] Production-feedback retraining lifecycle. *(append-only transaction intake, eligibility gate, chronological candidate evaluation, challenger/champion registry aliases)*
- [x] Unit tests cho feature pipeline, adapter, calibration logic.
- [x] Integration tests. *(FastAPI + SQL adapter qua SQLite in-memory; Docker service validation phụ thuộc quyền Docker host)*
- [x] Logging. *(PII-safe structured JSON request logs với correlation ID)*
- [x] Monitoring. *(Prometheus HTTP/investigation metrics và Compose service)*

---

