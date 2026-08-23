# -*- coding: utf-8 -*-
"""
Module trích xuất và biến đổi đặc trưng (Feature Engineering Pipeline)
Dùng chung cho cả quá trình Huấn luyện (Training) và Dự đoán (Inference / Serving).
"""

from typing import List, Tuple, Optional
import numpy as np
import pandas as pd


# Danh sách 24 đặc trưng chuẩn của SentinelAI
FEATURE_COLS: List[str] = [
    # Nhóm 1: Hành vi giao dịch
    "velocity_1h",
    "velocity_high",
    "amount",
    "amount_log",
    "amount_vs_avg_ratio",
    "amount_ratio_high",
    "time_since_last_s",
    "ip_risk_score",
    "ip_risk_high",
    
    # Nhóm 2: Thời gian
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_night",
    
    # Nhóm 3: Thiết bị và cờ bảo mật
    "is_foreign_txn",
    "card_present",
    "device_known",
    "has_2fa",
    
    # Nhóm 4: Hồ sơ tài khoản tĩnh
    "account_age_days",
    "credit_limit",
    
    # Nhóm 5: Đồ thị quan hệ (Graph features)
    "in_ring",
    "account_degree",
    "n_shared_types",
    
    # Nhóm 6: Lịch sử hành vi an toàn theo thời gian
    "avg_velocity",
    "pct_foreign",
]


