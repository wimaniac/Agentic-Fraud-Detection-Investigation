# 04 — AI Investigation Agent & Investigation Report

> Xem [README.md](./README.md) để có mục lục đầy đủ. **Ghi chú nhỏ đã
> thêm ở mục 11 (Agent Tools)** — nội dung chính không đổi.

## 11. AI Investigation Agent

Đây là phần giúp project thể hiện năng lực **AI Agent Engineer**.

LLM không trực tiếp thay thế fraud model.

Thay vào đó:

> ML phát hiện rủi ro → Agent điều tra nguyên nhân.

### Phân định trách nhiệm deterministic và LLM

- Risk Score, risk tier, escalation và action là **deterministic**: XGBoost,
  Risk Engine và policy code quyết định; LLM không được thay thế hoặc sửa các kết quả này.
- Bảy tool điều tra (rule, graph, user/device/IP history, transaction history,
  similar case) luôn chạy theo workflow cố định; chúng không do LLM chọn hay gọi.
- LLM (DeepSeek) chỉ chạy ở bước cuối để chuyển evidence JSON đã hoàn tất thành
  Investigation Report dễ đọc cho Human Reviewer. Nếu LLM lỗi, hệ thống giữ report
  template deterministic và không làm thay đổi quyết định.

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

> **[ĐÃ CẬP NHẬT]** `check_fraud_rules()` **không cần viết mới** —
> ánh xạ thẳng vào `RuleEngine.get_rule_details()` đã build và kiểm
> chứng sẵn ở Phase 3 (`rule_engine.py`). Hàm này trả về breakdown theo
> 5 nhóm luật (velocity/device/ip/amount/impossible_travel), đúng định
> dạng dữ liệu Agent cần để trích dẫn bằng chứng trong Investigation
> Report — tiết kiệm đáng kể thời gian Phase 6 vì phần "tính toán" đã
> xong, chỉ cần bọc thành 1 tool interface cho Agent gọi.
>
> Tương tự, `query_transaction_graph()` có thể tái sử dụng trực tiếp các
> Cypher query đã viết sẵn ở Phase 4 (`docs/cypher_queries.md`, đặc biệt
> mục 3 — "Tra cứu 1 user cụ thể").

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

> **Lưu ý nhỏ:** "Read Risk Score" ở đây nên đọc **cả** Risk Score
> (0-100, từ ML) **lẫn** 2 cờ escalation (`flag_novel_anomaly`,
> `flag_extreme_rule`) — không chỉ Risk Score đơn thuần. Một giao dịch
> có Risk Score thấp nhưng cờ escalation bật vẫn nên đi vào nhánh
> Investigation, theo đúng thiết kế đã cập nhật ở
> [03-graph-va-risk-score.md](./03-graph-va-risk-score.md) mục 10.

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

