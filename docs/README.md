## Mục lục

| # | File | Nội dung (mục gốc) |
|---|------|---------------------|
| 00 | [00-tong-quan.md](./00-tong-quan.md) | Tổng quan dự án, bài toán thực tế, mục tiêu chính *(mục 1-3)* |
| 01 | [01-kien-truc-tong-the.md](./01-kien-truc-tong-the.md) | Kiến trúc tổng thể *(mục 4)* |
| 02 | [02-thanh-phan-loi.md](./02-thanh-phan-loi.md) | Feature Engine, ML Fraud Detection, Anomaly Detection, Rule Engine *(mục 5-8)* |
| 03 | [03-graph-va-risk-score.md](./03-graph-va-risk-score.md) | Graph-based Fraud Detection, Risk Aggregation *(mục 9-10)* |
| 04 | [04-ai-agent-dieu-tra.md](./04-ai-agent-dieu-tra.md) | AI Investigation Agent, Investigation Report *(mục 11-12)* |
| 05 | [05-human-in-loop-va-explainability.md](./05-human-in-loop-va-explainability.md) | Human-in-the-Loop, Explainable AI *(mục 13-14)* |
| 06 | [06-dashboard-techstack-dataset.md](./06-dashboard-techstack-dataset.md) | Dashboard, Technology Stack, Dataset *(mục 15-17)* |
| 07 | [07-database-va-api.md](./07-database-va-api.md) | Database Design (PostgreSQL/Neo4j), API Design *(mục 18-19)* |
| 08 | [08-mlops-docker-folder.md](./08-mlops-docker-folder.md) | MLOps, Docker Architecture, Folder Structure *(mục 20-22)* |
| 09 | [09-roadmap.md](./09-roadmap.md) | Roadmap phát triển — 9 phase *(mục 23)* |
| 10 | [10-danh-gia-va-demo.md](./10-danh-gia-va-demo.md) | Tiêu chí đánh giá thành công, Demo Scenario *(mục 24-25)* |
| 11 | [11-portfolio-nguyen-tac-muc-tieu.md](./11-portfolio-nguyen-tac-muc-tieu.md) | Portfolio/CV Value, Nguyên tắc phát triển, Mục tiêu cuối cùng *(mục 26-28)* |

## Cách đọc gợi ý

- **Nếu bạn mới bắt đầu / muốn hiểu triết lý dự án trước:** đọc `11 → 00 → 01` (mục tiêu & nguyên tắc trước, sau đó mới vào kiến trúc).
- **Nếu bạn đang trong lúc code / triển khai:** dùng `09-roadmap.md` làm checklist chính, tra cứu chi tiết kỹ thuật ở các file `02` đến `08` tương ứng với từng phase.
- **Nếu bạn chuẩn bị demo hoặc viết CV:** đọc `10` và `11`.

## Nhận xét tổng quan về toàn bộ kế hoạch

- **Điểm mạnh nổi bật:** tài liệu gốc đã có tư duy hệ thống rất tốt — kiến trúc phân lớp rõ ràng (feature → nhiều mô hình song song → risk aggregation → agent → human review → feedback loop), và framing "Detect → Score → Investigate → Explain → Review → Learn" là một định vị mạnh, khác biệt so với các project fraud-detection thông thường chỉ dừng ở phân loại nhị phân.
- **Rủi ro lớn nhất là phạm vi (scope):** dự án bao phủ 5 kỹ thuật AI khác nhau (ML, Anomaly, Rule, Graph, Agent) cộng với backend, 3 loại database, MLOps và dashboard — đây là khối lượng công việc cấp sản phẩm doanh nghiệp. Khuyến nghị cụ thể đã nêu ở [09-roadmap.md](./09-roadmap.md): xây một MVP "mỏng nhưng chạy trọn luồng đầu-cuối" trước, rồi mới lần lượt bổ sung độ sâu cho từng thành phần (đặc biệt là Graph, vốn là phần khó và tốn thời gian nhất).
- **Khoảng trống cần bổ sung khi triển khai chi tiết** (đã ghi chú rải rác trong từng file, tổng hợp lại):
  1. Cách chuẩn hóa & gán trọng số khi cộng 4 loại score thành Risk Score (file 03).
  2. Cơ chế feature store / tránh training-serving skew cho các feature time-window (file 02, 08).
  3. Luồng xử lý cho lựa chọn "Need More Information" và "Additional Verification" (file 05).
  4. Cơ chế đồng bộ dữ liệu giữa PostgreSQL và Neo4j (file 07).
  5. Kịch bản demo phụ (LOW RISK auto-approve, False Positive) để tránh demo bị thiên lệch (file 10).

Đây là những điểm nhỏ, không ảnh hưởng đến tính khả thi tổng thể của kế hoạch — kế hoạch gốc đã rất chi tiết và có cấu trúc tốt, đây chỉ là các mục cần làm rõ thêm khi đi vào thực thi.