def extract_features(
    tx: pd.DataFrame,
    edges: Optional[pd.DataFrame] = None,
    accounts: Optional[pd.DataFrame] = None,
    acc_stats_train: Optional[pd.DataFrame] = None,
    train_median: Optional[pd.Series] = None,
    mode: str = "train"
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """
    Hàm tạo và chuẩn hóa toàn bộ 24 đặc trưng từ dữ liệu giao dịch, graph và account profiles.

    Args:
        tx: DataFrame giao dịch (transactions).
        edges: DataFrame đồ thị liên kết (network edges).
        accounts: DataFrame hồ sơ tài khoản (account profiles).
        acc_stats_train: Bảng thống kê avg_velocity & pct_foreign từ tập train (ngăn ngừa leakage).
        train_median: Giá trị median từ tập train dùng để điền khuyết (fillna).
        mode: "train" hoặc "infer".
            - "train": nếu acc_stats_train/train_median = None, TỰ TÍNH từ `tx` truyền vào
              (đúng và cần thiết khi đang huấn luyện lần đầu).
            - "infer": BẮT BUỘC phải truyền acc_stats_train và train_median đã lưu từ lúc
              training (joblib.load từ artifact). Hàm sẽ raise lỗi thay vì tự tính, vì tự
              tính từ dữ liệu inference là một dạng leakage nguy hiểm:
              (1) nếu tx là 1 giao dịch đơn lẻ đang cần chấm điểm real-time, nhóm theo
                  account_id chỉ có đúng 1 dòng -> avg_velocity sẽ bằng chính velocity_1h
                  của giao dịch đó (tự tương quan tuyệt đối, vô nghĩa và rất dễ gây lỗi
                  ngầm không ai biết);
              (2) nếu tx là một batch giao dịch mới, thống kê tính ra sẽ dùng cả thông tin
                  "tương lai" trong chính batch đó thay vì lịch sử đã biết trước.

    Returns:
        Tuple chứa: (DataFrame đã tạo feature, DataFrame thống kê account train, Series median train)

    Raises:
        ValueError: nếu mode="infer" mà thiếu acc_stats_train hoặc train_median.
    """
    if mode not in ("train", "infer"):
        raise ValueError(f"mode phải là 'train' hoặc 'infer', nhận được: {mode!r}")

    if mode == "infer" and (acc_stats_train is None or train_median is None):
        raise ValueError(
            "mode='infer' BẮT BUỘC phải truyền acc_stats_train và train_median đã lưu "
            "từ lúc training (ví dụ joblib.load('models/anomaly_artifact_full.pkl')). "
            "Không được để None ở serving/production — xem docstring để biết lý do."
        )
    tx = tx.copy()
    
    # 1. Feature từ thời gian và ngưỡng cờ
    if "hour_of_day" in tx.columns:
        tx["is_night"] = tx["hour_of_day"].isin([0, 1, 2, 3, 4, 5]).astype("int8")
    if "velocity_1h" in tx.columns:
        tx["velocity_high"] = (tx["velocity_1h"] >= 5).astype("int8")
    if "ip_risk_score" in tx.columns:
        tx["ip_risk_high"] = (tx["ip_risk_score"] >= 50).astype("int8")
    if "amount_vs_avg_ratio" in tx.columns:
        tx["amount_ratio_high"] = (tx["amount_vs_avg_ratio"] >= 5).astype("int8")
    if "amount" in tx.columns:
        tx["amount_log"] = np.log1p(tx["amount"].clip(lower=0))

    # 2. Feature từ đồ thị liên kết (Graph)
    if edges is not None:
        # 2.1 in_ring: Tài khoản có nằm trong vòng xoáy gian lận (Fraud Ring) không
        ring_edges = edges.dropna(subset=["ring_id"]) if "ring_id" in edges.columns else edges
        ring_accounts = set(ring_edges["account_a"]).union(set(ring_edges["account_b"]))
        tx["in_ring"] = tx["account_id"].isin(ring_accounts).astype("int8")

        # 2.2 account_degree: Số lượng liên kết của tài khoản
        degree = pd.concat([edges["account_a"], edges["account_b"]]).value_counts()
        tx["account_degree"] = tx["account_id"].map(degree).fillna(0).astype("int16")

        # 2.3 n_shared_types: Số lượng loại thực thể chia sẻ (device, IP, card, v.v.)
        if "shared_type" in edges.columns:
            shared_a = edges.groupby("account_a")["shared_type"].nunique()
            shared_b = edges.groupby("account_b")["shared_type"].nunique()
            shared_counts = shared_a.add(shared_b, fill_value=0).astype(int)
            tx["n_shared_types"] = tx["account_id"].map(shared_counts).fillna(0).astype("int8")
    else:
        for col in ["in_ring", "account_degree", "n_shared_types"]:
            if col not in tx.columns:
                tx[col] = 0

    # 3. Join thông tin tĩnh từ account profiles
    if accounts is not None:
        profile_cols = ["account_id", "risk_score", "is_high_risk", "fraud_rate", "is_fraudster", "avg_amount"]
        profile_cols = [c for c in profile_cols if c in accounts.columns]
        tx = tx.merge(accounts[profile_cols], on="account_id", how="left", suffixes=("", "_profile"))

    # 4. Tính toán avg_velocity & pct_foreign an toàn theo thời gian (chống data leakage)
    # CHỈ tự tính khi mode="train" (đã kiểm tra và raise lỗi ở đầu hàm nếu mode="infer"
    # mà thiếu acc_stats_train — xem docstring).
    if acc_stats_train is None:
        acc_stats_train = tx.groupby("account_id").agg(
            avg_velocity_safe=("velocity_1h", "mean"),
            pct_foreign_safe=("is_foreign_txn", "mean")
        )
    
    fallback_velocity = acc_stats_train["avg_velocity_safe"].median() if not acc_stats_train.empty else 1.0
    fallback_foreign = acc_stats_train["pct_foreign_safe"].median() if not acc_stats_train.empty else 0.0

    tx["avg_velocity"] = tx["account_id"].map(acc_stats_train["avg_velocity_safe"]).fillna(fallback_velocity)
    tx["pct_foreign"] = tx["account_id"].map(acc_stats_train["pct_foreign_safe"]).fillna(fallback_foreign)

    # 5. Điền khuyết (Imputation) bằng median
    # CHỈ tự tính khi mode="train" (đã raise lỗi ở đầu hàm nếu mode="infer" mà thiếu).
    valid_cols = [c for c in FEATURE_COLS if c in tx.columns]
    if train_median is None:
        train_median = tx[valid_cols].median(numeric_only=True)
    
    tx[valid_cols] = tx[valid_cols].fillna(train_median)

    return tx, acc_stats_train, train_median