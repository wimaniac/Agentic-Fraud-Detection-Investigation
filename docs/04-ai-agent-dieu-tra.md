# 04 — AI Investigation Agent & Investigation Report
## 11. AI Investigation Agent

Đây là phần giúp project thể hiện năng lực **AI Agent Engineer**.

LLM không trực tiếp thay thế fraud model.

Thay vào đó:

> ML phát hiện rủi ro → Agent điều tra nguyên nhân.

### Agent Tools

Agent có thể sử dụng:

```text
get_user_history()
get_transaction_history()
get_device_history()
get_ip_history()
query_transaction_graph()
get_similar_transactions()
check_fraud_rules()
```

### LangGraph Workflow

```text
START
  │
  ▼
Analyze Transaction
  │
  ▼
Read Risk Score
  │
  ├───────────────┐
  │               │
LOW RISK       HIGH RISK
  │               │
  ▼               ▼
 END        Investigation
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
    History     Graph      Rules
       │          │          │
       └──────────┼──────────┘
                  ▼
             Risk Analyst
                  │
                  ▼
          Investigation Report
```

---

## 12. Investigation Report

Agent cần tạo báo cáo có cấu trúc.

Ví dụ:

```text
FRAUD INVESTIGATION REPORT

Transaction:
TX-92831

Risk Score:
91/100

Risk Level:
HIGH

Executive Summary:
Giao dịch có mức độ đáng ngờ cao dựa trên nhiều tín hiệu
độc lập từ hành vi giao dịch, thiết bị và network graph.

Evidence:

1. Transaction velocity
   8 transactions trong 3 phút.

2. Device
   Device DEV-999 được sử dụng bởi 5 accounts.

3. IP
   IP Y từng xuất hiện trong 2 fraud cases.

4. Amount
   Giá trị giao dịch cao hơn 4.8 lần mức trung bình của user.

5. Graph
   User có liên kết với 3 accounts đã bị flag.

Recommendation:
→ HUMAN REVIEW

Confidence:
High
```

---

## Nhận xét / Phân tích

- Cách thiết kế "LLM không thay thế fraud model, mà điều tra nguyên nhân" là điểm mấu chốt giúp project tránh bẫy phổ biến (dùng LLM như một "black-box oracle" để phán fraud/không fraud) — đây cũng là nội dung được nhấn mạnh lại ở [mục 27 — Nguyên tắc phát triển](./11-portfolio-nguyen-tac-muc-tieu.md).
- 7 tool liệt kê cho agent đều là các hàm truy vấn dữ liệu (read-only) — điều này an toàn và hợp lý cho một investigation agent, vì agent chỉ cần thu thập bằng chứng chứ không cần quyền ghi/thay đổi dữ liệu giao dịch.
- Trong sơ đồ LangGraph, node "Risk Analyst" xuất hiện sau khi 3 nhánh (History, Graph, Rules) hội tụ — đây thực chất là bước tổng hợp bằng chứng thành báo cáo. Cần làm rõ node này là một lời gọi LLM riêng (tổng hợp) hay chỉ là bước ghép dữ liệu thuần túy, vì điều này ảnh hưởng đến độ trễ và chi phí gọi model.
- Investigation Report mẫu có cấu trúc rõ ràng (Summary, Evidence, Recommendation, Confidence) — nên định nghĩa đây thành **structured output schema** (ví dụ Pydantic model) ngay từ đầu để dễ validate và hiển thị lên dashboard, thay vì để LLM sinh free-text.
