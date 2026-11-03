"""Network acquisition only; source frames are not normalized here."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import time
from typing import Callable

import pandas as pd

from volrisk.config import DownloadSettings
from volrisk.data.models import DownloadError


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def download_etf(
    symbol: str, start: date, end: date, settings: DownloadSettings,
    *, cache_dir: Path | None = None, downloader: Callable | None = None,
    sleep: Callable = time.sleep,
) -> tuple[pd.DataFrame, dict]:
    """Download one asset, retry exceptions AND empty responses, retain audit history."""
    if downloader is None:
        import yfinance as yf

        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            yf.set_tz_cache_location(str(cache_dir))
        downloader = yf.download
    request = dict(
        tickers=symbol, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
        interval="1d", auto_adjust=True, back_adjust=False, actions=True,
        repair=False, keepna=True, rounding=False, threads=False, progress=False,
        ignore_tz=True, multi_level_index=False, timeout=settings.timeout_seconds,
    )
    history = []
    for attempt in range(1, settings.attempts + 1):
        record = {"attempt": attempt, "started_at_utc": utc_now()}
        try:
            frame = downloader(**request)
            if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
                raise ValueError("Provider returned no rows (network, symbol or coverage failure)")
            record.update(status="success", finished_at_utc=utc_now())
            history.append(record)
            return frame, {
                "retrieved_at_utc": record["finished_at_utc"], "request": request,
                "attempts": history,
                "original_index_name": frame.index.name,
                "original_index_frequency": getattr(frame.index, "freqstr", None),
                "raw_representation": "Unmodified yfinance-returned DataFrame serialized to Parquet; not upstream HTTP bytes. Close is already auto-adjusted.",
            }
        except Exception as exc:
            record.update(status="failed", finished_at_utc=utc_now(),
                          error=f"{type(exc).__name__}: {exc}")
            history.append(record)
            if attempt < settings.attempts:
                sleep(settings.retry_backoff_seconds * 2 ** (attempt - 1))
    raise DownloadError(f"{symbol}: download failed after {settings.attempts} attempts: "
                        f"{history[-1]['error']}", history)
