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

---

## Nhận xét / Phân tích

- Mục 27 ("Nguyên tắc phát triển") thực chất là **kim chỉ nam thiết kế** của toàn bộ dự án và nên được đọc trước tiên khi bắt tay vào code, không chỉ đọc cuối cùng — nó giải thích *tại sao* kiến trúc lại phân lớp (ML → Anomaly → Rules → Graph → Risk → Agent) thay vì gọi thẳng LLM. Có thể cân nhắc đưa nguyên tắc này lên đầu README hoặc đầu file [00-tong-quan.md](./00-tong-quan.md) để người đọc/nhà tuyển dụng hiểu đúng triết lý dự án ngay từ câu đầu tiên.
- Đoạn mô tả CV ở mục 26 là một bản tóm tắt tốt, súc tích, đúng văn phong resume (verb + kết quả + công nghệ). Tuy nhiên nó chỉ có sức thuyết phục *nếu* dự án thực sự triển khai đủ các phần được liệt kê (XGBoost, anomaly detection, graph, LangGraph agent, human-in-the-loop, MLflow, Docker) — nên coi câu mô tả CV này như một "definition of done": nếu một dòng nào trong CV chưa làm được, thì chưa nên đưa dòng đó vào.
- Mục tiêu cuối cùng ("Detect → Score → Investigate → Explain → Review → Learn") là một framing rất mạnh để dùng làm **tagline** hoặc slide mở đầu khi trình bày dự án (phỏng vấn, video demo, README) — nó tóm tắt toàn bộ 28 mục trong tài liệu chỉ bằng 6 từ, và có thể dùng làm tiêu đề cho slide/README chính.
- Nhìn tổng thể ba mục 26-27-28: đây là phần "định vị" (positioning) của dự án, khác về bản chất với các mục kỹ thuật (1-22). Gợi ý: khi viết README chính hoặc trình bày trước người khác, nên bắt đầu bằng mục 28 (mục tiêu), sau đó mục 27 (nguyên tắc/triết lý), rồi mới đến kiến trúc kỹ thuật — thứ tự "why → what → how" thường thuyết phục hơn "what → how → why".
