from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _strip_wrapping_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
        v = v[1:-1].strip()
    return v


MODEL_DIR = Path(_strip_wrapping_quotes(os.getenv("MODEL_DIR", str(PROJECT_ROOT / "models"))))
XGB_PATH = Path(
    _strip_wrapping_quotes(os.getenv("XGB_PATH", str(MODEL_DIR / "traffic_xgb_model.pkl")))
)
LE_PATH = Path(
    _strip_wrapping_quotes(os.getenv("LE_PATH", str(MODEL_DIR / "label_encoder.pkl")))
)
SCALER_PATH = Path(
    _strip_wrapping_quotes(os.getenv("SCALER_PATH", str(MODEL_DIR / "scaler.pkl")))
)

DATASET_ROOT_ENV = _strip_wrapping_quotes(os.getenv("DATASET_ROOT", ""))
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "data" / "images"
DATASET_ROOT = Path(DATASET_ROOT_ENV) if DATASET_ROOT_ENV else DEFAULT_DATASET_ROOT

DEMO_MODE = os.getenv("DEMO_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}
