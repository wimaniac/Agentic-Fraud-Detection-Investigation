# -*- coding: utf-8 -*-
"""
Module phát hiện giao dịch bất thường (Anomaly Detection) sử dụng thuật toán Isolation Forest.
Cung cấp khả năng huấn luyện, chuẩn hóa điểm dị biệt (Anomaly Score 0 - 100) và phát hiện Outliers.
"""

from typing import Dict, Any, Optional, Union
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib


class IsolationForestAnomalyDetector:
    """
    Bộ phát hiện bất thường dựa trên Isolation Forest cho hệ thống SentinelAI.
    
    Thuật toán cô lập các điểm dị biệt (Outliers) bằng cách xây dựng ngẫu nhiên các cây nhị phân (Isolation Trees).
    Các điểm dữ liệu bất thường (Anomalies) thường nằm ở vùng thưa thớt, cần ít lát cắt để cô lập (độ sâu đường đi ngắn).
    """

    def __init__(
        self,
        n_estimators: int = 200,
        max_samples: Union[int, float, str] = 256,
        contamination: Union[float, str] = 0.017,
        random_state: int = 42,
        n_jobs: int = -1
    ):
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.random_state = random_state
        self.n_jobs = n_jobs
        
        self.model: Optional[IsolationForest] = None
        self.score_params: Dict[str, float] = {}
        self.is_fitted: bool = False

    def fit(self, X: pd.DataFrame) -> "IsolationForestAnomalyDetector":
        """
        Huấn luyện mô hình Isolation Forest trên tập dữ liệu đặc trưng.
        
        Args:
            X: Ma trận đặc trưng huấn luyện (DataFrame hoặc ndarray).
            
        Returns:
            self: Đối tượng đã huấn luyện xong.
        """
        print(f"Bắt đầu huấn luyện Isolation Forest với {len(X):,} mẫu và {X.shape[1]} đặc trưng...")
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=self.n_jobs
        )
        self.model.fit(X)
        
        # Tính toán các tham số chuẩn hóa điểm dị biệt từ tập huấn luyện
        # decision_function: giá trị càng âm -> càng dị biệt
        raw_scores = -self.model.decision_function(X)
        self.score_params = {
            "mean": float(np.mean(raw_scores)),
            "std": float(np.std(raw_scores)) if np.std(raw_scores) > 0 else 1.0,
            "min": float(np.min(raw_scores)),
            "max": float(np.max(raw_scores)),
            "p95": float(np.percentile(raw_scores, 95)),
            "p99": float(np.percentile(raw_scores, 99))
        }
        self.is_fitted = True
        print("Huấn luyện Isolation Forest và tính toán tham số chuẩn hóa thành công!")
        return self

    def predict_raw_score(self, X: pd.DataFrame) -> np.ndarray:
        """
        Tính điểm dị biệt thô (Raw Anomaly Score = -decision_function).
        Giá trị càng lớn -> Giao dịch càng bất thường.
        """
        if not self.is_fitted or self.model is None:
            raise ValueError("Mô hình chưa được huấn luyện. Vui lòng gọi fit() trước!")
        return -self.model.decision_function(X)

    def predict_anomaly_score(self, X: pd.DataFrame, scale_to_100: bool = True) -> np.ndarray:
        """
        Tính toán Anomaly Score đã chuẩn hóa về thang đo [0, 1] hoặc [0, 100].
        Sử dụng hàm Sigmoid Transformation dựa trên phân phối của tập huấn luyện:
            S = 1 / (1 + exp(-(raw_score - mean) / std))
            
        Args:
            X: Dữ liệu giao dịch cần đánh giá.
            scale_to_100: Nếu True trả về thang đo [0, 100], ngược lại trả về [0, 1].
            
        Returns:
            np.ndarray: Điểm dị biệt (Anomaly Score).
        """
        raw_scores = self.predict_raw_score(X)
        mean = self.score_params.get("mean", 0.0)
        std = self.score_params.get("std", 1.0)
        
        # Sigmoid scaling mượt mà
        normalized_scores = 1.0 / (1.0 + np.exp(-(raw_scores - mean) / (std + 1e-8)))
        
        if scale_to_100:
            return np.clip(normalized_scores * 100.0, 0.0, 100.0)
        return np.clip(normalized_scores, 0.0, 1.0)

    def predict_is_outlier(self, X: pd.DataFrame, threshold_score: float = 70.0) -> np.ndarray:
        """
        Dự đoán cờ dị biệt (True nếu Anomaly Score >= threshold).
        """
        scores = self.predict_anomaly_score(X, scale_to_100=True)
        return (scores >= threshold_score).astype(int)

    def save(self, filepath: Union[str, Path]) -> None:
        """Lưu model và tham số chuẩn hóa vào file pickle"""
        data_to_save = {
            "model": self.model,
            "score_params": self.score_params,
            "params": {
                "n_estimators": self.n_estimators,
                "max_samples": self.max_samples,
                "contamination": self.contamination,
                "random_state": self.random_state
            }
        }
        joblib.dump(data_to_save, filepath)
        print(f"Đã lưu mô hình Anomaly Detection thành công tại: {filepath}")

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "IsolationForestAnomalyDetector":
        """Tải model từ file pickle"""
        data = joblib.load(filepath)
        detector = cls(**data["params"])
        detector.model = data["model"]
        detector.score_params = data["score_params"]
        detector.is_fitted = True
        return detector