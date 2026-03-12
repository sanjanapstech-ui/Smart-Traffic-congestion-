from __future__ import annotations

import argparse
import pickle
import random
from pathlib import Path

import cv2
import numpy as np
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from xgboost import XGBClassifier


def _random_brightness(img: np.ndarray) -> np.ndarray:
    factor = random.uniform(0.6, 1.4)
    return np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)


def _random_noise(img: np.ndarray) -> np.ndarray:
    noise = np.random.normal(0, 10, img.shape)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def _cutout(img: np.ndarray) -> np.ndarray:
    h, w, _ = img.shape
    size = random.randint(20, 50)
    x = random.randint(0, max(0, w - size))
    y = random.randint(0, max(0, h - size))
    img[y : y + size, x : x + size] = 0
    return img


def _random_blur(img: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(img, (5, 5), 0)


def _random_sharpen(img: np.ndarray) -> np.ndarray:
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    return cv2.filter2D(img, -1, kernel)


def _random_flip(img: np.ndarray) -> np.ndarray:
    return cv2.flip(img, 1)


def augment_image(img_rgb: np.ndarray) -> np.ndarray:
    ops = [
        _random_brightness,
        _random_noise,
        _cutout,
        _random_blur,
        _random_sharpen,
        _random_flip,
    ]
    op = random.choice(ops)
    return op(img_rgb)


def iter_images(dataset_root: Path):
    valid_exts = {".jpg", ".jpeg", ".png"}
    for label_dir in sorted(dataset_root.iterdir()):
        if not label_dir.is_dir():
            continue
        label = label_dir.name
        for img_path in label_dir.rglob("*"):
            if not img_path.is_file():
                continue
            if img_path.suffix.lower() not in valid_exts:
                continue
            yield label, img_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("models"))
    parser.add_argument("--augment-per-image", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    dataset_root: Path = args.dataset_root
    if not dataset_root.exists() or not dataset_root.is_dir():
        raise SystemExit(f"Invalid --dataset-root: {dataset_root}")

    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    base_model = MobileNetV2(
        weights="imagenet",
        include_top=False,
        pooling="avg",
        input_shape=(224, 224, 3),
    )
    for layer in base_model.layers:
        layer.trainable = False

    X: list[np.ndarray] = []
    y: list[str] = []

    for label, img_path in iter_images(dataset_root):
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_rgb = cv2.resize(img_rgb, (224, 224))

        inp = preprocess_input(np.expand_dims(img_rgb, 0))
        feat = base_model.predict(inp, verbose=0).flatten()
        X.append(feat)
        y.append(label)

        for _ in range(max(0, args.augment_per_image)):
            aug = augment_image(img_rgb.copy())
            aug_inp = preprocess_input(np.expand_dims(aug, 0))
            feat_aug = base_model.predict(aug_inp, verbose=0).flatten()
            X.append(feat_aug)
            y.append(label)

    if not X:
        raise SystemExit("No images found. Check dataset structure and file extensions.")

    X_np = np.array(X)
    y_np = np.array(y)

    le = LabelEncoder()
    y_encoded = le.fit_transform(y_np)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_np)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled,
        y_encoded,
        test_size=0.2,
        random_state=args.seed,
        stratify=y_encoded,
    )

    xgb = XGBClassifier(
        objective="multi:softmax",
        num_class=len(le.classes_),
        n_estimators=700,
        max_depth=8,
        learning_rate=0.03,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_weight=1,
        gamma=0.15,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=args.seed,
        tree_method="hist",
    )
    xgb.fit(X_train, y_train)

    y_pred = xgb.predict(X_test)
    print(f"Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    (out_dir / "traffic_xgb_model.pkl").write_bytes(pickle.dumps(xgb))
    (out_dir / "label_encoder.pkl").write_bytes(pickle.dumps(le))
    (out_dir / "scaler.pkl").write_bytes(pickle.dumps(scaler))

    print(f"Saved: {out_dir / 'traffic_xgb_model.pkl'}")
    print(f"Saved: {out_dir / 'label_encoder.pkl'}")
    print(f"Saved: {out_dir / 'scaler.pkl'}")


if __name__ == "__main__":
    main()
