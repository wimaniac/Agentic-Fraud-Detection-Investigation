"""Import the existing SentinelAI model as an audit-only MLflow Registry baseline.

This script does not retrain, evaluate, or promote a model.  Its registered
version is deliberately tagged as an unvalidated historical baseline and never
receives the ``champion`` alias automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SAFE_ARTIFACTS = [
    "xgb_calibrated.pkl",
    "acc_stats_train.pkl",
    "train_median.pkl",
    "isolation_forest.pkl",
    "anomaly_threshold_p98.pkl",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=PROJECT_ROOT / "models")
    parser.add_argument("--tracking-uri", help="For example: http://localhost:5000")
    parser.add_argument("--model-name", default="SentinelAI-Fraud-Detector")
    parser.add_argument("--dry-run", action="store_true", help="Show selected artifacts without contacting MLflow")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_dir = args.model_dir.resolve()
    artifacts = [model_dir / name for name in SAFE_ARTIFACTS if (model_dir / name).is_file()]
    if not artifacts:
        raise SystemExit(f"No safe model artifacts found in {model_dir}")

    manifest = {
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "existing_local_model_artifacts",
        "artifacts": [{"name": path.name, "size_bytes": path.stat().st_size} for path in artifacts],
        "excluded": ["raw transactions", "holdout parquet", "feedback data", "investigation snapshots"],
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if args.dry_run:
        print("Dry run complete: no MLflow run was created.")
        return

    if args.tracking_uri:
        os.environ["MLFLOW_TRACKING_URI"] = args.tracking_uri

    import mlflow
    from mlflow import MlflowClient

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("sentinelai-fraud-detection")
    with tempfile.TemporaryDirectory() as directory:
        manifest_path = Path(directory) / "legacy_baseline_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        with mlflow.start_run(run_name="legacy_baseline_import") as run:
            mlflow.log_params({
                "model_type": "calibrated_xgboost",
                "feature_count": 24,
                "risk_score_formula": "calibrated_ml_only",
                "risk_tier_thresholds": "low_lt_30_medium_lt_70_high_ge_70",
            })
            mlflow.set_tags({
                "run_type": "retrospective_import",
                "metrics_status": "not_recomputed",
                "data_policy": "no_raw_transactions_or_feedback_uploaded",
            })
            for artifact in [*artifacts, manifest_path]:
                mlflow.log_artifact(str(artifact), artifact_path="feature_artifacts")
            model_info = mlflow.sklearn.log_model(
                joblib.load(model_dir / "xgb_calibrated.pkl"), name="model"
            )
            registered = mlflow.register_model(model_info.model_uri, args.model_name)

        client = MlflowClient(tracking_uri=tracking_uri)
        client.set_model_version_tag(
            args.model_name, registered.version, "promotion_status", "baseline_not_validated"
        )
        client.set_model_version_tag(args.model_name, registered.version, "source_run_id", run.info.run_id)
    print(
        "Baseline import completed: "
        f"experiment='sentinelai-fraud-detection', model='{args.model_name}', "
        f"version={registered.version}, promotion_status=baseline_not_validated."
    )


if __name__ == "__main__":
    main()
