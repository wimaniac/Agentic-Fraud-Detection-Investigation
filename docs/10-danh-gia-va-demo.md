# 10 — Tiêu chí đánh giá thành công & Demo Scenario
## 24. Tiêu chí đánh giá thành công

### ML

```text
Precision
Recall
F1
PR-AUC
False Positive Rate
```

### System

```text
Prediction latency
Investigation latency
API throughput
Memory usage
Model inference time
```

### Agent

```text
Tool-call correctness
Investigation completeness
Evidence coverage
Structured output validity
Human agreement rate
```

### Business-oriented

```text
Fraud detection rate
False positive rate
Number of cases requiring human review
Average investigation time
```

---

## 25. Demo Scenario

Một demo hoàn chỉnh nên chạy như sau:

```text
1. Transaction TX-92831 xuất hiện
            ↓
2. Feature Engine tạo features
            ↓
3. ML Model → 0.82
            ↓
4. Anomaly Model → 0.91
            ↓
5. Rule Engine → 0.80
            ↓
6. Graph Analysis → 0.95
            ↓
7. Risk Aggregator
            ↓
8. Risk Score = 91/100
            ↓
9. HIGH RISK
            ↓
10. LangGraph Investigation Agent
            ↓
11. Agent gọi các tools
            ↓
12. Phân tích User + Device + IP + Graph
            ↓
13. Sinh Investigation Report
            ↓
14. Human Reviewer
            ↓
15. Confirm Fraud
            ↓
16. Lưu feedback
```

Đây là flow chính cần thể hiện trong video demo.

---

## Nhận xét / Phân tích

- Bốn nhóm tiêu chí (ML / System / Agent / Business) bao phủ khá toàn diện — đặc biệt nhóm "Agent" (tool-call correctness, evidence coverage, structured output validity, human agreement rate) là điểm ít project fraud detection khác có, vì phần lớn project chỉ dừng ở nhóm "ML". Đây là điểm nên nhấn mạnh khi trình bày vì nó cho thấy tư duy đánh giá một hệ thống AI Agent thực thụ, không chỉ một mô hình.
- "Human agreement rate" (tỷ lệ agent đồng thuận với quyết định cuối của con người) là chỉ số quan trọng nhất trong nhóm Agent nhưng cũng khó đo nhất — nó chỉ có ý nghĩa sau khi đã tích lũy đủ dữ liệu feedback từ Phase 7. Nên coi đây là một chỉ số theo dõi dài hạn (sau khi hệ thống chạy một thời gian) chứ không phải chỉ số benchmark ngay từ đầu.
- Demo Scenario mô tả rất rõ ràng và cụ thể (có transaction ID, số điểm từng bước) — đây gần như là một kịch bản video demo hoàn chỉnh, chỉ cần bổ sung: thời lượng ước tính cho mỗi bước, và một kịch bản phụ (ví dụ giao dịch LOW RISK được auto-approve) để cho thấy hệ thống không phải lúc nào cũng "báo động", tránh cảm giác demo bị thiên lệch chỉ vào trường hợp fraud.
- Gợi ý bổ sung: nên có thêm một kịch bản "False Positive" (Risk Score cao nhưng Human Reviewer chọn False Positive) để chứng minh giá trị thực sự của Human-in-the-Loop — nếu demo chỉ toàn "Confirm Fraud" thì phần Human Review sẽ trông như bước hình thức chứ không phải một lớp bảo vệ thực sự.
