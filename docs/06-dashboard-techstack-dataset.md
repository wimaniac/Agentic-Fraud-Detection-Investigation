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

