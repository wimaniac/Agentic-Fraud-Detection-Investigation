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

Ví dụ:

```text
Why?

1. Transaction amount cao hơn 4.8× mức trung bình.
2. Device được sử dụng bởi 5 accounts.
3. IP liên quan đến 2 fraud cases.
4. 8 giao dịch xảy ra trong 3 phút.
5. Location thay đổi bất thường.
```

Có thể nghiên cứu thêm:

```text
SHAP
Feature Importance
Rule Evidence
Graph Evidence
```

Mục tiêu:

> Không chỉ nói "fraud", mà phải nói "tại sao".

---

## Nhận xét / Phân tích

- Human-in-the-Loop là thành phần biến SentinelAI thành một **closed-loop system** thực sự — điểm này khớp với triết lý "Detect → Score → Investigate → Explain → Review → Learn" ở [mục 28](./11-portfolio-nguyen-tac-muc-tieu.md). Về mặt UX, tùy chọn "Need More Information" cần có luồng xử lý riêng (ví dụ: đẩy trở lại agent để thu thập thêm bằng chứng) — tài liệu hiện chưa mô tả luồng này, nên cân nhắc bổ sung khi thiết kế UI.
- "Additional Verification" ở mức MEDIUM RISK (30-70) là một nhánh chưa được mô tả chi tiết ở phần nào khác của tài liệu (ví dụ: OTP, xác thực sinh trắc học, hay chỉ đơn giản là giữ giao dịch chờ). Nên làm rõ ở giai đoạn thiết kế chi tiết vì đây là một trải nghiệm người dùng thực tế, không chỉ là nội bộ hệ thống.
- Explainable AI kết hợp 4 nguồn bằng chứng (SHAP, Rule, Graph, feature importance) là cách tiếp cận đúng — giải thích tổng hợp từ nhiều mô hình đáng tin hơn giải thích từ một mô hình đơn lẻ. Về mặt kỹ thuật, SHAP cho XGBoost khá rẻ và trực tiếp; SHAP cho Isolation Forest/Autoencoder phức tạp hơn (thường cần KernelSHAP hoặc cách tiếp cận riêng), nên đây có thể là điểm tốn thời gian nhất trong Phase 8 của roadmap.
