# 01 — Kiến trúc tổng thể
## 4. Kiến trúc tổng thể

```text
                         TRANSACTION
                              │
                              ▼
                    ┌──────────────────┐
                    │  Data Adapter    │ 
                    └─────────┬────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Feature Engine  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ ML Model │   │ Anomaly  │   │  Rules   │
        │          │   │  Model   │   │  Engine  │
        └─────┬────┘   └─────┬────┘   └─────┬────┘
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                    ┌─────────────────┐
                    │ Risk Aggregator │
                    └────────┬────────┘
                             │
                             ▼
                       ┌───────────┐
                       │ Risk Score│
                       └─────┬─────┘
                             │
                   ┌─────────┴─────────┐
                   ▼                   ▼
               LOW RISK            HIGH RISK
                   │                   │
                   ▼                   ▼
                APPROVE        Investigation Agent
                                       │
                  ┌────────────────────┼────────────────────┐
                  ▼                    ▼                    ▼
             User History         Graph Analysis       Rule Analysis
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

- Đây là kiến trúc dạng **pipeline phân nhánh**: 3 mô hình (ML, Anomaly, Rules) chạy song song trên cùng một feature set, sau đó hội tụ tại "Risk Aggregator". Về mặt hệ thống, điều này gợi ý các model này nên là các service/module độc lập, có thể triển khai và cập nhật riêng biệt (không phải một khối monolith).
- Nhánh "HIGH RISK" là phần phức tạp nhất vì nó rẽ thành một sub-pipeline điều tra (History, Graph, Rule Analysis) trước khi hội tụ lại thành báo cáo — về bản chất đây chính là logic của [AI Investigation Agent](./04-ai-agent-dieu-tra.md).
- Vòng lặp khép kín ở cuối (Confirm/False Positive → Feedback → Retraining) là điểm cần thiết kế cẩn thận nhất về mặt data engineering, vì đây là nơi hệ thống "học" — nếu thiếu chuẩn hóa schema của feedback dataset, việc retraining sẽ khó tái sử dụng.
- Gợi ý bổ sung (không có trong bản gốc): có thể vẽ thêm một sơ đồ triển khai (deployment diagram) tách bạch giữa phần realtime (dưới 1 giây, phục vụ auto-approve) và phần batch/offline (điều tra, retraining) vì độ trễ yêu cầu của hai phần này rất khác nhau.
