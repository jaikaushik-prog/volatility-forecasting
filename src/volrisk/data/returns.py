"""Load audited canonical datasets into forecasting-ready return series.

Daily log returns are used for model estimation and evaluation; simple returns
are carried separately for later portfolio work and are never mixed into the
variance evaluation. Only rows marked ``return_usable`` with finite returns are
kept; nothing is filled or interpolated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

import numpy as np
import pandas as pd

from volrisk.data.storage import sha256

REQUIRED_COLUMNS = ("date", "asset", "log_return", "simple_return", "return_usable", "currency")


@dataclass
class ReturnSeries:
    asset: str
    currency: str
    log_returns: pd.Series
    simple_returns: pd.Series
    source_path: str | None = None
    source_sha256: str | None = None
    audit_id: str | None = None
    n_rows: int = 0
    n_usable: int = 0
    dropped: dict = field(default_factory=dict)
    contiguous: bool = True
    audit_status: str | None = None
    calendar_policy: str = 'observed_sequence'

    @property
    def first_date(self):
        return None if self.log_returns.empty else self.log_returns.index[0]

    @property
    def last_date(self):
        return None if self.log_returns.empty else self.log_returns.index[-1]

    def provenance(self) -> dict:
        return {"asset": self.asset, "currency": self.currency, "source_path": self.source_path,
                "source_sha256": self.source_sha256, "audit_id": self.audit_id, "rows": int(self.n_rows),
                "usable_returns": int(self.n_usable), "dropped": dict(self.dropped), "contiguous": bool(self.contiguous),
                "audit_status": self.audit_status, "calendar_policy": self.calendar_policy,
                "first_date": None if self.first_date is None else self.first_date.date().isoformat(),
                "last_date": None if self.last_date is None else self.last_date.date().isoformat(),
                "estimation_series": "log_return (decimal)", "portfolio_series": "simple_return (decimal, unused here)"}


def returns_from_frame(frame: pd.DataFrame, asset: str, *, preserve_gaps=False,
                       require_verified_intervals=False, **provenance) -> ReturnSeries:
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"{asset}: canonical frame lacks columns {missing}")
    if not frame["asset"].eq(asset).all():
        raise ValueError(f"{asset}: frame contains other assets {sorted(set(frame['asset']) - {asset})}")
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"])
    if data['date'].isna().any() or not data['date'].is_monotonic_increasing:
        raise ValueError(f'{asset}: invalid or unsorted canonical dates')
    data = data.reset_index(drop=True)
    if data['currency'].nunique() != 1:
        raise ValueError(f'{asset}: inconsistent currency')
    if data["date"].duplicated().any():
        raise ValueError(f"{asset}: duplicate session dates in canonical frame")
    usable = data["return_usable"].astype(bool) & np.isfinite(data["log_return"].astype(float)) \
        & np.isfinite(data["simple_return"].astype(float))
    unverified = pd.Series(False, index=data.index)
    if require_verified_intervals:
        if 'calendar_interval_verified' not in data:
            raise ValueError(f'{asset}: interval calendar verification is unavailable')
        unverified = usable & ~data['calendar_interval_verified'].fillna(False).astype(bool)
        usable &= ~unverified
    dropped = {
        "not_return_usable": int((~data["return_usable"].astype(bool)).sum()),
        "non_finite_log_return": int((~np.isfinite(data["log_return"].astype(float))).sum()),
        "total_dropped": int((~usable).sum()),
        "unverified_return_intervals": int(unverified.sum()),
        "unverified_return_dates": data.loc[unverified, 'date'].dt.strftime('%Y-%m-%d').tolist(),
    }
    if "return_exclusion_reason" in data.columns:
        reasons = data.loc[~usable, "return_exclusion_reason"].fillna("").replace("", "unspecified")
        dropped["reasons"] = {str(k): int(v) for k, v in reasons.value_counts().items()}
    first_usable = int(np.flatnonzero(usable.values)[0]) if usable.any() else len(data)
    if preserve_gaps:
        kept = data.iloc[first_usable:].copy()
        kept.loc[~usable.iloc[first_usable:], ['log_return', 'simple_return']] = np.nan
    else:
        kept = data.loc[usable]
    contiguous = bool(usable.values[first_usable:].all())
    currency = str(data["currency"].iloc[0]) if len(data) else ""
    index = pd.DatetimeIndex(kept["date"].values, name="date")
    return ReturnSeries(asset=asset, currency=currency,
                        log_returns=pd.Series(kept["log_return"].astype(float).values, index=index, name="log_return"),
                        simple_returns=pd.Series(kept["simple_return"].astype(float).values, index=index,
                                                 name="simple_return"),
                        n_rows=int(len(data)), n_usable=int(usable.sum()), dropped=dropped, contiguous=contiguous,
                        calendar_policy='verified_intervals_reset_at_gaps' if require_verified_intervals else 'observed_sequence',
                        **provenance)


def load_canonical_returns(latest_audit: Path | str, assets: list[str] | None = None, *, end_date=None,
                           preserve_gaps=False, require_verified_intervals=False,
                           require_manifest=True) -> dict[str, ReturnSeries]:
    """Read the canonical Parquet files referenced by ``reports/latest_audit.json``."""
    pointer_path = Path(latest_audit)
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    if not pointer.get("complete", False):
        raise ValueError(f"latest audit {pointer.get('audit_id')} is incomplete; refusing to forecast on it")
    canonical = pointer.get("canonical", {})
    manifest = None
    if pointer.get('manifest'):
        manifest = json.loads(Path(pointer['manifest']).read_text(encoding='utf-8'))
        if manifest.get('audit_id') != pointer.get('audit_id'):
            raise ValueError('Audit pointer/manifest identity mismatch')
    elif require_manifest:
        raise ValueError('Canonical audit manifest required for provenance verification')
    wanted = list(canonical) if assets is None else list(assets)
    series = {}
    for asset in wanted:
        if asset not in canonical:
            raise KeyError(f"asset {asset!r} is not in the canonical audit output {sorted(canonical)}")
        path = Path(canonical[asset])
        if not path.is_absolute():
            path = (pointer_path.parent.parent / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"canonical dataset for {asset} is missing: {path}")
        digest = sha256(path)
        status = None
        if manifest is not None:
            details = [x for x in manifest['assets'] if x['summary']['asset'] == asset]
            if len(details) != 1 or details[0]['data_artifact']['sha256'] != digest:
                raise ValueError(f'{asset}: canonical hash differs from audit manifest')
            detail = details[0]
            status = detail['summary']['validation_status']
            if (status == 'FAIL' or detail['summary']['return_checks'] != 'PASS'
                    or detail['source_audit'].get('total_return_compatible') is not True):
                raise ValueError(f'{asset}: required numerical/source checks did not pass')
        filters = [('date', '<=', pd.Timestamp(end_date))] if end_date is not None else None
        frame = pd.read_parquet(path, filters=filters)
        series[asset] = returns_from_frame(frame, asset, source_path=str(path), source_sha256=digest,
            audit_id=pointer.get('audit_id'), audit_status=status, preserve_gaps=preserve_gaps,
            require_verified_intervals=require_verified_intervals)
    return series
