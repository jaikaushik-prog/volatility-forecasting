"""Causal end-of-session features; never interpolate or compress missing sessions."""
from __future__ import annotations
import numpy as np
import pandas as pd


def realized_features(daily, frequency=5):
    out = daily.sort_values('session_date').copy()
    if out.session_date.duplicated().any():
        raise ValueError('Duplicate daily feature sessions')
    rv = out[f'rv_{frequency}min']
    past = rv.shift(1)
    out['rv_lag1'] = past
    out['rv_mean5_lag1'] = past.rolling(5,min_periods=5).mean()
    out['rv_mean22_lag1'] = past.rolling(22,min_periods=22).mean()
    out['rv_change_lag1'] = past-past.shift(1)
    out['rv_log_change_lag1'] = np.log(past.where(past>0)/past.shift(1).where(past.shift(1)>0))
    out['realized_vol_of_vol22_lag1'] = np.sqrt(past).rolling(22,min_periods=22).std(ddof=1)
    out['positive_semivariance_lag1'] = out[f'positive_semivariance_{frequency}min'].shift(1)
    out['negative_semivariance_lag1'] = out[f'negative_semivariance_{frequency}min'].shift(1)
    out['overnight_squared_return_lag1'] = out.overnight_squared_return.shift(1)
    total = out[f'full_rv_proxy_{frequency}min'].where(lambda x:x>0)
    out['overnight_risk_share'] = out.overnight_squared_return/total
    out['intraday_risk_share'] = out[f'full_session_rv_{frequency}min']/total
    out['overnight_risk_share_lag1'] = out.overnight_risk_share.shift(1)
    out['intraday_risk_share_lag1'] = out.intraday_risk_share.shift(1)
    out['jump_variance_proxy_lag1'] = out.jump_variance_proxy_5min.shift(1)
    out['feature_origin_timestamp'] = out.session_close
    out['lagged_feature_source_session'] = out.session_date.shift(1)
    return out


def vix_features(nifty_daily, vix, *, annualization=252, calendar_days=365,
                 max_age_seconds=90, percentile_window=252, percentile_min_history=60):
    rows = []
    groups = {d:g.sort_values('available_at') for d,g in vix.groupby('session_date')}
    for day in nifty_daily.itertuples():
        origin = day.session_close
        candidates = groups.get(day.session_date,vix.iloc[:0])
        usable = candidates[candidates.valid_bar & candidates.schedule_verified
            & candidates.available_at.le(origin)] if pd.notna(origin) else candidates.iloc[:0]
        last = usable.iloc[-1] if len(usable) else None
        age = (origin-last.available_at).total_seconds() if last is not None else np.nan
        ok = last is not None and age<=max_age_seconds and bool(day.schedule_verified)
        rows.append({'session_date':day.session_date,'asset':'NIFTY','feature_origin_timestamp':origin,
            'vix_eod_percent':float(last.close) if ok else np.nan,
            'vix_observation_available_at':last.available_at if ok else pd.NaT,
            'vix_age_seconds':float(age) if ok else np.nan,
            'vix_eod_available':bool(ok), 'vix_missing_reason':'' if ok else 'no_valid_same_session_observation_within_age_limit',
            'vix_provenance_verified':bool(ok and last.provenance_verified),
            'research_ready':bool(ok and last.provenance_verified and day.research_ready)})
    out = pd.DataFrame(rows)
    level = out.vix_eod_percent
    out['vix_annualized_decimal'] = level/100
    out['vix_lag1_percent'] = level.shift(1)
    out['vix_change_points'] = level-level.shift(1)
    out['vix_log_change'] = np.log(level/level.shift(1))
    out['vix_mean5_percent'] = level.rolling(5,min_periods=5).mean()
    out['vix_mean22_percent'] = level.rolling(22,min_periods=22).mean()
    pct,counts = [],[]
    for i,value in enumerate(level):
        prior = level.iloc[max(0,i-percentile_window):i].dropna()
        counts.append(len(prior))
        pct.append(float(((prior<value).sum()+.5*(prior==value).sum())/len(prior))
                   if np.isfinite(value) and len(prior)>=percentile_min_history else np.nan)
    out['vix_percentile_past'] = pct
    out['vix_percentile_history_count'] = counts
    # Observed current-day measures are available at this close; no future RV enters.
    mean = nifty_daily.full_rv_proxy_5min.rolling(22,min_periods=22).mean().to_numpy()
    out['trailing_full_rv22_annualized_vol_decimal'] = np.sqrt(mean*annualization)
    out['vix_minus_trailing_rv22_annualized_decimal'] = out.vix_annualized_decimal-out.trailing_full_rv22_annualized_vol_decimal
    out['vix_30calendar_variance_proxy'] = out.vix_annualized_decimal**2*30/calendar_days
    out['trailing_rv_30calendar_variance_proxy'] = mean*annualization*30/calendar_days
    out['implied_minus_trailing_30calendar_variance_proxy'] = out.vix_30calendar_variance_proxy-out.trailing_rv_30calendar_variance_proxy
    return out


def coverage(frame, dataset):
    records=[]
    for col in frame.select_dtypes(include='number'):
        finite=np.isfinite(frame[col].to_numpy(dtype=float))
        dates=frame.loc[finite,'session_date']
        records.append({'dataset':dataset,'feature':col,'rows':len(frame),'nonmissing':int(finite.sum()),
            'missing':int((~finite).sum()),'coverage_fraction':float(finite.mean()) if len(frame) else np.nan,
            'first_available':dates.min(),'last_available':dates.max()})
    return pd.DataFrame(records)
