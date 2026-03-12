from __future__ import annotations

import heapq
import os
import random
from pathlib import Path

from ..ml.model import TrafficCongestionModel
from ..utils import image_path_to_thumbnail_data_url, normalize_label, placeholder_image_data_url
from .graph import GRAPH, TRAFFIC_COST


def _safe_relpath(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except Exception:
        return path.name


def get_random_image(root: Path) -> Path:
    folders = [root / d for d in os.listdir(root) if (root / d).is_dir()]
    if not folders:
        raise FileNotFoundError("No subfolders found under DATASET_ROOT")
    folder = random.choice(folders)

    valid_exts = (".jpg", ".jpeg", ".png", ".webp")
    imgs = [folder / f for f in os.listdir(folder) if f.lower().endswith(valid_exts)]

    if not imgs:
        for dirpath, _, filenames in os.walk(folder):
            for filename in filenames:
                if filename.lower().endswith(valid_exts):
                    imgs.append(Path(dirpath) / filename)

    if not imgs:
        raise FileNotFoundError(f"No images found in folder: {folder}")
    return random.choice(imgs)


def classify_image(path: Path, model: TrafficCongestionModel) -> str:
    pred = model.predict_from_path(path)
    raw = str(pred.get("raw_label", ""))
    return normalize_label(raw)


def assign_node_images(graph: dict[str, list[str]], source: str, dest: str, root: Path):
    imgs: dict[str, Path] = {}
    for node in graph:
        if node not in [source, dest]:
            imgs[node] = get_random_image(root)
    return imgs


def classify_nodes(
    graph: dict[str, list[str]],
    imgs: dict[str, Path],
    source: str,
    dest: str,
    model: TrafficCongestionModel,
):
    node_tr: dict[str, str] = {}
    for node in graph:
        if node in [source, dest]:
            node_tr[node] = "low"
        else:
            node_tr[node] = classify_image(imgs[node], model)
    return node_tr


def dijkstra(source: str, dest: str, graph: dict[str, list[str]], node_tr: dict[str, str]):
    pq: list[tuple[int, str, list[str]]] = [(0, source, [source])]
    visited: set[str] = set()

    while pq:
        cost, node, path = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)

        if node == dest:
            return path

        for nei in graph.get(node, []):
            w = TRAFFIC_COST.get(node_tr.get(nei, "moderate"), 5)
            heapq.heappush(pq, (cost + w, nei, path + [nei]))

    return None


def _path_cost(path: list[str], node_tr: dict[str, str]) -> int:
    return sum(TRAFFIC_COST.get(node_tr.get(n, "moderate"), 5) for n in path[1:])


def _label_from_path(dataset_root: Path, path: Path) -> str:
    try:
        rel = path.relative_to(dataset_root)
        if rel.parts:
            return normalize_label(rel.parts[0])
    except Exception:
        pass
    return "moderate"


def compute_route_demo(
    *, source: str, destination: str, dataset_root: Path | None = None
) -> dict:
    labels = ["low", "moderate", "high"]
    weights = [0.45, 0.4, 0.15]

    node_traffic: dict[str, str] = {}
    node_image_data_url: dict[str, str] = {}
    node_image_path: dict[str, Path] = {}
    node_image_source: dict[str, str] = {}

    for node in GRAPH:
        if node in {source, destination}:
            node_traffic[node] = "low"
            continue

        img_path: Path | None = None
        if dataset_root and dataset_root.exists():
            try:
                img_path = get_random_image(dataset_root)
            except Exception:
                img_path = None

        if img_path is not None:
            lbl = _label_from_path(dataset_root, img_path)
            node_traffic[node] = lbl
            node_image_path[node] = img_path
            node_image_source[node] = "dataset"
            try:
                node_image_data_url[node] = image_path_to_thumbnail_data_url(img_path)
            except Exception:
                node_image_data_url[node] = placeholder_image_data_url(lbl)
        else:
            lbl = random.choices(labels, weights=weights, k=1)[0]
            node_traffic[node] = lbl
            node_image_source[node] = "placeholder"
            node_image_data_url[node] = placeholder_image_data_url(lbl)

    path = dijkstra(source, destination, GRAPH, node_traffic)
    if path is None:
        raise RuntimeError("No route found.")

    total_cost = _path_cost(path, node_traffic)
    nodes = [
        {
            "name": n,
            "traffic": node_traffic[n],
            "image_data_url": node_image_data_url.get(n, ""),
            "image_relpath": _safe_relpath(dataset_root, node_image_path[n])
            if dataset_root and n in node_image_path
            else "",
            "image_source": node_image_source.get(n, "placeholder"),
        }
        for n in path
        if n not in {source, destination}
    ]

    return {"path": path, "total_cost": total_cost, "nodes": nodes}


def compute_route_ml(
    *,
    source: str,
    destination: str,
    dataset_root: Path,
    model: TrafficCongestionModel,
) -> dict:
    node_images = assign_node_images(GRAPH, source, destination, dataset_root)
    node_traffic = classify_nodes(GRAPH, node_images, source, destination, model)
    path = dijkstra(source, destination, GRAPH, node_traffic)

    if path is None:
        raise RuntimeError("No route found.")

    total_cost = _path_cost(path, node_traffic)
    nodes = [
        {
            "name": n,
            "traffic": node_traffic[n],
            "image_data_url": image_path_to_thumbnail_data_url(node_images[n]),
            "image_relpath": _safe_relpath(dataset_root, node_images[n]),
            "image_source": "dataset",
        }
        for n in path
        if n not in {source, destination}
    ]

    return {"path": path, "total_cost": total_cost, "nodes": nodes}
