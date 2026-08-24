# 10 — Tiêu chí đánh giá thành công & Demo Scenario

> Xem [README.md](./README.md) để có mục lục đầy đủ. **Demo Scenario (mục
> 25) đã được viết lại** để khớp với kiến trúc Risk Score đã kiểm chứng —
> xem [03-graph-va-risk-score.md](./03-graph-va-risk-score.md) mục 10.

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

> ⚠️ **Đã viết lại.** Bản gốc minh họa Risk Score = tổng có trọng số của
> 4 nguồn (ML/Anomaly/Rule/Graph). Kiến trúc hiện tại KHÔNG cộng theo
> cách đó — xem giải thích ngay sau bảng.

Một demo hoàn chỉnh nên chạy như sau:

```text
1. Transaction TX-92831 xuất hiện
            ↓
2. Feature Engine tạo features
   (đã bao gồm sẵn feature đồ thị: in_ring, account_degree, n_shared_types)
            ↓
3. ML Model (XGBoost, đã calibrate) → ml_prob = 0.82
            ↓
4. Risk Score = 1.0 × 0.82 × 100 = 82  →  Risk Tier: HIGH (≥70)
            ↓
5. SONG SONG — kiểm tra 2 cờ Escalation (không cộng vào Risk Score):

   Anomaly Model (Isolation Forest) → anomaly_score = 91
        → 91 ≥ ngưỡng percentile 98 (~92.66 trên tập train)?
        → SÁT ngưỡng, giả sử KHÔNG vượt → flag_novel_anomaly = False

   Rule Engine → rule_score = 80
        → 80 ≥ ngưỡng flag_extreme_rule (ví dụ 80)?
        → flag_extreme_rule = True
        → get_rule_details(): velocity_score=85, ip_score=72,
          device_score=40, amount_score=55, impossible_travel_score=90
            ↓
6. Vì Risk Tier đã là HIGH (từ bước 4) VÀ có 1 cờ escalation bật (bước 5)
   → củng cố quyết định, không có mâu thuẫn giữa 2 tín hiệu
            ↓
7. LangGraph Investigation Agent được kích hoạt (Risk Tier = HIGH)
            ↓
8. Agent gọi các tools — bao gồm Rule Analysis Tool, dùng THẲNG
   get_rule_details() đã tính ở bước 5, không cần tính lại
            ↓
9. Phân tích User History + Graph Analysis (Neo4j, riêng cho TX-92831)
   + Rule breakdown (đã có sẵn)
            ↓
10. Sinh Investigation Report — trích dẫn cả 3 nguồn: ML score, cờ nào
    đã bật (nếu có), breakdown rule chi tiết
            ↓
11. Human Reviewer
            ↓
12. Confirm Fraud / False Positive
            ↓
13. Lưu feedback
```

### Vì sao ví dụ trên khác bản gốc

Bản demo gốc cộng 4 điểm (`0.82 + 0.91 + 0.80 + 0.95 → 91/100`) để MINH
HỌA ý tưởng ban đầu. Nhưng khi kiểm chứng bằng số liệu thật, cách cộng
này được xác nhận làm giảm độ chính xác tổng thể (xem
[03-graph-va-risk-score.md](./03-graph-va-risk-score.md)). Ví dụ trên đã
sửa để phản ánh đúng cách hệ thống **thật sự** ra quyết định:

- **Risk Score chỉ từ ML** (không pha loãng bởi Anomaly/Rule).
- **Anomaly/Rule đóng vai trò cờ xác nhận độc lập** — nếu chúng đồng ý
  với ML (như case này), tăng độ tin cậy của quyết định; nếu chúng
  KHÔNG bật cờ dù ML nói HIGH, đó không phải mâu thuẫn (ML vẫn đủ để
  quyết định); nhưng nếu ML nói LOW mà 1 cờ vẫn bật, đó mới là tín hiệu
  quan trọng cần escalate thêm — xem kịch bản phụ bên dưới.

### Kịch bản phụ nên có trong video demo (bổ sung)

Để tránh demo chỉ toàn case "mọi tín hiệu đều đồng ý" (thiếu thuyết
phục), nên thêm ít nhất 1 trong các kịch bản sau:

```text
Kịch bản A — ML thấp nhưng Anomaly cao (giá trị thật của cờ escalation):
    ml_prob = 0.15  → Risk Score = 15  → Tier: LOW (nếu chỉ nhìn ML)
    anomaly_score = 96  → VƯỢT ngưỡng percentile 98
    → flag_novel_anomaly = True
    → HỆ THỐNG VẪN ESCALATE dù Risk Score gốc thấp
    → đây chính là case Anomaly Detection "cứu" được mà ML bỏ sót

Kịch bản B — Risk Score cao nhưng Human Reviewer xác nhận False Positive:
    → chứng minh giá trị thật của Human-in-the-Loop (mục 13),
      không phải bước hình thức
```

---
