from __future__ import annotations

import pickle
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .. import config
from ..utils import normalize_label


class ModelUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Prediction:
    label: str
    raw_label: str
    probabilities: dict[str, float] | None


class TrafficCongestionModel:
    def __init__(
        self,
        *,
        xgb: Any,
        label_encoder: Any,
        scaler: Any,
        base_model: Any,
        preprocess_input: Any,
    ):
        self.xgb = xgb
        self.le = label_encoder
        self.scaler = scaler
        self.base_model = base_model
        self.preprocess_input = preprocess_input

    @staticmethod
    def _load_pickle(path: Path) -> Any:
        with path.open("rb") as f:
            return pickle.load(f)

    @classmethod
    def load_from_paths(
        cls,
        *,
        xgb_path: Path,
        le_path: Path,
        scaler_path: Path,
    ) -> "TrafficCongestionModel":
        missing = [p for p in [xgb_path, le_path, scaler_path] if not p.exists()]
        if missing:
            names = ", ".join(str(p) for p in missing)
            raise ModelUnavailable(
                f"Model files not found. Add them under {config.MODEL_DIR} (missing: {names})."
            )

        try:
            xgb = cls._load_pickle(xgb_path)
            le = cls._load_pickle(le_path)
            scaler = cls._load_pickle(scaler_path)
        except ModuleNotFoundError as e:
            raise ModelUnavailable(
                "Missing ML dependencies to load the saved .pkl files. Install requirements-ml.txt."
            ) from e
        except Exception as e:
            raise ModelUnavailable(f"Could not load model artifacts: {e}") from e

        try:
            from tensorflow.keras.applications import MobileNetV2
            from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
        except Exception as e:  # pragma: no cover
            raise ModelUnavailable(
                "TensorFlow is required to run MobileNetV2. Install requirements-ml.txt or use DEMO_MODE=1."
            ) from e

        base_model = MobileNetV2(
            weights="imagenet",
            include_top=False,
            pooling="avg",
            input_shape=(224, 224, 3),
        )

        return cls(
            xgb=xgb,
            label_encoder=le,
            scaler=scaler,
            base_model=base_model,
            preprocess_input=preprocess_input,
        )

    def predict_from_bytes(self, image_bytes: bytes) -> dict[str, Any]:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Unable to read image.")

        # Matches the notebook's Streamlit app logic (BGR image, resized, then preprocess_input).
        img = cv2.resize(img, (224, 224))

        try:
            from tensorflow.keras.preprocessing.image import img_to_array
        except Exception as e:  # pragma: no cover
            raise ModelUnavailable(
                "TensorFlow is required to preprocess images. Install requirements-ml.txt or use DEMO_MODE=1."
            ) from e

        x = img_to_array(img)
        x = np.expand_dims(x, 0)
        x = self.preprocess_input(x)

        feat = self.base_model.predict(x, verbose=0).flatten()
        feat_scaled = self.scaler.transform([feat])

        pred = self.xgb.predict(feat_scaled)[0]
        raw_label = str(self.le.inverse_transform([pred])[0])
        label = normalize_label(raw_label)

        probabilities: dict[str, float] | None = None
        if hasattr(self.xgb, "predict_proba"):
            try:
                probs = self.xgb.predict_proba(feat_scaled)[0]
                classes = [str(c) for c in getattr(self.le, "classes_", [])]
                if classes and len(classes) == len(probs):
                    probabilities = {
                        classes[i]: float(probs[i]) for i in range(len(probs))
                    }
                else:
                    probabilities = {str(i): float(probs[i]) for i in range(len(probs))}
            except Exception:
                probabilities = None

        return {
            "label": label,
            "raw_label": raw_label,
            "probabilities": probabilities,
        }

    def predict_from_path(self, path: Path) -> dict[str, Any]:
        return self.predict_from_bytes(path.read_bytes())


@lru_cache(maxsize=1)
def get_model() -> TrafficCongestionModel:
    return TrafficCongestionModel.load_from_paths(
        xgb_path=config.XGB_PATH,
        le_path=config.LE_PATH,
        scaler_path=config.SCALER_PATH,
    )
