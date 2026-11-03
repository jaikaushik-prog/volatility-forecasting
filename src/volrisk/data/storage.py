"""Immutable per-run snapshots, Parquet output and atomic report publication."""

from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
from uuid import uuid4

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Cannot encode {type(value).__name__}")


def write_json(value: dict, path: Path) -> None:
    payload = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, default=_json_default) + "\n"
    write_text(payload, path)


def write_text(value: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{uuid4().hex}.tmp")
    try:
        temp.write_text(value, encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def write_parquet(frame: pd.DataFrame, path: Path, *, raw: bool = False) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite data snapshot: {path}")
    temp = path.with_name(path.name + f".{uuid4().hex}.tmp")
    try:
        frame.to_parquet(temp, engine="pyarrow", index=True if raw else False)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return {"path": str(path.resolve()), "sha256": sha256(path), "rows": len(frame)}


def snapshot_file(source: Path, target: Path) -> dict:
    """Copy original bytes without overwriting or reserializing a source snapshot."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as origin, target.open("xb") as destination:
        shutil.copyfileobj(origin, destination)
    return {"path": str(target.resolve()), "original_path": str(source.resolve()),
            "sha256": sha256(target), "bytes": target.stat().st_size,
            "original_mtime_utc": datetime.fromtimestamp(source.stat().st_mtime,
                                                         timezone.utc).isoformat()}


def snapshot_csv(source: Path, target: Path) -> dict:
    """Manual download time is unknown; an import is not a fresh retrieval."""
    return {**snapshot_file(source, target), "retrieved_at_utc": None,
            "retrieval_note": "Manual download timestamp unknown; filesystem mtime is not treated as retrieval time."}
