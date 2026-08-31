"""Optional MLflow tracking for training/evaluation; never used in serving decisions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class MlflowTracker:
    """Log reproducible experiment metadata without coupling scoring to MLflow uptime."""

    def __init__(self, experiment_name: str = "sentinelai-fraud-detection") -> None:
        self.experiment_name = experiment_name
        self.tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")

    def log_run(
        self,
        run_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        artifacts: list[str | Path] | None = None,
        tags: dict[str, str] | None = None,
        raise_on_error: bool = False,
    ) -> bool:
        """Log a run, optionally raising when an operator needs confirmation."""
        try:
            import mlflow

            mlflow.set_tracking_uri(self.tracking_uri)
            mlflow.set_experiment(self.experiment_name)
            with mlflow.start_run(run_name=run_name):
                mlflow.log_params({key: str(value) for key, value in params.items()})
                mlflow.log_metrics({key: float(value) for key, value in metrics.items()})
                if tags:
                    mlflow.set_tags(tags)
                for artifact in artifacts or []:
                    path = Path(artifact)
                    if path.exists():
                        mlflow.log_artifact(str(path))
            return True
        except Exception as error:
            # Experiment tracking must not invalidate a fitted/calibrated model.
            if raise_on_error:
                raise RuntimeError(f"MLflow run could not be logged: {error}") from error
            return False
