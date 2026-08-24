# 03 — Graph-based Fraud Detection & Risk Aggregation

> Xem [README.md](./README.md) để có mục lục đầy đủ. **Mục 10 đã được viết
> lại** dựa trên kết quả kiểm chứng thực nghiệm — xem
> [01-kien-truc-tong-the.md](./01-kien-truc-tong-the.md) mục "Lịch sử thay
> đổi" để biết toàn cảnh.

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

> **Cập nhật:** Graph pipeline (`graph_analysis.py`,
> `graph_score.py`, Neo4j ingest) đã được xây dựng đầy đủ ở Phase 4. Tuy
> nhiên, kết quả Graph **không được dùng như một "Graph Score" độc lập
> cộng vào Risk Score** như dự kiến ban đầu — xem mục 10 bên dưới để biết
> lý do và cách Graph thực sự được sử dụng trong hệ thống hiện tại.

---

## 10. Risk Aggregation

> ⚠️ **Phần này đã được viết lại.** Công thức gốc dưới đây từng được đề
> xuất trong bản thiết kế ban đầu, nhưng đã được **kiểm chứng bằng số
> liệu thật và không giữ nguyên**:
>
> ```text
> Risk Score = ML Score + Anomaly Score + Rule Score + Graph Score
> ```
>
> Xem phần "Vì sao công thức trên bị thay đổi" ngay dưới đây để hiểu quá
> trình dẫn đến kiến trúc hiện tại.

### Vì sao công thức trộn 4 nguồn bị thay đổi

Ý tưởng ban đầu (cộng 4 điểm số theo trọng số, ví dụ 40/30/20/10 hoặc bất
kỳ tỷ lệ minh họa nào) là hợp lý *về mặt trực giác*, nhưng khi đo bằng
PR-AUC trên dữ liệu thật (1M giao dịch, tách theo thời gian đúng chuẩn),
kết quả cho thấy:

| Cách kết hợp | PR-AUC | So với ML một mình |
|---|---|---|
| Chỉ ML Score | 0.8468 | (baseline) |
| ML + Anomaly Score (30%) | 0.8126 | **-0.0342** |
| ML + Rule Score (30%) | 0.8089 | **-0.0379** |

**Cả 2 lần trộn đều làm hệ thống TỆ HƠN**, không tốt hơn như giả định ban
đầu. Lý do khác nhau cho từng nguồn:

- **Anomaly Score** (Isolation Forest): tín hiệu **độc lập thật** với ML,
  nhưng **quá yếu** — trong nhóm giao dịch được Anomaly gắn cờ mà ML bỏ
  sót, chỉ ~2.8-4.5% thực sự là fraud. Phần lớn là nhiễu.
- **Rule Score**: **không yếu**, nhưng **không độc lập theo đúng nghĩa
  hữu ích** — nó được tính từ chính những feature thô (`velocity_1h`,
  `ip_risk_score`...) mà XGBoost đã học cách kết hợp tối ưu. Rule Engine
  dùng trọng số cố định, đoán tay (0.4/0.3/0.3...) cho cùng loại thông
  tin đó — về bản chất là "bản sao kém hơn", trộn vào chỉ pha loãng bản
  gốc đã tốt hơn.

### Kiến trúc Risk Score hiện tại (đã kiểm chứng)

```text
Risk Score (0-100) = 1.0 × ML Score

Anomaly Score và Rule Score KHÔNG cộng vào công thức trên.
Thay vào đó, chúng sinh ra 2 CỜ ESCALATION độc lập:

    flag_novel_anomaly()   — True nếu Anomaly Score ≥ ngưỡng cao
                              (percentile 98 trên tập train, KHÔNG
                              phải số cố định đoán tay)
    flag_extreme_rule()    — True nếu Rule Score ≥ ngưỡng cao

Quyết định cuối cùng = Risk Tier (từ Risk Score) 
                        VÀ/HOẶC ép escalate nếu bất kỳ cờ nào bật lên,
                        dù Risk Score gốc đang ở tầng LOW/MEDIUM.
```

Cách này giữ được **cả 2 lợi ích**: (1) Risk Score chính vẫn chính xác
nhất có thể (không bị pha loãng), và (2) không bỏ phí Anomaly/Rule —
chúng vẫn bắt được nhóm case hiếm mà ML bỏ sót, chỉ là bắt theo cơ chế
"cờ báo động", không phải "cộng điểm".

### Ngưỡng phân tầng (risk thresholds)

```text
Risk Score < 30
LOW RISK
→ Automatically Approve

30 ≤ Risk Score < 70
MEDIUM RISK
→ Additional Verification (OTP/2FA)

Risk Score ≥ 70
HIGH RISK
→ AI Investigation + Human Review

BẤT KỂ risk tier nào ở trên: nếu flag_novel_anomaly() hoặc
flag_extreme_rule() = True → ép escalate lên ít nhất MEDIUM,
hoặc thẳng lên HIGH tùy mức độ nghiêm trọng của cờ.
```

Ngưỡng 30/70 và ngưỡng percentile 98 cho 2 cờ đều đã được benchmark
trên tập test 100K giao dịch thật (không phải số minh họa) — xem
[10-danh-gia-va-demo.md](./10-danh-gia-va-demo.md) để có ví dụ walkthrough
đầy đủ với số liệu cụ thể.

### Vai trò của Graph trong kiến trúc hiện tại

Graph **không có "Graph Score" riêng** trong công thức trên. Thay vào
đó, thông tin đồ thị (`in_ring`, `account_degree`, `n_shared_types`) đã
được **Feature Engine (mục 5) nhúng thẳng vào bộ feature của ML Model**
— nghĩa là Graph vẫn ảnh hưởng đến Risk Score, chỉ là gián tiếp qua
`ml_prob`, không phải một nhánh cộng điểm độc lập.

`graph_score.py` (Phase 4, kỹ thuật leave-one-out chống leakage) vẫn tồn
tại và có thể tái sử dụng làm cờ escalation thứ 3 (giống Anomaly/Rules)
nếu sau này muốn — nhưng **cần kiểm chứng bằng số liệu thật trước**,
theo đúng quy trình đã áp dụng cho Anomaly và Rule, tránh lặp lại giả
định chưa kiểm chứng.
