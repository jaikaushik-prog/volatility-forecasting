"""Explicit signal, execution and holding-period contract. No implicit forecast lag."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

TZ = 'Asia/Kolkata'
CUTOFF = pd.Timestamp('2024-12-31')


def bounded_parquet(path, date_column, *, start=None, end=CUTOFF, columns=None):
    """Predicate pushdown prevents future numerical observations entering memory."""
    end = pd.Timestamp(end)
    if end > CUTOFF:
        raise ValueError('Stage 5 numerical-data cutoff is 2024-12-31')
    filters = [(date_column, '<=', end)]
    if start is not None:
        filters.append((date_column, '>=', pd.Timestamp(start)))
    frame = pd.read_parquet(path, filters=filters, columns=columns)
    dates = pd.to_datetime(frame[date_column])
    if dates.gt(end).any():
        raise ValueError('Numerical read exceeded the registered cutoff')
    return frame


@dataclass(frozen=True)
class Instrument:
    asset: str
    currency: str
    total_return_verified: bool
    executable: bool
    price_convention: str

    @property
    def label(self):
        return 'EXECUTION_DATA_REQUIRED' if self.executable else 'NON_EXECUTABLE_THEORETICAL_TOTAL_RETURN_INDEX'

    def require_panel(self, panel, *, adjusted_ohlc_verified=False, actions_verified=False):
        if not self.total_return_verified:
            raise ValueError('Total-return adjustment/source gate failed')
        if panel == 'B' and (not self.executable or not adjusted_ohlc_verified or not actions_verified):
            raise ValueError('Panel B requires verified executable OHLC and corporate actions')
        if panel not in ('A', 'B'):
            raise ValueError('Unknown experiment panel')


def validate_grid(frame):
    if not isinstance(frame.index, pd.DatetimeIndex) or not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError('Native session grid must be chronological and unique')
    if frame.index.max() > CUTOFF:
        raise ValueError('Future numerical observations are forbidden in Stage 5')


def validate_signal(row, execution_timestamp, target_date, asset):
    """After-close signal can never execute at the origin close."""
    issued = pd.Timestamp(row['issued_at'])
    execution = pd.Timestamp(execution_timestamp)
    if issued.tzinfo is None or execution.tzinfo is None:
        raise ValueError('Timezone-aware availability/execution timestamps required')
    if not issued < execution:
        raise ValueError('Same-close or future signal execution is forbidden')
    origin = pd.Timestamp(row['origin_date'])
    if origin.date() >= execution.date() or issued.date() != origin.date():
        raise ValueError('After-close origin and availability dates are inconsistent')
    if pd.notna(row.get('training_end')) and pd.Timestamp(row['training_end']) > origin:
        raise ValueError('Training includes future observations')
    if row['asset'] != asset or row['target_quantity'] != 'daily_close_to_close_log_return_variance':
        raise ValueError('Asset or holding-period risk mismatch')
    if pd.Timestamp(row['target_date']) != pd.Timestamp(target_date):
        raise ValueError('Forecast does not target the subsequent holding interval')
    if pd.Timestamp(row['execution_date']).date() != execution.date():
        raise ValueError('Forecast execution session mismatch')


def causal_features(panel):
    from volrisk.forecasting.har import origin_features
    validate_grid(panel)
    result = origin_features(panel)
    available = pd.to_datetime(panel['vix_available_at'])
    origins = pd.to_datetime(panel['origin_timestamp'])
    source_session = pd.to_datetime(panel['vix_source_session'])
    bad = available.notna() & ((available > origins) | (source_session >= panel.index))
    if bad.any():
        raise ValueError('VIX availability violates conservative full-session lag')
    result.loc[available.isna(), 'vix_implied_variance'] = np.nan
    if 'rv_eligible' in panel:
        if (panel.rv.notna() & ~panel.rv_eligible.eq(True)).any():
            raise ValueError('Ineligible intraday session contains a usable RV')
    return result
