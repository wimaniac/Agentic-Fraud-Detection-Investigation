# 06 — Dashboard · Technology Stack · Dataset
## 15. Dashboard

Sử dụng Streamlit.

Dashboard dự kiến:

```text
┌─────────────────────────────────────────────┐
│             FRAUD MONITORING                │
├─────────────────────────────────────────────┤
│                                             │
│ Transactions       Suspicious       Fraud   │
│    124,521             842            91    │
│                                             │
├─────────────────────────────────────────────┤
│ Transaction ID: TX-92831                    │
│                                             │
│ Risk Score                         91/100   │
│ ████████████████████████████████░░          │
│                                             │
│ Reasons                                     │
│                                             │
│ ⚠ Unusual transaction velocity              │
│ ⚠ New device                                │
│ ⚠ Suspicious IP                             │
│ ⚠ Connected accounts                        │
│                                             │
├─────────────────────────────────────────────┤
│              FRAUD NETWORK                  │
│                                             │
│       User A ─── Device X ─── User B        │
│          │                   │               │
│          └────── IP Y ───────┘               │
│                                             │
├─────────────────────────────────────────────┤
│ AI Investigation Report                     │
│                                             │
│ "This transaction is highly suspicious..."  │
│                                             │
│ [ CONFIRM FRAUD ] [ FALSE POSITIVE ]        │
└─────────────────────────────────────────────┘
```

---

## 16. Technology Stack

### Programming

```text
Python
```

### Machine Learning

```text
Scikit-learn
XGBoost / LightGBM
PyTorch
```

### AI Agent

```text
LangGraph
LangChain
Ollama
Local LLM
```

### Database

```text
PostgreSQL
Neo4j
Redis
```

### Backend

```text
FastAPI
```

### Frontend

```text
Streamlit
```

### MLOps

```text
MLflow
Docker
Docker Compose
```

### Data / Graph

```text
Pandas
NumPy
NetworkX
```

---

## 17. Dataset

Có thể bắt đầu với dataset public:

```text
IEEE-CIS Fraud Detection
PaySim
```

Sau đó tạo thêm synthetic fraud network để mô phỏng:

```text
Normal Users
Fraud Users
Shared Devices
Shared IPs
Fraud Merchants
Fraud Rings
```

Ví dụ:

```text
NORMAL

User A → Device 1 → IP 1
User B → Device 2 → IP 2
User C → Device 3 → IP 3


FRAUD RING

User A ─┐
User B ─┼── Device 99 ── IP 77
User C ─┘
                 │
                 ▼
             Merchant X
```

---

## Nhận xét / Phân tích

- Bố cục dashboard đề xuất (tổng quan số liệu → chi tiết giao dịch → graph network → báo cáo AI → hành động review) đi đúng theo luồng tư duy của một chuyên viên điều tra thật, từ tổng quan đến chi tiết đến quyết định — đây là nguyên tắc UX hợp lý cho công cụ vận hành (operational tool), không chỉ là dashboard báo cáo.
- Tech stack khá đầy đủ và tự-host được (Ollama, local LLM, PostgreSQL, Neo4j, Redis) — phù hợp cho demo cá nhân/CV vì không phụ thuộc API trả phí. Điểm cần lưu ý: chạy LLM local đủ mạnh để làm agent điều tra có chất lượng tốt sẽ cần GPU hoặc model nhỏ được lựa chọn cẩn thận; nên benchmark sớm để tránh việc agent suy luận kém ảnh hưởng đến chất lượng investigation report.
- IEEE-CIS và PaySim là hai lựa chọn dataset kinh điển và hợp lý cho fraud detection tabular, nhưng **cả hai đều không có sẵn dữ liệu graph** (device/IP sharing giữa nhiều user thực tế khá thưa). Việc tài liệu đã tính đến bước "tạo synthetic fraud network" bổ sung là cần thiết và đúng đắn — nên coi đây là một sub-task quan trọng trong Phase 4 (Graph Fraud Detection) chứ không phải phần phụ.
