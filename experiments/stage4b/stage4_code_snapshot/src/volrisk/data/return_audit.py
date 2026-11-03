"""Independent numerical checks; never repair supplied return values."""
import numpy as np
import pandas as pd

from volrisk.config import AuditSettings


def audit_returns(frame: pd.DataFrame, settings: AuditSettings, gap_mask=None) -> dict:
    n = len(frame)
    p = pd.to_numeric(frame['price'], errors='coerce').to_numpy(dtype=float)
    s = pd.to_numeric(frame['simple_return'], errors='coerce').to_numpy(dtype=float)
    log = pd.to_numeric(frame['log_return'], errors='coerce').to_numpy(dtype=float)
    gaps = np.zeros(n, dtype=bool) if gap_mask is None else np.asarray(gap_mask, dtype=bool)
    valid = np.isfinite(p) & (p > 0) & frame['date'].notna().to_numpy()
    usable = valid & np.r_[False, valid[:-1]] & ~gaps if n else np.array([], dtype=bool)
    expected_s, expected_log = np.full(n, np.nan), np.full(n, np.nan)
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        ratio = p[1:] / p[:-1]
        expected_s[1:] = ratio - 1
        expected_log[1:] = np.log(ratio)
        expected_s[~usable] = np.nan
        expected_log[~usable] = np.nan
        identity = np.log1p(s)
    close = lambda a, b: np.isclose(a, b, rtol=settings.return_rtol, atol=settings.return_atol, equal_nan=True)
    bad_s = ~close(s, expected_s)
    bad_log = ~close(log, expected_log)
    bad_types = np.zeros(n, dtype=bool)
    for col in ('simple_return', 'log_return'):
        bad_types |= (frame[col].notna() & pd.to_numeric(frame[col], errors='coerce').isna()).to_numpy()
    bad_identity = usable & (~close(log, identity) | (s <= -1))
    bad_alias = np.zeros(n, dtype=bool)
    if 'daily_return' in frame:
        daily = pd.to_numeric(frame['daily_return'], errors='coerce').to_numpy(dtype=float)
        bad_alias = ~close(daily, s)
    bad_compound = np.zeros(n, dtype=bool)
    bad_sum = np.zeros(n, dtype=bool)
    segments = 0
    pos = 0
    while pos < n:
        if not valid[pos]:
            pos += 1
            continue
        stop = pos + 1
        while stop < n and valid[stop] and not gaps[stop]:
            stop += 1
        if stop - pos > 1:
            segments += 1
            with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
                compound = np.cumprod(1 + s[pos+1:stop])
                sums = np.cumsum(log[pos+1:stop])
                target = p[pos+1:stop] / p[pos]
                bad_compound[pos+1:stop] = ~close(compound, target)
                bad_sum[pos+1:stop] = ~close(sums, np.log(target))
        pos = stop
    bad_nonfinite = usable & (~np.isfinite(s) | ~np.isfinite(log))
    bad = bad_s | bad_log | bad_identity | bad_compound | bad_sum | bad_types | bad_alias | bad_nonfinite
    return {
        'status': 'FAIL' if bad.any() else 'PASS',
        'first_return_null': bool(n and np.isnan(s[0]) and np.isnan(log[0])),
        'arithmetic_formula_valid': not bool(bad_s.any()),
        'log_formula_valid': not bool(bad_log.any()),
        'log1p_identity_valid': not bool(bad_identity.any()),
        'compounded_simple_reconciles': not bool(bad_compound.any()),
        'summed_log_reconciles': not bool(bad_sum.any()),
        'daily_return_alias_valid': not bool(bad_alias.any()),
        'segments_checked': segments, 'usable_return_observations': int((usable & ~bad).sum()),
        'unexpected_nonfinite_returns': int(bad_nonfinite.sum()),
        'bad_rows': np.flatnonzero(bad).tolist(),
        'rtol': settings.return_rtol, 'atol': settings.return_atol,
    }
