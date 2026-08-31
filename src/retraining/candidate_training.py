"""Time-based candidate training and MLflow Registry logging for production feedback."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from xgboost import XGBClassifier

from src.features.feature_pipeline import FEATURE_COLS, extract_features


@dataclass(frozen=True)
class CandidateTrainingResult:
    metrics: dict[str, float]
    artifact_dir: Path
    dataset_fingerprint: str


def train_candidate(dataset: pd.DataFrame, artifact_dir: Path) -> CandidateTrainingResult:
    """Train/calibrate a candidate from resolved production labels only.

    The caller must evaluate eligibility before reaching this function. The
    chronological split intentionally preserves a final, untouched holdout.
    """
    if "is_fraud" not in dataset or "timestamp" not in dataset:
        raise ValueError("Curated dataset requires is_fraud and timestamp columns")
    ordered = dataset.sort_values("timestamp").reset_index(drop=True)
    train_end, calib_end = int(len(ordered) * 0.70), int(len(ordered) * 0.85)
    train_raw, calib_raw, test_raw = ordered.iloc[:train_end], ordered.iloc[train_end:calib_end], ordered.iloc[calib_end:]
    for name, part in {"train": train_raw, "calibration": calib_raw, "holdout": test_raw}.items():
        if part["is_fraud"].nunique() < 2:
            raise ValueError(f"Time-based {name} split requires both fraud labels")

    train_feat, stats, median = extract_features(train_raw, mode="train")
    calib_feat, _, _ = extract_features(calib_raw, acc_stats_train=stats, train_median=median, mode="infer")
    test_feat, _, _ = extract_features(test_raw, acc_stats_train=stats, train_median=median, mode="infer")
    model = XGBClassifier(
        n_estimators=500, max_depth=4, learning_rate=0.03, min_child_weight=10,
        subsample=0.8, colsample_bytree=0.8, reg_alpha=1, reg_lambda=5,
        scale_pos_weight=float(((train_feat["is_fraud"] == 0).sum() / train_feat["is_fraud"].sum()) ** 0.5),
        eval_metric="aucpr", early_stopping_rounds=50, random_state=42, n_jobs=-1,
    )
    model.fit(train_feat[FEATURE_COLS], train_feat["is_fraud"], eval_set=[(calib_feat[FEATURE_COLS], calib_feat["is_fraud"])], verbose=False)
    try:
        from sklearn.frozen import FrozenEstimator
        calibrated = CalibratedClassifierCV(estimator=FrozenEstimator(model), method="sigmoid")
    except ImportError:  # pragma: no cover - compatibility path
        calibrated = CalibratedClassifierCV(estimator=model, method="sigmoid", cv="prefit")
    calibrated.fit(calib_feat[FEATURE_COLS], calib_feat["is_fraud"])
    probability = calibrated.predict_proba(test_feat[FEATURE_COLS])[:, list(calibrated.classes_).index(1)]
    metrics = {
        "holdout_pr_auc": float(average_precision_score(test_feat["is_fraud"], probability)),
        "holdout_roc_auc": float(roc_auc_score(test_feat["is_fraud"], probability)),
        "holdout_brier_score": float(brier_score_loss(test_feat["is_fraud"], probability)),
    }
    artifact_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(calibrated, artifact_dir / "xgb_calibrated.pkl")
    joblib.dump(stats, artifact_dir / "acc_stats_train.pkl")
    joblib.dump(median, artifact_dir / "train_median.pkl")
    fingerprint = hashlib.sha256(pd.util.hash_pandas_object(ordered[FEATURE_COLS + ["is_fraud"]], index=False).values.tobytes()).hexdigest()
    (artifact_dir / "candidate_manifest.json").write_text(json.dumps({
        "dataset_fingerprint": fingerprint, "rows": len(ordered), "metrics": metrics,
        "split": "chronological_70_15_15", "risk_score_formula": "calibrated_ml_only",
    }, indent=2), encoding="utf-8")
    return CandidateTrainingResult(metrics=metrics, artifact_dir=artifact_dir, dataset_fingerprint=fingerprint)


def log_candidate_to_registry(result: CandidateTrainingResult, model_name: str = "SentinelAI-Fraud-Detector") -> tuple[str, str]:
    """Log a candidate and register it as challenger; never auto-promote champion."""
    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns"))
    mlflow.set_experiment("sentinelai-fraud-detection")
    calibrated = joblib.load(result.artifact_dir / "xgb_calibrated.pkl")
    with mlflow.start_run(run_name="production_feedback_candidate") as run:
        mlflow.log_params({"dataset_fingerprint": result.dataset_fingerprint, "split": "chronological_70_15_15"})
        mlflow.log_metrics(result.metrics)
        mlflow.log_artifacts(str(result.artifact_dir), artifact_path="feature_artifacts")
        model_info = mlflow.sklearn.log_model(calibrated, name="model")
        registered = mlflow.register_model(model_info.model_uri, model_name)
        client = MlflowClient()
        client.set_model_version_tag(model_name, registered.version, "promotion_status", "pending_human_approval")
        client.set_model_version_tag(model_name, registered.version, "dataset_fingerprint", result.dataset_fingerprint)
        client.set_registered_model_alias(model_name, "challenger", registered.version)
        return run.info.run_id, registered.version
