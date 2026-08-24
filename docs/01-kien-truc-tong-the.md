# 01 — Kiến trúc tổng thể

> **Đã cập nhật** so với bản thiết kế gốc, dựa trên kết quả kiểm chứng thực
> nghiệm trên dữ liệu thật (1M giao dịch) qua các Phase 1-4. Xem mục "Lịch
> sử thay đổi" ở cuối file để biết chính xác đã sửa gì và vì sao.

## 4. Kiến trúc tổng thể

```text
                                  TRANSACTION
                                       │
                                       ▼
                    ┌────────────────────────────────────┐
                    │           Feature Engine           │
                    └──────────────────┬─────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
        ┌──────────┐             ┌──────────┐             ┌──────────┐
        │ ML Model │             │ Anomaly  │             │  Rules   │
        │ (XGBoost │             │  Model   │             │  Engine  │
        │calibrated)│            │(Isolation│             │(5 nhóm   │
        │          │             │ Forest)  │             │ luật)    │
        └─────┬────┘             └─────┬────┘             └─────┬────┘
              │                        │                        │
              │ weight = 1.0           └───────────┬────────────┘
              │                                    │ weight = 0.0
              ▼                                    ▼
    ┌──────────────────────┐            ┌────────────────────────────────┐
    │   Risk Aggregator    │            │        Cờ Escalation           │
    │  (chỉ nhận ML Score) │            │  flag_novel_anomaly()  +       │
    └──────────┬───────────┘            │  flag_extreme_rule()           │
               │                        └──────────────┬─────────────────┘
               ▼                                       │
         ┌───────────┐                                 │
         │ Risk Score│◄────────────────────────────────┘
         │  (0-100)  │   (cờ có thể ép escalate dù Risk Score thấp)
         └─────┬─────┘
               │
     ┌─────────┼──────────┐
     ▼         ▼          ▼
   LOW       MEDIUM      HIGH
     │         │          │
     ▼         ▼          ▼
 APPROVE   ADDITIONAL   Investigation Agent
           VERIFICATION       │
            (OTP/2FA)         │
                  ┌────────────────────┼────────────────────┐
                  ▼                    ▼                    ▼
             User History         Graph Analysis       Rule Analysis
             (lịch sử giao         (truy vấn Neo4j/     (get_rule_details()
              dịch của account      NetworkX cho riêng    — CÙNG module với
              đang bị điều tra)     giao dịch này)         Rules Engine ở trên)
                  │                    │                    │
                  └────────────────────┼────────────────────┘
                                       ▼
                              Investigation Report
                                       │
                                       ▼
                                Human Reviewer
                                       │
                         ┌─────────────┴─────────────┐
                         ▼                           ▼
                    Confirm Fraud              False Positive
                         │                           │
                         └─────────────┬─────────────┘
                                       ▼
                                Feedback Dataset
                                       │
                                       ▼
                                  Retraining
```

---

## Nhận xét / Phân tích

- **Điểm hội tụ tại Risk Aggregator KHÔNG còn là "3 model hội tụ bình
  đẳng"** như bản vẽ gốc. Đây là thay đổi quan trọng nhất, dựa trên kiểm
  chứng thực nghiệm 2 lần độc lập (validation set và test set 100K giao
  dịch thật): trộn tuyến tính Anomaly Score và Rule Score vào Risk Score
  theo trọng số cố định làm PR-AUC **giảm** (lần lượt khoảng -0.03 đến
  -0.05), chứ không cải thiện như giả định ban đầu. Nguyên nhân khác
  nhau cho từng nguồn:
  - **Anomaly Score**: độc lập với ML nhưng quá yếu — chỉ ~2.8-4.5% giao
    dịch bị gắn cờ "bất thường" thực sự là fraud.
  - **Rule Score**: không yếu, nhưng dùng lại đúng những feature thô mà
    XGBoost đã học tối ưu (velocity, ip_risk...) với trọng số đoán tay
    thay vì học từ dữ liệu — về bản chất là "bản sao kém hơn" của cùng
    thông tin, nên trộn vào chỉ pha loãng.

  Giải pháp: tách 2 nguồn này thành **Cờ Escalation riêng biệt**
  (`flag_novel_anomaly()`, `flag_extreme_rule()`) — không cộng điểm,
  chỉ bật cờ boolean có thể ép hệ thống escalate lên Investigation Agent
  dù Risk Score (chỉ từ ML) đang ở mức thấp. Cách này giữ được giá trị
  thật của cả 2 tín hiệu (bắt case hiếm mà ML bỏ sót) mà không làm hỏng
  độ chính xác của con số chính.

- **Risk Score giờ rẽ 3 tầng (LOW / MEDIUM / HIGH), không phải 2 tầng**
  như bản gốc. Đây là kết quả đã kiểm chứng bằng số liệu thật: chỉ
  ~2% giao dịch (tầng MEDIUM+HIGH gộp lại) đã bắt được ~80% tổng số
  fraud — một tỷ lệ vận hành hoàn toàn khả thi mà hệ thống 2 tầng không
  thể hiện được. Tầng MEDIUM ánh xạ với hành động "Additional
  Verification / Step-up 2FA" — một bước trung gian trước khi phải đẩy
  sang Investigation Agent tốn kém hơn.

