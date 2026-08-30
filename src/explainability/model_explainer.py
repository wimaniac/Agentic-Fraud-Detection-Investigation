"""Model evidence based on native XGBoost TreeSHAP contributions.

The explanation is deliberately separate from scoring.  Contributions describe
how each feature moved the underlying XGBoost margin; calibrated probability,
risk tier and policy remain owned by their existing deterministic components.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


class ModelExplainer:
    """Extract local TreeSHAP and global feature-importance evidence safely."""

    def __init__(self, top_features: int = 5) -> None:
        self.top_features = top_features

    def explain(self, calibrated_model: Any, features: pd.DataFrame) -> dict[str, Any]:
        """Return evidence for exactly one already-engineered transaction.

        This method never calls ``predict`` and therefore cannot alter the
        calibrated prediction path.  If a fitted XGBoost estimator cannot be
        reached, callers receive an explicit unavailable explanation instead
        of a fabricated feature attribution.
        """
        if len(features) != 1:
            return self._unavailable("Local explanation requires exactly one transaction.")

        try:
            estimator = self._unwrap_estimator(calibrated_model)
            booster = estimator.get_booster()
            import xgboost as xgb

            feature_names = list(features.columns)
            matrix = xgb.DMatrix(features, feature_names=feature_names)
            contributions = booster.predict(matrix, pred_contribs=True)[0]
            if len(contributions) != len(feature_names) + 1:
                raise ValueError("Unexpected TreeSHAP contribution shape")

            local = self._local_contributions(feature_names, contributions[:-1])
            return {
                "available": True,
                "method": "xgboost_native_treeshap",
                "score_space": "underlying_xgboost_raw_margin",
                "base_value": float(contributions[-1]),
                "top_positive_drivers": local["positive"],
                "top_negative_drivers": local["negative"],
                "global_feature_importance": self._global_importance(estimator, feature_names),
                "limitations": [
                    "Contributions explain the underlying XGBoost margin, not a new risk score.",
                    "Probability calibration, risk tier and policy are calculated elsewhere and are unchanged.",
                ],
            }
        except Exception as error:
            return self._unavailable(str(error))

    def _unwrap_estimator(self, model: Any) -> Any:
        """Reach the fitted XGBClassifier inside supported calibration wrappers."""
        current = model
        for _ in range(6):
            if hasattr(current, "get_booster"):
                return current
            calibrated = getattr(current, "calibrated_classifiers_", None)
            if calibrated:
                current = calibrated[0]
                continue
            for attribute in ("estimator", "base_estimator"):
                candidate = getattr(current, attribute, None)
                if candidate is not None:
                    current = candidate
                    break
            else:
                break
        raise TypeError("A fitted XGBoost estimator was not found in the calibrated model")

    def _local_contributions(self, names: list[str], values: np.ndarray) -> dict[str, list[dict[str, float | str]]]:
        entries = [
            {"feature": name, "contribution": float(value)}
            for name, value in zip(names, values, strict=True)
        ]
        positive = sorted((item for item in entries if item["contribution"] > 0), key=lambda item: item["contribution"], reverse=True)
        negative = sorted((item for item in entries if item["contribution"] < 0), key=lambda item: item["contribution"])
        return {
            "positive": positive[: self.top_features],
            "negative": negative[: self.top_features],
        }

    def _global_importance(self, estimator: Any, feature_names: list[str]) -> list[dict[str, float | str]]:
        values = getattr(estimator, "feature_importances_", None)
        if values is None or len(values) != len(feature_names):
            return []
        entries = [
            {"feature": name, "importance": float(value)}
            for name, value in zip(feature_names, values, strict=True)
        ]
        return sorted(entries, key=lambda item: item["importance"], reverse=True)[: self.top_features]

    @staticmethod
    def _unavailable(reason: str) -> dict[str, Any]:
        return {
            "available": False,
            "method": "xgboost_native_treeshap",
            "reason": reason,
            "limitations": ["Risk scoring continues normally when explanation evidence is unavailable."],
        }
