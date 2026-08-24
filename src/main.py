"""
run_pipeline.py — Chạy toàn bộ pipeline SentinelAI trên dữ liệu thật.

"""
from __future__ import annotations
from pathlib import Path
import sys
# Add the parent directory of this script to sys.path so that we can import src.* modules
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_score,
    recall_score, f1_score,
)
import os
import subprocess
# Set console output to UTF-8 for Vietnamese characters on Windows
if os.name == 'nt':  # Windows
    subprocess.run(['chcp', '65001'], shell=True, capture_output=True)

from src.features.feature_pipeline import extract_features, FEATURE_COLS
from src.anomaly.isolation_forest_detector import IsolationForestAnomalyDetector
from src.risk_engine.aggregator import RiskScoreAggregator
from src.rule_engine.rule_engine import RuleEngine
# Import Investigation Agent for Phase 6
from src.investigation import investigate_transaction, InvestigationAgent

# ----------------------------------------------------------------------
# CẤU HÌNH — sửa ở đây nếu cấu trúc thư mục của bạn khác
# ----------------------------------------------------------------------
DATA_DIR = Path("data/processed/fraud_1m_processed")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

TIME_COL = "timestamp"          # đã xác nhận đúng ở EDA notebook (01)
LABEL_COL = "is_fraud"
TRAIN_FRAC = 0.8                 # 80% đầu (theo thời gian) = train
CALIB_FRAC_OF_VAL = 0.5          # nửa đầu của 20% còn lại = calib, nửa sau = test


