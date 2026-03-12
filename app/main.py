from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from . import config
from .ml.model import ModelUnavailable, get_model
from .routing.graph import GRAPH
from .routing.route import compute_route_demo, compute_route_ml

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Traffic Congestion", version="0.1.0")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
def splash(request: Request):
    return templates.TemplateResponse("splash.html", {"request": request})


@app.get("/app", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/healthz")
def healthz():
    return {"ok": True}


def _count_dataset_images(dataset_root: Path) -> int:
    if not dataset_root.exists() or not dataset_root.is_dir():
        return 0
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    count = 0
    for p in dataset_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            count += 1
    return count


@app.get("/api/status")
def api_status():
    dataset_root = config.DATASET_ROOT
    dataset_count = _count_dataset_images(dataset_root)
    dataset_ok = dataset_root.exists() and dataset_root.is_dir() and dataset_count > 0

    model_files = {
        "xgb": {"path": str(config.XGB_PATH), "exists": config.XGB_PATH.exists()},
        "label_encoder": {"path": str(config.LE_PATH), "exists": config.LE_PATH.exists()},
        "scaler": {"path": str(config.SCALER_PATH), "exists": config.SCALER_PATH.exists()},
    }
    model_files_ok = all(v["exists"] for v in model_files.values())

    ml_deps = {
        "tensorflow": find_spec("tensorflow") is not None,
        "xgboost": find_spec("xgboost") is not None,
        "sklearn": find_spec("sklearn") is not None,
    }
    ml_deps_ok = all(ml_deps.values())

    ml_ready = model_files_ok and ml_deps_ok
    if config.DEMO_MODE:
        auto_mode = "demo"
    else:
        auto_mode = "ml" if (dataset_ok and ml_ready) else "demo"

    return {
        "demo_mode_env": config.DEMO_MODE,
        "dataset": {
            "root": str(dataset_root),
            "exists": dataset_root.exists(),
            "is_dir": dataset_root.is_dir(),
            "image_count": dataset_count,
            "supported_exts": [".jpg", ".jpeg", ".png", ".webp"],
        },
        "model_files": model_files,
        "ml_deps": ml_deps,
        "ml_ready": ml_ready,
        "auto_mode": auto_mode,
    }


@app.get("/api/graph")
def api_graph():
    return {"nodes": list(GRAPH.keys())}


@app.post("/api/predict")
async def api_predict(file: UploadFile = File(...)):
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty upload.")

    try:
        model = get_model()
    except ModelUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    try:
        return model.predict_from_bytes(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class RouteRequest(BaseModel):
    source: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    mode: Literal["auto", "ml", "demo"] = "auto"


@app.post("/api/route")
def api_route(req: RouteRequest):
    if req.source not in GRAPH:
        raise HTTPException(status_code=400, detail=f"Unknown source: {req.source}")
    if req.destination not in GRAPH:
        raise HTTPException(
            status_code=400, detail=f"Unknown destination: {req.destination}"
        )
    if req.source == req.destination:
        raise HTTPException(
            status_code=400, detail="Source and destination cannot be the same."
        )

    mode = req.mode
    dataset_root = config.DATASET_ROOT
    demo_reason: str | None = None

    if mode == "auto" and config.DEMO_MODE:
        mode = "demo"
        demo_reason = "forced by DEMO_MODE=1"

    if mode in {"auto", "ml"}:
        if mode == "ml":
            if not dataset_root.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"DATASET_ROOT does not exist: {dataset_root}",
                )
            if not dataset_root.is_dir():
                raise HTTPException(
                    status_code=400,
                    detail=f"DATASET_ROOT is not a folder: {dataset_root}",
                )

        if dataset_root.exists():
            try:
                model = get_model()
                result = compute_route_ml(
                    source=req.source,
                    destination=req.destination,
                    dataset_root=dataset_root,
                    model=model,
                )
                result["mode"] = "ml"
                return result
            except ModelUnavailable as e:
                if mode == "ml":
                    raise HTTPException(status_code=503, detail=str(e)) from e
                demo_reason = str(e)
            except FileNotFoundError as e:
                if mode == "ml":
                    raise HTTPException(status_code=400, detail=str(e)) from e
                demo_reason = str(e)
            except Exception as e:
                if mode == "ml":
                    raise HTTPException(
                        status_code=500, detail=f"Route failed: {e}"
                    ) from e
                demo_reason = f"ML route failed: {e}"
        else:
            demo_reason = f"dataset not found at {dataset_root}"

    if mode == "demo" and demo_reason is None:
        demo_reason = "requested demo mode"

    result = compute_route_demo(
        source=req.source,
        destination=req.destination,
        dataset_root=dataset_root if dataset_root.exists() else None,
    )
    result["mode"] = "demo"
    if demo_reason:
        result["reason"] = demo_reason
    return result
