"""Save / load versioned model bundles."""
from __future__ import annotations

import json
from pathlib import Path

import joblib


def save_bundle(path: Path, objects: dict, meta: dict, files: dict[str, str] | None = None) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for name, obj in objects.items():
        joblib.dump(obj, path / f"{name}.joblib", compress=3)
    (path / "metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    for fname, text in (files or {}).items():
        (path / fname).write_text(text)


def load_bundle(path: Path, names: list[str]) -> tuple[dict, dict]:
    objs = {n: joblib.load(path / f"{n}.joblib") for n in names}
    meta = json.loads((path / "metadata.json").read_text())
    return objs, meta
