# 11 — Portfolio Value · Nguyên tắc phát triển · Mục tiêu cuối cùng
## 26. Portfolio / CV Value

Sau khi hoàn thành, project có thể mô tả trong CV:

> **SentinelAI — Agentic Fraud Detection & Investigation Platform**
>
> Built an end-to-end fraud detection platform combining XGBoost, anomaly detection, rule-based scoring, graph analysis, and LangGraph-based AI agents to detect and investigate suspicious financial transactions. Implemented human-in-the-loop review, explainable risk scoring, Neo4j transaction graphs, FastAPI services, MLflow tracking, and Docker-based deployment.

Điểm quan trọng là project thể hiện được nhiều năng lực cùng lúc:

```text
Machine Learning
       +
Anomaly Detection
       +
Graph AI
       +
LLM
       +
AI Agent
       +
Backend
       +
Database
       +
MLOps
       +
Deployment
```

---

## 27. Nguyên tắc phát triển

Không xây project theo hướng:

```text
LLM
 ↓
Prompt
 ↓
"Is this fraud?"
```

Mà theo hướng:

```text
Data
 ↓
Deterministic Features
 ↓
ML
 ↓
Anomaly Detection
 ↓
Rules
 ↓
Graph
 ↓
Risk Engine
 ↓
AI Agent Investigation
 ↓
Human Review
 ↓
Feedback
 ↓
Model Improvement
```

LLM/Agent là **một thành phần trong hệ thống**, không phải toàn bộ hệ thống.

---

## 28. Mục tiêu cuối cùng

SentinelAI hướng tới một hệ thống:

> **Detect → Score → Investigate → Explain → Review → Learn**

Thay vì chỉ phát hiện gian lận, hệ thống phải có khả năng **giải thích tại sao giao dịch đáng ngờ, thu thập bằng chứng, hỗ trợ chuyên viên điều tra và học lại từ quyết định của con người.**

Đây là mục tiêu quan trọng nhất của project.

