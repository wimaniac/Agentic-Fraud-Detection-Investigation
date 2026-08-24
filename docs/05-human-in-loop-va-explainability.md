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

Có thể nghiên cứu thêm:

```text
SHAP
Feature Importance
Rule Evidence (đã có qua RuleEngine.get_rule_details())
Graph Evidence
```

Mục tiêu:

> Không chỉ nói "fraud", mà phải nói "tại sao".


