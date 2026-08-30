# 05 — Human-in-the-Loop & Explainable AI
## 13. Human-in-the-Loop

AI không nên tự động block mọi giao dịch có Risk Score cao.

Workflow:

```text
Risk < 30
   ↓
Auto Approve

30 ≤ Risk < 70
   ↓
Additional Verification

Risk ≥ 70
   ↓
AI Investigation
   ↓
Human Review
```

Human Reviewer có thể chọn:

```text
Confirm Fraud
False Positive
Need More Information
```

Feedback được lưu lại:

```text
Human Decision
      ↓
Feedback Dataset
      ↓
Retraining
      ↓
Improved Model
```

Mục tiêu là xây dựng một:

> Closed-loop AI system

### Triển khai Phase 7

Human Review UI được xây dựng bằng Streamlit (`streamlit_app.py`). Reviewer nhập
`transaction_id`, chạy investigation deterministic, sau đó chọn một trong ba
quyết định: `CONFIRM_FRAUD`, `FALSE_POSITIVE`, hoặc
`NEED_MORE_INFORMATION`.

Feedback được ghi append-only vào SQLite local
`data/feedback/human_feedback.sqlite` qua `HumanFeedbackRepository`. Mỗi record
lưu transaction ID, reviewer ID, decision, ghi chú, snapshot investigation và
timestamp UTC. Lưu append-only giúp audit được cả lượt review; không ghi đè
quyết định cũ.

Nút export tạo feedback dataset cho retraining. Chính sách nhãn:

- `CONFIRM_FRAUD` → `review_fraud_label = 1`;
- `FALSE_POSITIVE` → `review_fraud_label = 0`;
- `NEED_MORE_INFORMATION` không đưa vào retraining (`ready_for_retraining = false`).

UI không hiển thị `is_fraud` gốc của dataset cho reviewer, để tránh leakage
ground truth và giữ đúng ý nghĩa human review.

---

## 14. Explainable AI

Khi model trả về:

```text
Fraud Probability = 93%
```

hệ thống phải có khả năng giải thích.

**Trong triển khai hiện tại, chúng tôi đã triển khai Rule Explainability qua hàm `RuleEngine.get_rule_details()` cung cấp sự phân bổ cho từng loại rule (velocity, device, ip, amount, impossible_travel).** Điều này cung cấp một phần giải thích cho tại sao một giao dịch được đánh dấu là đáng ngờ.

Ví dụ:

```text
Why?

1. Transaction amount cao hơn 4.8× mức trung bình.
   (Rule contribution: amount_score = 75.0)

2. Device được sử dụng bởi 5 accounts.
   (Rule contribution: device_score = 70.0)

3. IP liên quan đến 2 fraud cases.
   (Rule contribution: ip_score = 90.0)

4. 8 giao dịch xảy ra trong 3 phút.
   (Rule contribution: velocity_score = 85.0)

5. Location thay đổi bất thường.
   (Graph/ML feature: account_degree = 15)
```

### Triển khai Phase 8

Mỗi investigation đưa thêm evidence có cấu trúc vào `investigation_summary`:

- **Native TreeSHAP**: `ModelExplainer` gọi `XGBoost.predict(...,
  pred_contribs=True)` để cho biết feature nào đẩy raw margin của model nền lên
  hoặc xuống. Đây không phải score mới, không tính lại calibrated probability,
  và không sửa Risk Score/tier/policy.
- **Feature importance**: tái sử dụng `feature_importances_` của fitted
  `XGBClassifier` để hiển thị top global features, tách biệt với local TreeSHAP.
- **Rule evidence**: `RuleEngine.get_rule_details()` từ Phase 3.
- **Graph evidence**: `GraphEvidenceExtractor` chuẩn hoá structural evidence
  (neighbors, centrality, component) và gắn cờ rõ ràng cho evidence dựa nhãn
  lịch sử (fraud ring). Tất cả là investigation/human-review evidence, không
  phải online ML feature hay policy input.
- **AI-generated explanation**: nếu DeepSeek được opt-in, nó chỉ viết lại JSON
  evidence đã hoàn tất thành báo cáo cho reviewer; không được suy luận thêm,
  tính điểm hoặc thay đổi quyết định deterministic.

Streamlit UI hiển thị local drivers, global importance và graph evidence. Nếu
TreeSHAP không thể đọc fitted model, investigation vẫn chạy và báo rõ evidence
không khả dụng thay vì tự tạo giải thích.

Mục tiêu:

> Không chỉ nói "fraud", mà phải nói "tại sao".