# ----------------------------------------------------------------------
# GIAI ĐOẠN 1 — TRAIN
# ----------------------------------------------------------------------
def stage1_train():
    print("=" * 70)
    print("GIAI ĐOẠN 1 — TRAIN")
    print("=" * 70)

    print("\n[1/6] Đọc dữ liệu thật...")
    tx = pd.read_parquet(DATA_DIR / "transactions_clean.parquet")
    edges = pd.read_parquet(DATA_DIR / "network_edges_clean.parquet")
    accounts = pd.read_parquet(DATA_DIR / "account_profiles_clean.parquet")
    print(f"    transactions: {tx.shape}, edges: {edges.shape}, accounts: {accounts.shape}")

    assert TIME_COL in tx.columns, (
        f"Không thấy cột '{TIME_COL}' trong transactions_clean.parquet. "
        f"Các cột có sẵn: {list(tx.columns)}"
    )

    # --- Time-based split (đúng phương pháp đã kiểm chứng ở notebook 03) ---
    print("\n[2/6] Chia train / calib / test theo thời gian...")
    tx_sorted = tx.sort_values(TIME_COL).reset_index(drop=True)
    n = len(tx_sorted)
    train_end = int(n * TRAIN_FRAC)
    val_df = tx_sorted.iloc[train_end:]
    train_raw = tx_sorted.iloc[:train_end]

    calib_end = int(len(val_df) * CALIB_FRAC_OF_VAL)
    calib_raw = val_df.iloc[:calib_end]
    test_raw = val_df.iloc[calib_end:]

    print(f"    Train : {len(train_raw):,} | {train_raw[TIME_COL].min()} -> {train_raw[TIME_COL].max()}")
    print(f"    Calib : {len(calib_raw):,} | {calib_raw[TIME_COL].min()} -> {calib_raw[TIME_COL].max()}")
    print(f"    Test  : {len(test_raw):,} | {test_raw[TIME_COL].min()} -> {test_raw[TIME_COL].max()}")
    print(f"    Fraud rate — train: {train_raw[LABEL_COL].mean()*100:.3f}% "
          f"| calib: {calib_raw[LABEL_COL].mean()*100:.3f}% "
          f"| test: {test_raw[LABEL_COL].mean()*100:.3f}%")

    # --- Feature engineering (mode="train": được phép tự tính acc_stats/median) ---
    print("\n[3/6] Feature engineering (mode='train')...")
    train_feat, acc_stats_train, train_median = extract_features(
        train_raw, edges=edges, accounts=accounts, mode="train"
    )
    X_train = train_feat[FEATURE_COLS]
    y_train = train_feat[LABEL_COL]

    # calib dùng CHUNG acc_stats_train/train_median từ train (mode="infer" ngay từ giai
    # đoạn train để nhất quán tuyệt đối với cách calib/test sẽ được xử lý ở Giai đoạn 2)
    calib_feat, _, _ = extract_features(
        calib_raw, edges=edges, accounts=accounts,
        acc_stats_train=acc_stats_train, train_median=train_median, mode="infer",
    )
    X_calib = calib_feat[FEATURE_COLS]
    y_calib = calib_feat[LABEL_COL]

    # --- Train XGBoost (hyperparameter đã kiểm chứng ở notebook 03) ---
    print("\n[4/6] Train XGBoost...")
    n_pos, n_neg = y_train.sum(), len(y_train) - y_train.sum()
    scale_pos_weight = float(np.sqrt(n_neg / n_pos))
    print(f"    scale_pos_weight (căn bậc 2, đã smooth) = {scale_pos_weight:.3f}")

    xgb = XGBClassifier(
        n_estimators=500, max_depth=4, learning_rate=0.03,
        min_child_weight=10, subsample=0.8, colsample_bytree=0.8,
        reg_alpha=1, reg_lambda=5, scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr", early_stopping_rounds=50,
        random_state=42, n_jobs=-1,
    )
    xgb.fit(X_train, y_train, eval_set=[(X_calib, y_calib)], verbose=False)
    print(f"    Best iteration: {xgb.best_iteration}")

    # --- Calibrate (Sigmoid — giữ nguyên PR-AUC, đã kiểm chứng ở notebook 03) ---
    print("\n[5/6] Calibrate xác suất (Sigmoid, fit trên calib)...")
    try:
        from sklearn.frozen import FrozenEstimator
        cal_xgb = CalibratedClassifierCV(estimator=FrozenEstimator(xgb), method="sigmoid")
    except ImportError:
        cal_xgb = CalibratedClassifierCV(estimator=xgb, method="sigmoid", cv="prefit")
    cal_xgb.fit(X_calib, y_calib)

    # --- Train Isolation Forest ---
    print("\n[6/6] Train Isolation Forest...")
    anomaly_detector = IsolationForestAnomalyDetector(
        n_estimators=200, contamination=float(y_train.mean()), random_state=42,
    )
    anomaly_detector.fit(X_train)

    # --- Tính ngưỡng escalation theo percentile THẬT của train (thay vì đoán 70.0) ---
    # Lý do: giá trị cố định 70.0 đã đánh dấu tới 17-19% giao dịch trong các lần chạy
    # trước — quá lỏng cho một cờ "escalation hiếm gặp". Dùng percentile 98 của phân
    # phối anomaly_score TRÊN TẬP TRAIN (không phải test, tránh leakage) để ngưỡng tự
    # thích nghi đúng ~2% giao dịch bất thường nhất.
    train_anomaly_scores = anomaly_detector.predict_anomaly_score(X_train)
    anomaly_threshold_p98 = float(np.percentile(train_anomaly_scores, 98))
    print(f"    Ngưỡng anomaly (percentile 98 trên train): {anomaly_threshold_p98:.2f} "
          f"(thay cho giá trị cố định 70.0 trước đây)")
    joblib.dump(anomaly_threshold_p98, MODEL_DIR / "anomaly_threshold_p98.pkl")

    # --- Lưu TOÀN BỘ artifact cần cho inference ---
    joblib.dump(cal_xgb, MODEL_DIR / "xgb_calibrated.pkl")
    joblib.dump(acc_stats_train, MODEL_DIR / "acc_stats_train.pkl")
    joblib.dump(train_median, MODEL_DIR / "train_median.pkl")
    anomaly_detector.save(MODEL_DIR / "isolation_forest.pkl")
    # Lưu luôn test_raw để Giai đoạn 2 chấm điểm đúng holdout (không phải chạy lại từ đầu)
    test_raw.to_parquet(MODEL_DIR / "_test_holdout.parquet")
    edges.to_parquet(MODEL_DIR / "_edges_ref.parquet")
    accounts.to_parquet(MODEL_DIR / "_accounts_ref.parquet")

    print(f"\nĐã lưu đầy đủ artifact vào {MODEL_DIR}/")


