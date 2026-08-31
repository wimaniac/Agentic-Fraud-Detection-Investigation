"""Resolve one reproducible model bundle for deterministic serving."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


@dataclass(frozen=True)
class ModelBundle:
    calibrated_model: Any
    acc_stats_train: pd.DataFrame
    train_median: pd.Series
    edges: pd.DataFrame | None
    accounts: pd.DataFrame | None
    source: str


@lru_cache(maxsize=1)
def load_production_bundle() -> ModelBundle:
    """Load local artifacts by default, or an explicit MLflow champion alias."""
    source = os.getenv("MODEL_SOURCE", "local").lower()
    if source == "local":
        model_dir = Path(os.getenv("MODEL_DIR", "models"))
        if not model_dir.exists():
            raise FileNotFoundError("Calibrated model artifacts directory 'models' was not found")
        return ModelBundle(
            calibrated_model=joblib.load(model_dir / "xgb_calibrated.pkl"),
            acc_stats_train=joblib.load(model_dir / "acc_stats_train.pkl"),
            train_median=joblib.load(model_dir / "train_median.pkl"),
            edges=pd.read_parquet(model_dir / "_edges_ref.parquet") if (model_dir / "_edges_ref.parquet").exists() else None,
            accounts=pd.read_parquet(model_dir / "_accounts_ref.parquet") if (model_dir / "_accounts_ref.parquet").exists() else None,
            source="local_artifacts",
        )
    if source != "mlflow":
        raise ValueError("MODEL_SOURCE must be 'local' or 'mlflow'")

    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise RuntimeError("MLFLOW_TRACKING_URI is required when MODEL_SOURCE=mlflow")
    name = os.getenv("MLFLOW_MODEL_NAME", "SentinelAI-Fraud-Detector")
    alias = os.getenv("MLFLOW_MODEL_ALIAS", "champion")
    mlflow.set_tracking_uri(tracking_uri)
    version = MlflowClient().get_model_version_by_alias(name, alias)
    artifact_dir = Path(mlflow.artifacts.download_artifacts(run_id=version.run_id, artifact_path="feature_artifacts"))
    return ModelBundle(
        calibrated_model=mlflow.sklearn.load_model(f"models:/{name}@{alias}"),
        acc_stats_train=joblib.load(artifact_dir / "acc_stats_train.pkl"),
        train_median=joblib.load(artifact_dir / "train_median.pkl"),
        edges=None,
        accounts=None,
        source=f"mlflow:{name}@{alias}",
    )