- **"Rules Engine" ở đầu pipeline và "Rule Analysis" trong nhánh điều
  tra HIGH RISK thực ra là CÙNG MỘT MODULE**, dùng ở 2 thời điểm khác
  nhau — không cần 2 implementation riêng như bản vẽ gốc ngụ ý:
  - `calculate_rule_score()`: chạy sớm, cho ra cờ escalation.
  - `get_rule_details()`: chạy khi điều tra sâu 1 giao dịch cụ thể, trả
    về breakdown theo từng nhóm luật (velocity/device/ip/amount/travel)
    — đây chính là nguyên liệu cho Investigation Report (mục 12), thứ
    mà xác suất ML thuần không tự giải thích được.

- **Quyết định Graph Score — đã chọn phương án A (nhúng vào Feature
  Engine, không tách thành nhánh song song riêng).** Feature Engine đã
  tính sẵn `in_ring`, `account_degree`, `n_shared_types` từ dữ liệu
  Graph (Phase 4) và đưa thẳng vào feature set của ML Model — nghĩa là
  tín hiệu đồ thị đã ảnh hưởng gián tiếp lên `ml_prob`, không cần một
  "Graph Score" độc lập cộng thêm vào Risk Aggregator. Hệ quả code:
  tham số `weight_graph` trong `RiskScoreAggregator` nên được **loại bỏ**
  (không chỉ để mặc định = 0) để tránh gây hiểu nhầm là có 1 nhánh Graph
  Score đang hoạt động song song.

  **Đánh đổi có ý thức của lựa chọn này:** hệ thống mất khả năng tạo cờ
  escalation riêng cho graph (kiểu "giao dịch nằm trong 1 ring đã biết
  nhiều case fraud, dù ML điểm thấp") — tương tự cách Anomaly/Rules đang
  làm. Nếu sau này muốn phục hồi khả năng này, `graph_score.py` đã build
  sẵn ở Phase 4 (kỹ thuật leave-one-out, không leakage) có thể tái sử
  dụng làm nguồn thứ 3 cho nhánh Cờ Escalation — nhưng cần kiểm chứng
  bằng số liệu thật y hệt cách đã làm với Anomaly và Rules trước khi
  đưa vào, tránh lặp lại giả định chưa kiểm chứng như thiết kế ban đầu.

  **Lưu ý phân biệt quan trọng:** nhánh "Graph Analysis" trong sub-pipeline
  điều tra HIGH RISK ở dưới sơ đồ **không mâu thuẫn** với quyết định
  này — đó là truy vấn Neo4j/NetworkX cho **1 giao dịch cụ thể đã bị
  đánh dấu HIGH**, phục vụ Investigation Agent tìm bằng chứng (ai liên
  quan, ring nào), khác hoàn toàn với việc có 1 "Graph Score" cộng vào
  Risk Score lúc chấm điểm ban đầu.

- Vòng lặp khép kín ở cuối (Confirm/False Positive → Feedback →
  Retraining) là điểm cần thiết kế cẩn thận nhất về mặt data
  engineering, vì đây là nơi hệ thống "học" — nếu thiếu chuẩn hóa schema
  của feedback dataset, việc retraining sẽ khó tái sử dụng. Phần này
  chưa bị ảnh hưởng bởi các thay đổi ở trên, giữ nguyên như thiết kế gốc.

- Gợi ý bổ sung (chưa làm): có thể vẽ thêm một sơ đồ triển khai
  (deployment diagram) tách bạch giữa phần realtime (dưới 1 giây, phục
  vụ Risk Aggregator + Cờ Escalation) và phần batch/offline (User
  History, Graph Analysis, Retraining) vì độ trễ yêu cầu của hai phần
  này rất khác nhau.

---

## Lịch sử thay đổi

| Thay đổi | Lý do | Bằng chứng |
|---|---|---|
| Risk Aggregator chỉ nhận ML Score (weight=1.0); Anomaly + Rules tách thành Cờ Escalation riêng | Trộn tuyến tính làm giảm PR-AUC | Đo 2 lần độc lập trên validation set và test set 100K giao dịch thật: -0.0342 (Anomaly), -0.0379 (Rule) |
| Risk Score: 3 tầng (LOW/MEDIUM/HIGH) thay vì 2 (LOW/HIGH) | Vận hành thực tế cần bước trung gian trước Investigation Agent | Tầng MEDIUM+HIGH (~2% volume) bắt được ~80% fraud trên test set thật |
| `weight_graph` bị loại khỏi `RiskScoreAggregator` | Graph đã nhúng vào Feature Engine, không cần nhánh song song riêng | Quyết định thiết kế (phương án A), chưa kiểm chứng phương án B bằng số liệu |
| Rules Engine dùng chung 1 module cho cả "Rules Engine" (đầu pipeline) và "Rule Analysis" (điều tra) | Tránh trùng lặp code, đảm bảo nhất quán logic | `calculate_rule_score()` và `get_rule_details()` cùng nằm trong `rule_engine.py` |