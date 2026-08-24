# -*- coding: utf-8 -*-
"""
Module tổng hợp điểm rủi ro (Risk Engine / Score Aggregator)
Kết hợp ML Score, Anomaly Score và Rule Score thành Risk Score tổng thể (0 - 100).
"""

from typing import Dict, Any, Union
import numpy as np
import pandas as pd


class RiskScoreAggregator:
    """
    Bộ tổng hợp điểm rủi ro đa nguồn của SentinelAI.
    Công thức:
        Risk Score = w_ml * ML_Score + w_anom * Anomaly_Score + w_rule * Rule_Score
    """

    def __init__(
        self,
        weight_ml: float = 1.00,
        weight_anomaly: float = 0.00,
        weight_rule: float = 0.00,
        anomaly_threshold: float = 70.0
    ):
        """
        Mặc định weight_anomaly=0.0 — ĐÃ ĐỔI so với bản đầu (0.30).

        Lý do: kiểm chứng độc lập 2 lần (validation set ở notebook 04, và
        test set 100K giao dịch thật ở run_pipeline.py) đều cho cùng kết
        luận: trộn tuyến tính Anomaly Score vào Risk Score làm PR-AUC
        GIẢM (lần lượt -0.0342 và tương tự ở lần đo trước), không tăng.
        Nguyên nhân: Isolation Forest phát hiện được rất ít fraud mà XGBoost
        chưa biết (quadrant Q2 chỉ ~68/2427 case là fraud thật), nên phần
        đóng góp chủ yếu là nhiễu pha loãng một score ML vốn đã tốt.

        Anomaly Score VẪN CÓ GIÁ TRỊ — nhưng nên dùng qua `flag_novel_anomaly()`
        (cờ escalation riêng biệt, xem bên dưới) thay vì cộng thẳng vào
        Risk Score chính. Nếu sau này có Rule Score được kiểm
        chứng thực sự cải thiện PR-AUC, hãy set weight tương ứng > 0 dựa
        trên bằng chứng, đừng dùng số minh họa trong tài liệu thiết kế ban đầu.

        anomaly_threshold: ngưỡng (0-100) để xác định anomaly mới (novel) kích hoạt cờ.
        """
        total_w = weight_ml + weight_anomaly + weight_rule
        if not np.isclose(total_w, 1.0):
            # Tự động chuẩn hóa tổng trọng số về 1.0
            weight_ml /= total_w
            weight_anomaly /= total_w
            weight_rule /= total_w

        self.w_ml = weight_ml
        self.w_anom = weight_anomaly
        self.w_rule = weight_rule
        self.anomaly_threshold = anomaly_threshold

    def calculate_risk_score(
        self,
        ml_prob: Union[float, np.ndarray, pd.Series],
        anomaly_score: Union[float, np.ndarray, pd.Series],
        rule_score: Union[float, np.ndarray, pd.Series] = 0.0
    ) -> Union[float, np.ndarray, pd.Series]:
        """
        Tính toán điểm Risk Score từ 0 đến 100.

        Args:
            ml_prob: Xác suất gian lận từ mô hình Supervised, BẮT BUỘC trong [0.0, 1.0].
            anomaly_score: Điểm dị biệt từ Anomaly Detector, BẮT BUỘC trong [0.0, 100.0].
            rule_score: Điểm vi phạm từ Rule Engine (0.0 - 100.0).

        Returns:
            Risk Score trong khoảng [0, 100].

        Raises:
            ValueError: nếu ml_prob hoặc anomaly_score nằm ngoài thang đo quy estimés.

        Lưu ý thiết kế: bản trước dùng heuristic `np.max(x) <= 1.0` để TỰ ĐOÁN xem input
        đang ở thang 0-1 hay 0-100. Đây là cách làm RỦI RO: một mảng anomaly_score toàn
        giá trị thấp (ví dụ mọi giao dịch đều an toàn, anomaly_score trong khoảng
        0.0-0.9 trên thang 0-100) sẽ bị hiểu NHẦM là thang 0-1 và nhân 100 lần nữa,
        rồi bị `np.clip` che giấu triệu chứng (giá trị sai bị kẹp về 100 trong im lặng,
        không có cảnh báo nào). Thay vào đó, ta BẮT BUỘC input đúng quy ước đã tài liệu
        hóa và raise lỗi rõ ràng nếu sai, thay vì đoán.
        """
        ml_arr = np.asarray(ml_prob, dtype=float)
        anom_arr = np.asarray(anomaly_score, dtype=float)

        if np.any((ml_arr < 0.0) | (ml_arr > 1.0)):
            raise ValueError(
                "ml_prob phải nằm trong [0.0, 1.0] (xác suất). "
                f"Giá trị nhận được có min={ml_arr.min():.4f}, max={ml_arr.max():.4f}. "
                "Nếu bạn đang truyền điểm đã nhân 100, hãy chia lại cho 100 trước khi gọi hàm này."
            )
        if np.any((anom_arr < 0.0) | (anom_arr > 100.0)):
            raise ValueError(
                "anomaly_score phải nằm trong [0.0, 100.0]. "
                f"Giá trị nhận được có min={anom_arr.min():.4f}, max={anom_arr.max():.4f}."
            )

        ml_score_100 = ml_arr * 100.0

        risk = (
            self.w_ml * ml_score_100 +
            self.w_anom * anom_arr +
            self.w_rule * rule_score
        )
        return np.clip(risk, 0.0, 100.0)

    def flag_novel_anomaly(
        self,
        anomaly_score: Union[float, np.ndarray, pd.Series]
    ) -> Union[bool, np.ndarray, pd.Series]:
        """
        Xác định anomaly mới (novel) dựa trên ngưỡng anomaly_threshold.
        Trả về boolean mask/cờ chỉ những giao dịch có anomaly_score >= threshold.

        Args:
            anomaly_score: Điểm dị biệt từ Anomaly Detector, BẮT BUỘC trong [0.0, 100.0].

        Returns:
            Boolean mask cùng shape với anomaly_score chỉ các anomaly mới.

        Raises:
            ValueError: nếu anomaly_score nằm ngoài [0.0, 100.0].
        """
        anom_arr = np.asarray(anomaly_score, dtype=float)

        if np.any((anom_arr < 0.0) | (anom_arr > 100.0)):
            raise ValueError(
                "anomaly_score phải nằm trong [0.0, 100.0]. "
                f"Giá trị nhận được có min={anom_arr.min():.4f}, max={anom_arr.max():.4f}."
            )

        return anom_arr >= self.anomaly_threshold

    def flag_extreme_rule(
        self,
        rule_score: Union[float, np.ndarray, pd.Series],
        threshold: float = 80.0
    ) -> Union[bool, np.ndarray, pd.Series]:
        """
        Flag extreme rule violations based on a threshold.
        Trả về boolean mask/cờ chỉ những giao dịch có rule_score >= threshold.

        Args:
            rule_score: Điểm vi phạm từ Rule Engine, BẮT BUỘC trong [0.0, 100.0].
            threshold: Ngưỡng (0-100) để xác định extreme rule violation. Mặc định là 80.0.

        Returns:
            Boolean mask cùng shape với rule_score chỉ các extreme rule violations.

        Raises:
            ValueError: nếu rule_score nằm ngoài [0.0, 100.0].
        """
        rule_arr = np.asarray(rule_score, dtype=float)

        if np.any((rule_arr < 0.0) | (rule_arr > 100.0)):
            raise ValueError(
                "rule_score phải nằm trong [0.0, 100.0]. "
                f"Giá trị nhận được có min={rule_arr.min():.4f}, max={rule_arr.max():.4f}."
            )

        return rule_arr >= threshold

    @staticmethod
    def get_risk_tier(risk_score: float) -> Dict[str, Any]:
        """
        Phân luồng hành động dựa trên ngưỡng Risk Score (theo chuẩn SentinelAI).
        
        Tầng 1: Risk < 30   -> LOW RISK (Automatically Approve)
        Tầng 2: 30 <= Risk < 70 -> MEDIUM RISK (Additional Verification / Step-up 2FA)
        Tầng 3: Risk >= 70  -> HIGH RISK (AI Investigation + Human Review)
        """
        if risk_score < 30.0:
            return {
                "level": "LOW",
                "action": "AUTO_APPROVE",
                "color": "green",
                "description": "Giao dịch an toàn. Tự động phê duyệt."
            }
        elif risk_score < 70.0:
            return {
                "level": "MEDIUM",
                "action": "ADDITIONAL_VERIFICATION",
                "color": "yellow",
                "description": "Giao dịch có dấu hiệu bất thường. Yêu cầu xác thực bổ sung (OTP/2FA)."
            }
        else:
            return {
                "level": "HIGH",
                "action": "AI_INVESTIGATION_HUMAN_REVIEW",
                "color": "red",
                "description": "Giao dịch rủi ro cao. Kích hoạt AI Agent điều tra và chuyển Human Review."
            }   