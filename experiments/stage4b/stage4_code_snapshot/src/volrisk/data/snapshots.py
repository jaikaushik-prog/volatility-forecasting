"""Replay explicit downloaded sources, verifying hashes and preserving original bytes."""

from datetime import datetime
import json
from pathlib import Path
import re

import pandas as pd

from volrisk.data.acquisition import utc_now
from volrisk.data.models import Asset, DataError
from volrisk.data.storage import snapshot_file


def _expected_hash(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", value):
        raise DataError("Source metadata must contain a valid SHA-256 fingerprint")
    return value.lower()


def _local_file(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name:
        raise DataError("Source manifest must name a file")
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise DataError(f"Source file missing or outside snapshot directory: {name}")
    return target


def _copy(source: Path, target: Path, records: list[dict], expected: str | None = None) -> Path:
    record = snapshot_file(source, target)
    record["imported_at_utc"] = utc_now()
    records.append(record)
    if expected is not None and (not isinstance(expected, str) or record["sha256"] != expected.lower()):
        raise DataError(f"SHA-256 mismatch for {source.name}; source snapshot was changed")
    return target


def replay_etf(directory: Path, asset: Asset, destination: Path,
               records: list[dict]) -> tuple[pd.DataFrame, dict]:
    """Accept the original yfinance Parquet and the retrieval metadata saved with it."""
    metadata_path = _copy(_local_file(directory, f"{asset.symbol}_metadata.json"),
                          destination / f"{asset.symbol}_source_metadata.json", records)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    request = metadata["request"]
    if (metadata.get("symbol") != asset.symbol or metadata.get("currency") != asset.currency
            or metadata.get("price_convention") != asset.price_convention
            or metadata.get("source_url") != asset.source_url):
        raise DataError(f"{asset.symbol}: source metadata does not identify the requested asset/convention")
    required = {"tickers": asset.symbol, "interval": "1d", "auto_adjust": True,
                "actions": True, "back_adjust": False, "repair": False,
                "keepna": True, "rounding": False}
    for key, value in required.items():
        if request.get(key) != value or type(request.get(key)) is not type(value):
            raise DataError(f"{asset.symbol}: snapshot request must have {key}={value!r}")
    retrieved = metadata["retrieved_at_utc"]
    if datetime.fromisoformat(retrieved.replace("Z", "+00:00")).utcoffset() is None:
        raise DataError("Retrieval timestamp must include its timezone")
    source = _local_file(directory, metadata["raw_snapshot"])
    raw_path = _copy(source, destination / f"{asset.symbol}.parquet", records, _expected_hash(metadata["raw_sha256"]))
    raw = pd.read_parquet(raw_path)
    return raw, {
        "mode": "saved_yfinance_snapshot", "imported_at_utc": utc_now(),
        "retrieved_at_utc": retrieved, "request": request,
        "retrieval_versions": metadata.get("versions", {}),
        "raw_representation": metadata.get("raw_representation"),
        "source_metadata": str(metadata_path.resolve()),
    }


def replay_nifty(directory: Path, destination: Path,
                 records: list[dict]) -> tuple[list[Path], dict]:
    """Read the original NSE JSON responses listed in the download's provenance file."""
    manifest_path = _copy(_local_file(directory, "provenance.json"),
                          destination / "provenance.json", records)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if (manifest.get("index") != "NIFTY 50" or manifest.get("series") != "Gross Total Returns Index"
            or manifest.get("currency_basis") != "INR"
            or manifest.get("endpoint") != "https://www.niftyindices.com/BackPage/getTotalReturnIndexString"):
        raise DataError("NIFTY snapshot provenance does not identify the official gross TRI")
    batches = manifest.get("source_responses")
    if not isinstance(batches, list) or not batches:
        raise DataError("NIFTY source manifest has no response files")
    paths, responses, seen = [], [], set()
    for batch in batches:
        source = _local_file(directory, batch["file"])
        if source in seen:
            raise DataError(f"Duplicate source manifest entry: {batch['file']}")
        seen.add(source)
        request = batch["request"]
        if request.get("name", "").upper() != "NIFTY 50" or request.get("indexName", "").upper() != "NIFTY 50":
            raise DataError("NIFTY response request is for a different index")
        target = destination / source.relative_to(directory.resolve())
        paths.append(_copy(source, target, records, _expected_hash(batch["sha256"])))
        payload = json.loads(target.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or len(payload) != batch.get("observations"):
            raise DataError(f"Response observation count differs from provenance: {source.name}")
        response = {"file": str(target.resolve()), "request": request,
                    "retrieved_at_utc": None, "response_saved_at_utc": batch.get("saved_at_utc")}
        request_source = source.with_name(source.name.replace("_response.json", "_request.json"))
        if request_source != source and request_source.is_file():
            request_target = _copy(request_source, target.with_name(request_source.name), records)
            request_metadata = json.loads(request_target.read_text(encoding="utf-8-sig"))
            if request_metadata.get("response_sha256") != batch["sha256"]:
                raise DataError(f"Request metadata hash mismatch: {request_source.name}")
            response["recorded_retrieval_at_utc"] = request_metadata.get("retrieved_at_utc")
            response["retrieval_time_basis"] = "Original downloader recorded response-file save time; HTTP completion was not timed separately."
        responses.append(response)
    return paths, {
        "mode": "saved_nse_json_responses", "imported_at_utc": utc_now(),
        "retrieved_at_utc": None, "source_url": manifest.get("source_page"),
        "endpoint": manifest["endpoint"], "method": manifest.get("method"),
        "retrieval_note": "Original per-response save times retained separately; replay does not claim a new download.",
        "responses": responses,
    }
