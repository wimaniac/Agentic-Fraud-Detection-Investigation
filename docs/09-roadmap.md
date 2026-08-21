# 09 — Roadmap phát triển
## Phase 1 — Baseline Fraud Detection

- [x] Download dataset.
- [x] Data cleaning.
- [x] Exploratory Data Analysis.
- [x] Feature Engineering.
- [x] Train Random Forest.
- [x] Train XGBoost.
- [x] Evaluate Precision, Recall, F1, ROC-AUC, PR-AUC.
- [x] Chọn baseline production model.

## Phase 2 — Anomaly Detection

- [ ] Implement Isolation Forest.
- [ ] Xây dựng anomaly score.
- [ ] So sánh supervised model với anomaly model.
- [ ] Kết hợp anomaly score vào Risk Score.

## Phase 3 — Rule Engine

- [ ] Transaction velocity.
- [ ] Device sharing.
- [ ] IP reputation.
- [ ] Amount deviation.
- [ ] Impossible travel.
- [ ] Xây dựng Rule Score.

## Phase 4 — Graph Fraud Detection

- [ ] Xây dựng transaction graph.
- [ ] Implement NetworkX prototype.
- [ ] Xây dựng Neo4j database.
- [ ] Query suspicious connections.
- [ ] Detect shared device/IP.
- [ ] Detect fraud rings.
- [ ] Tạo Graph Score.

## Phase 5 — Risk Engine

- [ ] Combine ML Score.
- [ ] Combine Anomaly Score.
- [ ] Combine Rule Score.
- [ ] Combine Graph Score.
- [ ] Normalize Risk Score về 0–100.
- [ ] Xây dựng risk thresholds.

## Phase 6 — AI Investigation Agent

- [ ] Thiết kế LangGraph workflow.
- [ ] User History Tool.
- [ ] Transaction History Tool.
- [ ] Device History Tool.
- [ ] IP History Tool.
- [ ] Graph Query Tool.
- [ ] Rule Analysis Tool.
- [ ] Similar Case Tool.
- [ ] Investigation Agent.
- [ ] Structured Investigation Report.

## Phase 7 — Human-in-the-Loop

- [ ] Human Review UI.
- [ ] Confirm Fraud.
- [ ] False Positive.
- [ ] Need More Information.
- [ ] Lưu feedback.
- [ ] Chuẩn bị feedback dataset.

## Phase 8 — Explainability

- [ ] SHAP.
- [ ] Feature importance.
- [ ] Rule evidence.
- [ ] Graph evidence.
- [ ] AI-generated explanation.

## Phase 9 — Productionization

- [ ] FastAPI.
- [ ] PostgreSQL.
- [ ] Redis.
- [ ] Neo4j.
- [ ] Ollama.
- [ ] Streamlit.
- [ ] Docker Compose.
- [ ] MLflow.
- [ ] Unit tests.
- [ ] Integration tests.
- [ ] Logging.
- [ ] Monitoring.

---

## Nhận xét / Phân tích

- Thứ tự 9 phase đi theo đúng logic phụ thuộc: Rule/Anomaly/Graph (Phase 2-4) đều là các nguồn tín hiệu độc lập cần có **trước** khi có thể xây Risk Engine (Phase 5); Risk Engine lại cần có trước AI Agent (Phase 6) vì agent chỉ được kích hoạt khi risk score đủ cao. Đây là trình tự hợp lý, nên giữ nguyên.
- Nếu làm một mình hoặc trong thời gian giới hạn (ví dụ đồ án tốt nghiệp/portfolio 2-3 tháng), có thể cân nhắc một **MVP rút gọn** trước khi làm đủ 9 phase:
  - *MVP tối thiểu để demo được toàn bộ luồng đầu-cuối:* Phase 1 (rút gọn, chỉ cần 1 model) → Phase 3 (2-3 rule đơn giản, bỏ qua Phase 2 Anomaly) → Phase 5 (rút gọn, bỏ Anomaly Score) → Phase 6 (Agent với 3-4 tool) → Phase 7 (UI review đơn giản).
  - Sau khi luồng đầu-cuối chạy được, quay lại bổ sung Phase 2 (Anomaly), Phase 4 (Graph — phần khó nhất), Phase 8 (Explainability), Phase 9 (Production hoá).
  - Lý do: một demo "mỏng nhưng chạy trọn luồng" (Detect → Score → Investigate → Review) có giá trị trình bày cao hơn nhiều so với 9 phase làm dở dang.
- Phase 9 (Productionization) gộp khá nhiều việc khác nhau (hạ tầng, testing, logging, monitoring) — có thể tách thêm thành Phase 9a (hạ tầng & deployment) và Phase 9b (chất lượng: test/logging/monitoring) nếu cần theo dõi tiến độ chi tiết hơn.
- Không có ô nào trong roadmap đề cập đến **viết tài liệu/video demo** — trong khi mục 25-26 của tài liệu gốc (xem [Đánh giá, Demo & Portfolio](./10-danh-gia-va-demo.md)) coi video demo là sản phẩm đầu ra quan trọng. Nên thêm một checklist nhỏ "Chuẩn bị demo" vào cuối Phase 9.
