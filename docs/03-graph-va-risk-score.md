# 03 — Graph-based Fraud Detection & Risk Aggregation
## 9. Graph-based Fraud Detection

Đây là một trong những phần quan trọng nhất của SentinelAI.

### Graph

```text
User
 │
 ├── Device
 │
 ├── IP
 │
 ├── Bank Account
 │
 └── Merchant
```

Ví dụ:

```text
User A ─────┐
            │
User B ─────┼── Device X ─── IP Y
            │
User C ─────┘
```

Nếu nhiều user khác nhau cùng sử dụng:

```text
Device X
IP Y
Bank Account Z
```

→ có thể là một fraud ring.

### Công nghệ

Có thể sử dụng:

```text
NetworkX
```

cho prototype và:

```text
Neo4j
```

cho phiên bản production-like.

---

## 10. Risk Aggregation

Không nên quyết định fraud chỉ dựa vào một model.

Tạo Risk Score tổng hợp:

```text
Risk Score =
    ML Score
  + Anomaly Score
  + Rule Score
  + Graph Score
```

Có thể chuẩn hóa về:

```text
0 → 100
```

Ví dụ:

```text
0 - 30
LOW RISK
→ Automatically Approve

30 - 70
MEDIUM RISK
→ Additional Verification

70 - 100
HIGH RISK
→ AI Investigation + Human Review
```

Các threshold cần được benchmark và điều chỉnh dựa trên validation data.

---

## Nhận xét / Phân tích

- Graph-based detection là phần **khó nhất về mặt kỹ thuật** nhưng cũng là phần tạo giá trị khác biệt lớn nhất, vì fraud ring (nhiều tài khoản chia sẻ chung thiết bị/IP) gần như không thể phát hiện bằng ML tabular đơn lẻ trên từng giao dịch riêng lẻ.
- Việc dùng NetworkX cho prototype rồi chuyển sang Neo4j cho bản gần production là lộ trình hợp lý, nhưng cần lưu ý: mô hình dữ liệu (schema) nên được thiết kế thống nhất ngay từ đầu (xem thêm [Database Design](./07-database-va-api.md)) để việc chuyển đổi giữa hai công cụ không phải viết lại logic truy vấn.
- Công thức `Risk Score = ML + Anomaly + Rule + Graph` được trình bày dạng cộng đơn giản; trong thực tế nên làm rõ thêm:
  - Trọng số (weight) cho từng thành phần — có thể không bằng nhau.
  - Cách chuẩn hóa từng score con về cùng thang đo trước khi cộng (ví dụ min-max hoặc sigmoid).
  - Đây là chi tiết kỹ thuật quan trọng nên được thêm vào roadmap Phase 5 khi triển khai thực tế.
- Threshold 30/70 là điểm khởi đầu hợp lý, nhưng tài liệu đã đúng khi nhấn mạnh cần benchmark trên validation data — với dữ liệu fraud vốn mất cân bằng, threshold cố định dễ gây quá nhiều false positive hoặc bỏ sót fraud nếu không hiệu chỉnh theo phân phối thực tế.
