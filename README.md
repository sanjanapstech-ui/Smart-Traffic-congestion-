# Smart Traffic-Based Route Finder (ML + Frontend)

This replaces the Streamlit UI from your notebook with a cleaner frontend served by a FastAPI backend.

Your original notebook is included at `notebooks/traffic_congestion.ipynb`.

## What you get

- **Predict Image**: upload a road image → get predicted congestion (`low` / `moderate` / `high`)
- **Route Finder**:
  - `ml` mode (needs dataset + model files): simulates traffic at each node using random dataset images + your ML model
  - `demo` mode (no files needed): simulates traffic with placeholders so the UI still works

## 1) Put your trained model files in `models/`

From your notebook you already save:

- `traffic_xgb_model.pkl`
- `label_encoder.pkl`
- `scaler.pkl`

Copy those 3 files into `models/` in this project.

If you saved them in Google Drive (Colab), you can download them with:

```python
from google.colab import files
files.download("/content/drive/MyDrive/traffic_xgb_model.pkl")
files.download("/content/drive/MyDrive/label_encoder.pkl")
files.download("/content/drive/MyDrive/scaler.pkl")
```

## 2) (Optional) Point to your dataset folder for route ML mode

Your dataset should look like:

```
images/
  low/
    *.jpg
  moderate/
    *.jpg
  high/
    *.jpg
```

Set `DATASET_ROOT` to that `images/` folder.

If you put the dataset inside this repo at `data/images/`, the app will use it by default (no env var needed).

## Optional: train + export model locally

If you don’t have the 3 `.pkl` files handy, you can retrain and export them:

```powershell
python scripts\train_and_export.py --dataset-root "C:\path\to\images"
```

## Run locally (Windows / PowerShell)

If TensorFlow fails to install on your local Python, use Docker (recommended) or install Python 3.11.

### Option A: Docker (recommended for deployment too)

```powershell
docker build -t traffic-congestion .
docker run --rm -p 8000:8000 `
  -e DEMO_MODE=0 `
  -v "${PWD}\models:/app/models" `
  -v "C:\path\to\images:/data/images" `
  -e DATASET_ROOT="/data/images" `
  traffic-congestion
```

Then open:

- `http://127.0.0.1:8000/` (splash) → redirects to `/app`
- `http://127.0.0.1:8000/api/status` (debug status: dataset + model + ML deps)

### Option B: Python venv (if your system can install TensorFlow)

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:DATASET_ROOT="C:\path\to\images"   # optional
$env:DEMO_MODE="0"                      # set to 1 to force demo

uvicorn app.main:app --reload
```

To enable ML prediction endpoints locally, install:

```powershell
pip install -r requirements-ml.txt
```

### Using Command Prompt (cmd.exe) instead of PowerShell

If your terminal prompt looks like `C:\...>` (not `PS C:\...>`), use `set`:

```bat
set DEMO_MODE=1
set DATASET_ROOT=C:\path\to\images
python -m uvicorn app.main:app --reload
```

## Deploy

This app is container-friendly. Easiest options:

- **Render / Railway / Fly.io**: deploy as a Docker web service
- Start command inside container: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Notes:

- If you don’t include the dataset on the server, the Route Finder will automatically fall back to `demo` mode.
- If you don’t include the 3 `.pkl` model files, `/api/predict` will return a `503` until you add them.
- If you want to deploy by pushing to GitHub (instead of mounting files), remove the `*.pkl` / `models/` ignores from `.gitignore` so the model files are included.
