"""Controlled model resolution for local artifacts or MLflow Registry aliases."""

from .model_bundle import ModelBundle, load_production_bundle

__all__ = ["ModelBundle", "load_production_bundle"]
