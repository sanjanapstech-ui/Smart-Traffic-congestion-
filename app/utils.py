from __future__ import annotations

import base64
from pathlib import Path

import cv2
import numpy as np


def normalize_label(lbl: str) -> str:
    lbl = str(lbl).lower()
    if "low" in lbl:
        return "low"
    if "moderate" in lbl:
        return "moderate"
    if "high" in lbl:
        return "high"
    return "moderate"


def _jpeg_data_url(bgr: np.ndarray, *, quality: int = 85) -> str:
    ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("Could not encode image as JPEG.")
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def image_bytes_to_thumbnail_data_url(image_bytes: bytes, *, size: int = 160) -> str:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image.")

    thumb = cv2.resize(img, (size, size))
    return _jpeg_data_url(thumb)


def image_path_to_thumbnail_data_url(path: Path, *, size: int = 160) -> str:
    return image_bytes_to_thumbnail_data_url(path.read_bytes(), size=size)


def placeholder_image_data_url(label: str, *, size: int = 160) -> str:
    label = normalize_label(label)
    colors = {
        "low": ("#10b981", "#052e2b"),
        "moderate": ("#f59e0b", "#2e2205"),
        "high": ("#fb7185", "#2e0614"),
    }
    fg, bg = colors.get(label, ("#a3a3a3", "#111827"))
    text = label.upper()

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{bg}"/>
      <stop offset="1" stop-color="#0b1220"/>
    </linearGradient>
  </defs>
  <rect width="{size}" height="{size}" rx="20" fill="url(#g)"/>
  <circle cx="{int(size*0.2)}" cy="{int(size*0.25)}" r="{int(size*0.08)}" fill="{fg}" opacity="0.9"/>
  <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-family="ui-sans-serif,system-ui" font-size="{int(size*0.16)}" fill="white" font-weight="700">{text}</text>
  <text x="50%" y="72%" dominant-baseline="middle" text-anchor="middle" font-family="ui-sans-serif,system-ui" font-size="{int(size*0.07)}" fill="rgba(255,255,255,0.75)">placeholder</text>
</svg>"""

    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"
