"""Orchestrate independent assets; a failed source cannot masquerade as old output."""

from dataclasses import asdict, replace
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import platform
from typing import Callable
from uuid import uuid4

from volrisk import __version__
from volrisk.config import Settings
from volrisk.data.acquisition import download_etf, utc_now
from volrisk.data.models import ASSETS, DownloadError, issue
from volrisk.data.normalization import normalize_nifty, normalize_yfinance
from volrisk.data.reporting import quality_markdown
from volrisk.data.snapshots import replay_etf, replay_nifty
from volrisk.data.storage import sha256, snapshot_csv, write_json, write_parquet, write_text
from volrisk.data.validation import validate


def _versions() -> dict:
    result = {"python": platform.python_version(), "volrisk": __version__}
    for name in ("pandas", "numpy", "yfinance", "pyarrow", "pytest"):
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = "not installed"
    return result


def run_pipeline(settings: Settings, *, skip_download: bool = False,
                 downloader: Callable | None = None, config_path: Path | None = None) -> dict:
    started = utc_now()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex[:8]
    report_dir = settings.reports_dir / "runs" / run_id
    raw_dir = settings.raw_dir / "runs" / run_id
    processed_dir = settings.processed_dir / run_id
    manifest = {"schema_version": 2, "run_id": run_id, "started_at_utc": started,
                "configuration": settings.as_dict(), "skip_download": skip_download,
                "versions": _versions(), "assets": [],
                "return_definitions": {
                    "simple_return": "price.pct_change(fill_method=None)",
                    "daily_return": "price / price.shift(1) - 1; invalid adjacent prices produce null, never filled",
                    "log_return": "np.log(price / price.shift(1))",
                    "volatility_primary": "log_return", "portfolio_pnl": "simple_return",
                }}
    package_root = Path(__file__).resolve().parents[1]
    manifest["implementation_sha256"] = {
        path.relative_to(package_root).as_posix(): sha256(path) for path in sorted(package_root.rglob("*.py"))
    }
    manifest["required_columns"] = ["date", "asset", "price", "daily_return", "currency", "source", "price_convention"]
    if config_path is not None:
        manifest["config_file"] = {"path": str(config_path.resolve()), "sha256": sha256(config_path)}
    reports = []
    for configured_asset in ASSETS:
        asset = (replace(configured_asset, source="NSE Indices official JSON responses")
                 if configured_asset.symbol == "NIFTY50_TRI" and settings.nifty_json_dir is not None
                 else configured_asset)
        entry = {**asdict(asset), "raw": [], "started_at_utc": utc_now()}
        summary = {"asset": asset.symbol, "asset_name": asset.name, "currency": asset.currency,
                   "source": asset.source, "price_convention": asset.price_convention,
                   "status": "failed", "issues": []}
        try:
            if asset.symbol != "NIFTY50_TRI":
                if skip_download:
                    summary.update(status="skipped", issues=[issue("download_skipped", "error", "ETF download explicitly skipped; no prior run is reused.")])
                    continue
                if settings.etf_snapshot_dir is not None:
                    raw, retrieval = replay_etf(settings.etf_snapshot_dir, asset, raw_dir, entry["raw"])
                else:
                    raw, retrieval = download_etf(asset.symbol, settings.start, settings.end, settings.download,
                                                 cache_dir=settings.raw_dir / ".yfinance_cache", downloader=downloader)
                    retrieval["mode"] = "live_yfinance"
                    entry["raw"].append(write_parquet(raw, raw_dir / f"{asset.symbol}.parquet", raw=True))
                entry["acquisition"] = retrieval
                write_json({**asdict(asset), **retrieval, "raw": entry["raw"]}, raw_dir / f"{asset.symbol}.metadata.json")
                normalized = normalize_yfinance(raw, asset, settings.start, settings.end)
            elif settings.nifty_json_dir is not None:
                paths, retrieval = replay_nifty(settings.nifty_json_dir, raw_dir / "nifty50_tri", entry["raw"])
                entry["acquisition"] = retrieval
                write_json({**asdict(asset), **retrieval, "raw": entry["raw"]}, raw_dir / "NIFTY50_TRI.metadata.json")
                normalized = normalize_nifty(paths, asset, settings.start, settings.end, settings.nifty_date_format)
            else:
                sources = sorted(p for p in settings.nifty_csv_dir.glob("*") if p.is_file() and p.suffix.lower() == ".csv")
                if not sources:
                    message = (f"Place manually downloaded official NIFTY 50 Total Returns Index CSV files in {settings.nifty_csv_dir}. "
                               "At https://www.niftyindices.com/reports/historical-data select Total returns Index Values, "
                               "NIFTY 50, then download CSVs for successive periods. Keep the original files unchanged. "
                               "Price-index and net-total-return files are not accepted.")
                    summary.update(status="missing_input", issues=[issue("nifty_csv_missing", "error", message)])
                    continue
                imported = utc_now()
                paths = []
                for source in sources:
                    target = raw_dir / "nifty50_tri" / source.name
                    snapshot = snapshot_csv(source, target)
                    snapshot["imported_at_utc"] = imported
                    entry["raw"].append(snapshot)
                    paths.append(target)
                entry["acquisition"] = {"mode": "manual_official_csv", "imported_at_utc": imported,
                                        "retrieved_at_utc": None, "source_origin": "user-supplied official export; not cryptographically authenticated"}
                write_json(entry, raw_dir / "NIFTY50_TRI.metadata.json")
                normalized = normalize_nifty(paths, asset, settings.start, settings.end, settings.nifty_date_format)
            entry["normalization"] = normalized.details
            summary = validate(normalized, asset, settings.start, settings.end, settings.validation)
            if summary["status"] != "failed":
                summary["processed"] = write_parquet(normalized.frame, processed_dir / f"{asset.symbol}.parquet")
        except Exception as exc:
            summary.update(status="failed")
            summary["issues"].append(issue("asset_ingestion_failed", "error", f"{type(exc).__name__}: {exc}"))
            if isinstance(exc, DownloadError):
                entry["failed_download_attempts"] = exc.attempts
        finally:
            entry.update(finished_at_utc=utc_now(), quality=summary)
            manifest["assets"].append(entry)
            reports.append(summary)
    complete = all(item["status"] in {"passed", "warning"} for item in reports)
    report = {"schema_version": 1, "run_id": run_id, "start": settings.start.isoformat(),
              "end": settings.end.isoformat(), "complete": complete, "assets": reports}
    manifest.update(finished_at_utc=utc_now(), complete=complete)
    write_json(manifest, report_dir / "manifest.json")
    write_json(report, report_dir / "data_quality.json")
    write_text(quality_markdown(report), report_dir / "data_quality.md")
    latest = {"run_id": run_id, "complete": complete, "report_dir": str(report_dir.resolve()),
              "manifest": str((report_dir / "manifest.json").resolve()),
              "data_quality": str((report_dir / "data_quality.json").resolve()),
              "processed": {r["asset"]: r["processed"]["path"] for r in reports if "processed" in r}}
    # A failed rerun still updates this pointer, preventing silent use of yesterday's success.
    write_json(latest, settings.reports_dir / "latest.json")
    return {**latest, "assets": reports}