# ----------------------------------------------------------------------
# GIAI ĐOẠN 2 — INFER trên TEST SET (holdout thật, chưa dùng để fit gì)
# ----------------------------------------------------------------------
def stage2_infer_and_report():
    print("\n" + "=" * 70)
    print("GIAI ĐOẠN 2 — INFER trên TEST SET (mô phỏng process serving thật)")
    print("=" * 70)

    print("\n[1/4] LOAD artifact đã lưu (không tính lại gì)...")
    cal_xgb = joblib.load(MODEL_DIR / "xgb_calibrated.pkl")
    acc_stats_train = joblib.load(MODEL_DIR / "acc_stats_train.pkl")
    train_median = joblib.load(MODEL_DIR / "train_median.pkl")
    anomaly_detector = IsolationForestAnomalyDetector.load(MODEL_DIR / "isolation_forest.pkl")
    anomaly_threshold_p98 = joblib.load(MODEL_DIR / "anomaly_threshold_p98.pkl")
    test_raw = pd.read_parquet(MODEL_DIR / "_test_holdout.parquet")
    edges = pd.read_parquet(MODEL_DIR / "_edges_ref.parquet")
    accounts = pd.read_parquet(MODEL_DIR / "_accounts_ref.parquet")

    print("\n[2/4] Feature engineering (mode='infer' — bắt buộc dùng artifact đã lưu)...")
    test_feat, _, _ = extract_features(
        test_raw, edges=edges, accounts=accounts,
        acc_stats_train=acc_stats_train, train_median=train_median, mode="infer",
    )
    X_test = test_feat[FEATURE_COLS]
    y_test = test_feat[LABEL_COL]

    print("\n[3/4] Tính điểm ML + Anomaly + Rule, tổng hợp Risk Score...")
    ml_prob = cal_xgb.predict_proba(X_test)[:, 1]
    anomaly_score = anomaly_detector.predict_anomaly_score(X_test)

    # --- Tính toán Rule Score ---
    rule_engine = RuleEngine(use_variance_threshold=False)
    rule_score = rule_engine.calculate_rule_score(test_feat, accounts=accounts, edges=edges)

    # anomaly_threshold dùng percentile 98 tính từ TRAIN (xem stage1_train), thay cho
    # giá trị cố định 70.0 trước đây (đã đánh dấu tới 17-19% giao dịch — quá lỏng).
    # Tách Rule Score và Anomaly Score ra khỏi Risk Score: chỉ giữ ML Score trong Risk Score.
    aggregator = RiskScoreAggregator(
        weight_ml=1.00, weight_anomaly=0.0, weight_rule=0.0,
        anomaly_threshold=anomaly_threshold_p98,
    )
    risk_score = aggregator.calculate_risk_score(ml_prob=ml_prob, anomaly_score=anomaly_score, rule_score=rule_score)
    tiers = [aggregator.get_risk_tier(r)["level"] for r in risk_score]

    # --- Phát hiện anomaly mới (novel) làm cờ escalation riêng biệt ---
    novel_anomaly_flag = aggregator.flag_novel_anomaly(anomaly_score)
    novel_count = int(novel_anomaly_flag.sum()) if hasattr(novel_anomaly_flag, 'sum') else (1 if novel_anomaly_flag else 0)
    fraud_rate_novel = y_test[novel_anomaly_flag].mean() if hasattr(novel_anomaly_flag, '__len__') and len(novel_anomaly_flag) > 0 and novel_anomaly_flag.any() else 0.0

    print(f"\n    Anomaly Score (Isolation Forest) làm cờ escalation (ngưỡng {aggregator.anomaly_threshold}):")
    print(f"    Số giao dịch được đánh dấu là anomaly mới: {novel_count:,} / {len(y_test):,} ({novel_count/len(y_test)*100:.2f}%)")
    print(f"    Tỷ lệ gian lận trong các anomaly mới: {fraud_rate_novel*100:.2f}%")

    # --- Phát hiện rule violation cực đoan làm cờ escalation riêng biệt ---
    extreme_rule_flag = aggregator.flag_extreme_rule(rule_score, threshold=80.0)
    extreme_rule_count = int(extreme_rule_flag.sum()) if hasattr(extreme_rule_flag, 'sum') else (1 if extreme_rule_flag else 0)
    fraud_rate_extreme_rule = y_test[extreme_rule_flag].mean() if hasattr(extreme_rule_flag, '__len__') and len(extreme_rule_flag) > 0 and extreme_rule_flag.any() else 0.0

    print(f"\n    Rule Score làm cờ escalation cho violation cực đoan (ngưỡng 80.0):")
    print(f"    Số giao dịch được đánh dấu là rule violation cực đoan: {extreme_rule_count:,} / {len(y_test):,} ({extreme_rule_count/len(y_test)*100:.2f}%)")
    print(f"    Tỷ lệ gian lận trong các rule violation cực đoan: {fraud_rate_extreme_rule*100:.2f}%")

    # --- Thống kê Rule Score ---
    print(f"\n    Rule Score statistics:")
    print(f"    Rule Score trung bình: {np.mean(rule_score):.2f}")
    print(f"    Rule Score min/max: {np.min(rule_score):.2f} / {np.max(rule_score):.2f}")
    print(f"    Rule Score > 50: {(rule_score > 50).sum()} giao dịch ({(rule_score > 50).sum()/len(rule_score)*100:.1f}%)")

    print("\n[4/4] Báo cáo kết quả trên TEST SET (holdout thật)...")
    roc_auc = roc_auc_score(y_test, ml_prob)
    pr_auc = average_precision_score(y_test, ml_prob)
    y_pred_05 = (ml_prob >= 0.5).astype(int)
    print(f"\n    ML Score (đã calibrate) — ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f}")
    print(f"    Precision@0.5: {precision_score(y_test, y_pred_05):.4f} | "
          f"Recall@0.5: {recall_score(y_test, y_pred_05):.4f} | "
          f"F1@0.5: {f1_score(y_test, y_pred_05):.4f}")

    # --- Kiểm tra dứt điểm: risk_score (đã trộn theo trọng số hiện tại: ML/Anomaly/Rule)
    # có tệ hơn ml_prob thuần không, TRÊN CHÍNH test set thật này. ---
    pr_auc_risk = average_precision_score(y_test, risk_score)
    roc_auc_risk = roc_auc_score(y_test, risk_score)
    delta_pr = pr_auc_risk - pr_auc
    print(f"\n    So sánh risk_score (w_ml={aggregator.w_ml:.2f}, w_anom={aggregator.w_anom:.2f}, "
          f"w_rule={aggregator.w_rule:.2f}) vs ml_prob thuần:")
    print(f"    risk_score  — ROC-AUC: {roc_auc_risk:.4f} | PR-AUC: {pr_auc_risk:.4f}")
    print(f"    Chênh lệch PR-AUC (risk_score - ml_prob): {delta_pr:+.4f} "
          f"{'(risk_score TỆ HƠN)' if delta_pr < -0.005 else '(khác biệt không đáng kể)' if abs(delta_pr) <= 0.005 else '(risk_score TỐT HƠN)'}")

    # --- CHẨN ĐOÁN: nếu delta gần bằng 0 tuyệt đối, kiểm tra NGAY xem có bug không,
    # thay vì đoán mò. In đủ 3 thứ: (1) rule_score có biến thiên thật không,
    # (2) rule_score có tương quan quá cao với ml_prob không (redundant signal),
    # (3) có bao nhiêu % risk_score bị np.clip kẹp đúng biên 0/100 (gây trùng hạng
    # hàng loạt, có thể làm AUC trông "giống hệt" dù không phải do trùng giá trị). ---
    print(f"\n    --- Chẩn đoán Rule Score (để xác định vì sao chênh lệch = {delta_pr:+.4f}) ---")
    rule_score_arr = np.asarray(rule_score, dtype=float)
    print(f"    Rule Score — mean: {rule_score_arr.mean():.4f} | std: {rule_score_arr.std():.4f} "
          f"| min: {rule_score_arr.min():.4f} | max: {rule_score_arr.max():.4f}")
    if rule_score_arr.std() < 1e-6:
        print("    ⚠️ Rule Score GẦN NHƯ HẰNG SỐ (std ~ 0) -> ĐÂY LÀ BUG, kiểm tra lại "
              "RuleEngine hoặc các cột input nó cần (velocity_1h, ip_risk_score, "
              "amount_vs_avg_ratio, is_foreign_txn, device_known, n_shared_types, "
              "avg_velocity, time_since_last_s) có tồn tại & không toàn NaN trong test_feat không.")
    corr_pearson = float(np.corrcoef(rule_score_arr, ml_prob)[0, 1])
    corr_spearman = float(pd.Series(rule_score_arr).corr(pd.Series(ml_prob), method="spearman"))
    print(f"    Tương quan Rule Score vs ML Prob — Pearson: {corr_pearson:.4f} | Spearman: {corr_spearman:.4f}")
    if corr_spearman > 0.90:
        print("    ⚠️ Tương quan RẤT CAO (>0.90) -> Rule Score gần như là bản sao thứ hạng của "
              "ML Prob, giải thích vì sao trộn vào không đổi AUC. Không phải bug, nhưng Rule "
              "Score hiện KHÔNG bổ sung thông tin độc lập nào.")
    n_clipped_100 = int((np.asarray(risk_score) >= 99.999).sum())
    n_clipped_0 = int((np.asarray(risk_score) <= 0.001).sum())
    print(f"    Số giao dịch risk_score bị kẹp ở biên: ~100 -> {n_clipped_100:,} "
          f"({n_clipped_100/len(risk_score)*100:.2f}%) | ~0 -> {n_clipped_0:,} "
          f"({n_clipped_0/len(risk_score)*100:.2f}%)")
    if n_clipped_100 / len(risk_score) > 0.05:
        print("    ⚠️ Hơn 5% giao dịch bị kẹp ở biên 100 -> nhiều khả năng gây trùng hạng "
              "(tied ranks) hàng loạt, làm biến dạng ROC-AUC/PR-AUC. Cân nhắc bỏ np.clip "
              "khi ĐÁNH GIÁ metric (chỉ clip khi HIỂN THỊ cho người dùng cuối).")

    # --- GIAI ĐOẠN 6: AI INVESTIGATION AGENT ---
    # Phân tích sâu các giao dịch có nguy cơ cao để tạo báo cáo chi tiết
    print("\n[5/5] GIAI ĐOẠN 6 — AI INVESTIGATION AGENT (Phase 6)")
    print("    Phân tích sâu các giao dịch HIGH RISK và MEDIUM RISK...")

    # Khởi tạo Investigation Agent
    investigation_agent = InvestigationAgent()

    # Danh sách lưu trữ kết quả điều tra
    investigation_results = []

    # Xác định các giao dịch cần điều tra (HIGH RISK và MEDIUM RISK)
    high_risk_mask = np.array(tiers) == "HIGH RISK"
    medium_risk_mask = np.array(tiers) == "MEDIUM RISK"
    investigate_mask = high_risk_mask | medium_risk_mask  # Điều tra cả HIGH và MEDIUM risk

    if investigate_mask.any():
        investigate_indices = np.where(investigate_mask)[0]
        print(f"    Tìm thấy {len(investigate_indices)} giao dịch cần điều tra "
              f"(HIGH RISK: {high_risk_mask.sum()}, MEDIUM RISK: {medium_risk_mask.sum()})")

        # Giới hạn số lượng giao dịch điều tra để tránh quá tải (ví dụ: tối đa 20 giao dịch)
        max_investigations = min(20, len(investigate_indices))
        if len(investigate_indices) > max_investigations:
            print(f"    Giới hạn điều tra tối đa {max_investigations} giao dịch "
                  f"(chọn dựa trên risk_score cao nhất)")
            # Chọn các giao dịch có risk_score cao nhất để điều tra
            investigate_indices = investigate_indices[np.argsort(-risk_score[investigate_indices])[:max_investigations]]

        # Thực hiện điều tra cho từng giao dịch được chọn
        for idx in investigate_indices:
            # Lấy dữ liệu giao dịch từ test_feat
            transaction_data = test_feat.iloc[idx]

            # Lấy thông tin tài khoản và mạng lưới nếu cần
            account_id = transaction_data.get('account_id', 'UNKNOWN')

            # Thực hiện điều tra
            try:
                investigation_result = investigate_transaction(
                    transaction_data=transaction_data,
                    accounts_data=accounts,  # Đã tải ở trên
                    edges_data=edges         # Đã tải ở trên
                )

                # Thêm thông tin giao dịch vào kết quả điều tra
                investigation_result['transaction_index'] = int(idx)
                investigation_result['original_risk_score'] = float(risk_score[idx])
                investigation_result['original_tier'] = tiers[idx]
                investigation_result['ml_prob'] = float(ml_prob[idx])

                investigation_results.append(investigation_result)

                # In tiến độ
                if len(investigation_results) % 5 == 0:
                    print(f"    Đã hoàn thành {len(investigation_results)}/{max_investigations} cuộc điều tra...")

            except Exception as e:
                print(f"    Cảnh báo: Không thể điều tra giao dịch index {idx}: {e}")
                continue

        print(f"    Hoàn thành {len(investigation_results)} cuộc điều tra chi tiết")

        # Lưu kết quả điều tra
        if investigation_results:
            # Tóm tắt các trường hợp điều tra
            investigation_summary = {
                'total_investigations': len(investigation_results),
                'high_risk_investigations': sum(1 for r in investigation_results
                                              if r.get('investigation_summary', {}).get('risk_tier') == 'HIGH RISK'),
                'medium_risk_investigations': sum(1 for r in investigation_results
                                                if r.get('investigation_summary', {}).get('risk_tier') == 'MEDIUM RISK'),
                'avg_investigation_confidence': np.mean([r.get('confidence_score', 0)
                                                       for r in investigation_results]) if investigation_results else 0,
                'investigations': investigation_results
            }

            # Lưu kết quả điều tra
            import json
            import datetime
            investigation_file = MODEL_DIR / f"investigation_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(investigation_file, 'w', encoding='utf-8') as f:
                json.dump(investigation_summary, f, ensure_ascii=False, indent=2, default=str)

            print(f"    Đã lưu kết quả điều tra chi tiết -> {investigation_file}")

            # Hiển thị tóm tắt một vài trường hợp điều tra nổi bật
            print(f"\n    TÓM TẮT MỘT SỐ TRƯỜNG HỢP ĐIỀU TRA NỔI BẬT:")
            for i, inv_result in enumerate(investigation_results[:3]):  # Hiển thị 3 trường hợp đầu tiên
                tx_id = inv_result.get('transaction_id', f'TX_{inv_result.get("transaction_index", "UNKNOWN")}')
                action = inv_result.get('recommended_action', 'N/A')
                confidence = inv_result.get('confidence_score', 0)
                risk_tier = inv_result.get('investigation_summary', {}).get('risk_tier', 'N/A')
                print(f"    {i+1}. Giao dịch {tx_id}:")
                print(f"       - Mức rủi ro gốc: {inv_result.get('original_tier', 'N/A')} "
                      f"(score: {inv_result.get('original_risk_score', 0):.1f})")
                print(f"       - Kết luận điều tra: {risk_tier}")
                print(f"       - Hành động đề xuất: {action}")
                print(f"       - Mức độ tin cậy: {confidence:.1%}")
                print()
    else:
        print("    Không có giao dịch HIGH RISK hoặc MEDIUM RISK để điều tra.")

    result = test_feat[["account_id", LABEL_COL]].copy()
    result["ml_prob"] = ml_prob.round(4)
    result["anomaly_score"] = anomaly_score.round(2)
    result["risk_score"] = risk_score.round(2)
    result["tier"] = tiers

    print("\n    Phân bố tier trên test set:")
    tier_summary = (
        result.groupby("tier")
        .agg(so_giao_dich=("tier", "size"), so_fraud=(LABEL_COL, "sum"))
        .assign(ty_le_fraud_pct=lambda d: (d["so_fraud"] / d["so_giao_dich"] * 100).round(2))
    )
    print(tier_summary.to_string())

    result.to_parquet(MODEL_DIR / "scored_test_results.parquet")
    print(f"\nĐã lưu kết quả chấm điểm chi tiết -> {MODEL_DIR / 'scored_test_results.parquet'}")

    return result


if __name__ == "__main__":
    stage1_train()
    stage2_infer_and_report()
    print("\n" + "=" * 70)
    print("HOÀN TẤT PIPELINE.")
    print("=" * 70)