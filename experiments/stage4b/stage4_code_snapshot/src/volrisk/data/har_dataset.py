"""Read audited intraday artifacts without re-ingestion; seal holdout before loading values."""
from __future__ import annotations
import json
from pathlib import Path
import tomllib
import numpy as np
import pandas as pd

from .storage import sha256
from volrisk.evaluation.walk_forward import PeriodSplits


class ReadinessError(ValueError):
    """Critical integrity/temporal failure; no empirical experiment may proceed."""


def protected_splits(config, root):
    splits = PeriodSplits.from_config(config['splits'])
    if not splits.holdout_sealed:
        raise ReadinessError('Stage 4 does not provide a holdout-unsealing path')
    path = root/config['data']['protected_protocol']
    original = tomllib.loads(path.read_text(encoding='utf-8'))
    protected_start = pd.Timestamp(original['splits']['holdout'][0])
    if splits.validation[1] >= protected_start or splits.development[1] >= protected_start:
        raise ReadinessError('Requested evaluation overlaps the previously protected holdout')
    return splits


def _ordered(frame, label):
    if not frame.session_date.is_monotonic_increasing or frame.session_date.duplicated().any():
        raise ReadinessError(f'{label}: non-monotonic or duplicate session dates')


def validate_daily(daily, bars_by_frequency):
    """Independent identities and bar/session checks on pre-holdout stored artifacts."""
    _ordered(daily,'realized data')
    d = daily.set_index('session_date')
    complete = d.rv_eligible
    if (complete & (~d.session_complete | ~d.schedule_verified | d.missing_or_invalid_minutes.ne(0))).any():
        raise ReadinessError('RV eligible flag contradicts session completeness')
    for frequency in (1,5,10,15):
        rv = d[f'rv_{frequency}min']
        if (complete & (~np.isfinite(rv) | rv.lt(0))).any() or rv[~complete].notna().any():
            raise ReadinessError('Invalid or incomplete-session realized variance')
        if not np.allclose(rv,d[f'positive_semivariance_{frequency}min']+d[f'negative_semivariance_{frequency}min'],
                           equal_nan=True,rtol=1e-10,atol=1e-15):
            raise ReadinessError('Semivariance identity failed')
        if frequency not in bars_by_frequency: continue
        bars = bars_by_frequency[frequency]
        if not bars.timestamp.is_monotonic_increasing or bars.timestamp.duplicated().any():
            raise ReadinessError('Stored bars are not sorted/unique')
        if str(bars.timestamp.dt.tz)!='Asia/Kolkata':
            raise ReadinessError('Stored bar timezone is not Asia/Kolkata')
        duration = (bars.available_at-bars.timestamp).dt.total_seconds()/60
        if not duration.eq(bars.duration_minutes).all() or (duration<=0).any():
            raise ReadinessError('Invalid bar availability/duration convention')
        for date, part in bars.groupby('session_date',sort=False):
            if date not in d.index or not d.loc[date,'rv_eligible']: continue
            info = d.loc[date]
            if (not part.complete.all() or not part.intraday_log_return.notna().all()
                or not part.observed_valid_minutes.eq(part.expected_minutes).all()
                or part.duration_minutes.sum()!=info.expected_minutes
                or part.timestamp.iloc[0]!=info.session_open or part.available_at.iloc[-1]!=info.session_close):
                raise ReadinessError(f'{date}: incomplete or misaligned bars contributed to RV')
            for _,segment in part.groupby('segment'):
                if len(segment)>1 and not np.array_equal(segment.timestamp.iloc[1:].to_numpy(),segment.available_at.iloc[:-1].to_numpy()):
                    raise ReadinessError('Gap/overlap inside an eligible continuous segment')
                reference=segment.close.shift().copy()
                reference.iloc[0]=segment.open.iloc[0]
                reconstructed=np.log(segment.close/reference)
                if not np.allclose(reconstructed,segment.intraday_log_return,rtol=1e-10,atol=1e-14):
                    raise ReadinessError('Stored intraday log return disagrees with within-segment prices')
            implied = float(np.square(part.intraday_log_return).sum())
            if not np.isclose(implied,info[f'rv_{frequency}min'],rtol=1e-10,atol=1e-15):
                raise ReadinessError('Stored RV does not equal squared within-session bar log returns')
        covered = set(bars.session_date)
        if not set(d.index[complete]) <= covered:
            raise ReadinessError('An eligible session has no stored aggregated bars')
    adjacent = d.schedule_verified & d.schedule_verified.shift(fill_value=False) & d.expected_session & d.expected_session.shift(fill_value=False)
    on_ok = adjacent & d.endpoint_open_valid & d.endpoint_close_valid.shift(fill_value=False)
    c2c_ok = adjacent & d.endpoint_close_valid & d.endpoint_close_valid.shift(fill_value=False)
    # The loaded first observation can have a pre-sample predecessor; exclude it from this local comparison.
    for col, expected in [('overnight_log_return',np.log(d.open/d.close.shift()).where(on_ok)),
                          ('close_to_close_log_return',np.log(d.close/d.close.shift()).where(c2c_ok))]:
        if not np.allclose(d[col].iloc[1:],expected.iloc[1:],equal_nan=True,rtol=1e-10,atol=1e-14):
            raise ReadinessError(f'{col}: invalid endpoint adjacency or price reconciliation')
    if not np.allclose(d.overnight_squared_return,d.overnight_log_return**2,equal_nan=True,atol=1e-15):
        raise ReadinessError('Overnight-square identity failed')


def validate_vix(vix):
    _ordered(vix,'VIX')
    ok = vix.vix_eod_available
    age = (vix.feature_origin_timestamp-vix.vix_observation_available_at).dt.total_seconds()
    same_session = vix.vix_observation_available_at.dt.tz_localize(None).dt.normalize().eq(vix.session_date)
    if (ok & (~np.isfinite(vix.vix_eod_percent) | vix.vix_eod_percent.le(0) | ~age.between(0,90) | ~same_session)).any():
        raise ReadinessError('VIX source availability/age/units fail the origin-time gate')
    if not np.allclose(vix.vix_annualized_decimal,vix.vix_eod_percent/100,equal_nan=True):
        raise ReadinessError('VIX percentage-to-decimal conversion failed')


def load_har_inputs(config, root):
    """Hash checks use bytes only; numerical Parquet reads are filtered to <= validation end."""
    splits = protected_splits(config,root)
    pointer_path = root/config['data']['latest_intraday']
    pointer = json.loads(pointer_path.read_text(encoding='utf-8'))
    path = Path(pointer['manifest'])
    if sha256(path)!=pointer['manifest_sha256']:
        raise ReadinessError('Intraday manifest hash mismatch')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if not manifest.get('complete'):
        raise ReadinessError('Intraday run is incomplete')
    run = path.parent
    for relative,digest in manifest['inputs_sha256'].items():
        if sha256(root/relative)!=digest:
            raise ReadinessError(f'Changed raw/config/evidence input: {relative}; audit must be reconciled first')
    for relative,digest in manifest['implementation_sha256'].items():
        if sha256(root/relative)!=digest:
            raise ReadinessError(f'Intraday implementation has changed since audit: {relative}')
    provisional = not all(manifest['config']['assets'][key][flag] for key in ('nifty','sensex','india_vix')
                          for flag in ('instrument_verified','timezone_verified','bar_label_verified'))
    if provisional and not config['data']['allow_provisional']:
        raise ReadinessError('Unverified provenance is prohibited by this experiment configuration')
    if provisional and config['data']['vix_extra_lag']<1:
        raise ReadinessError('Unverified EOD timing requires at least one full-session additional VIX lag')
    hashes = {'intraday_manifest':sha256(path),'protected_protocol':sha256(root/config['data']['protected_protocol'])}
    def read(relative):
        f = run/relative
        if relative not in manifest['output_sha256'] or sha256(f)!=manifest['output_sha256'][relative]:
            raise ReadinessError(f'Changed or unaudited intraday artifact: {relative}')
        hashes[relative] = sha256(f)
        return pd.read_parquet(f,filters=[('session_date','>=',splits.development[0]),('session_date','<=',splits.validation[1])])
    datasets = {}
    for asset in config['data']['assets']:
        key = asset.lower()
        if key not in ('nifty','sensex'): raise ReadinessError('Only the audited NIFTY/SENSEX spot candidates are supported')
        daily = read(f'features/{key}_realized_vol_daily.parquet')
        if daily.empty: raise ReadinessError(f'{asset}: no observations in development/validation')
        bars = {f:read(f'intraday/{key}_{f}min.parquet') for f in (5,10,15)}
        validate_daily(daily,bars)
        datasets[asset] = daily
    vix = read('features/nifty_vix_features_daily.parquet')
    validate_vix(vix)
    vix_sources = [s for s in manifest['source_files'] if s['asset']=='INDIA_VIX']
    vix_end = max(pd.Timestamp(s['last_timestamp']).tz_localize(None).normalize() for s in vix_sources)
    return datasets,vix,{'status':'PROVISIONAL' if provisional else 'VERIFIED','critical_checks_passed':True,
        'intraday_run_id':manifest['run_id'],'input_hashes':hashes,'holdout_sealed':True,
        'loaded_through':str(splits.validation[1].date()),'vix_source_last_session':str(vix_end.date()),
        'user_confirmation':config['data'].get('user_confirmation',{}),
        'remaining_blockers':['timestamp_timezone_unconfirmed','bar_labels_unconfirmed','vendor_export_not_independently_verified',
                              'SENSEX_identity_not_independently_verified'] if provisional else []}


def prepare_panel(daily, vix, *, frequency=5, scenario='eligible', vix_extra_lag=1,
                  full_session_minutes=375, questionable_stale_minutes=10, vix_end=None):
    """Retain session rows; excluded observations become missing, never compressed or filled."""
    _ordered(daily,'panel')
    d = daily.set_index('session_date').copy()
    asset = d.asset.iloc[0]
    if scenario not in ('eligible','exclude_questionable'):
        raise ValueError('Unknown sensitivity scenario')
    if asset=='NIFTY' and vix_end is not None:
        d = d.loc[d.index<=pd.Timestamp(vix_end)]
    full = d.expected_minutes.eq(full_session_minutes) & d.schedule_verified & d.expected_session
    questionable = d.extreme_return_flags.gt(0) | d.max_unchanged_run_minutes.ge(questionable_stale_minutes)
    excluded = questionable if scenario=='exclude_questionable' else pd.Series(False,index=d.index)
    # Complete verified special sessions are genuine native-calendar observations.
    # Preserve their measured duration; never extrapolate their RV to a normal day.
    rv_ok = d.schedule_verified & d.expected_session & d.rv_eligible & d.session_complete & ~excluded
    frame = pd.DataFrame(index=d.index)
    frame['asset'] = asset
    frame['origin_timestamp'] = d.session_close
    frame['session_open'] = d.session_open
    frame['rv'] = d[f'rv_{frequency}min'].where(rv_ok)
    frame['intraday'] = frame.rv
    endpoint_exclusion = excluded | excluded.shift(fill_value=False)
    frame['overnight_squared'] = d.overnight_squared_return.where(d.overnight_endpoints_valid & ~endpoint_exclusion)
    frame['intraday_overnight'] = frame.rv+frame.overnight_squared
    # Spot close-to-close return from the SAME minute series, never daily NIFTY TRI.
    frame['spot_return'] = d.close_to_close_log_return.where(~endpoint_exclusion)
    frame['spot_c2c_squared'] = (frame.spot_return**2).where(d.schedule_verified & d.expected_session & ~excluded)
    frame['vix_implied_variance'] = np.nan
    frame['vix_available_at'] = pd.Series(pd.NaT,index=d.index,dtype='datetime64[ns, Asia/Kolkata]')
    frame['vix_source_session'] = pd.NaT
    if asset=='NIFTY':
        v = vix.set_index('session_date').reindex(d.index)
        values = (v.vix_eod_percent/100)**2
        values = values.where(v.vix_eod_available.eq(True))
        lagged = values.shift(vix_extra_lag)
        available = v.vix_observation_available_at.shift(vix_extra_lag)
        valid = available.le(frame.origin_timestamp) & np.isfinite(lagged) & lagged.gt(0)
        frame['vix_implied_variance'] = lagged.where(valid)
        frame['vix_available_at'] = available.where(valid)
        frame['vix_source_session'] = d.index.to_series().shift(vix_extra_lag).where(valid)
    frame['data_quality_status'] = 'PROVISIONAL'
    frame['questionable'] = questionable
    frame['rv_eligible'] = rv_ok
    frame['nonstandard_duration'] = ~d.expected_minutes.eq(full_session_minutes)
    reasons=[]
    for idx,row in d.iterrows():
        flags=[]
        if not row.schedule_verified: flags.append('unverified_schedule')
        if not row.session_complete: flags.append('missing_or_invalid_minutes')
        if excluded.loc[idx]: flags.append('questionable_session_sensitivity_exclusion')
        reasons.append(';'.join(flags))
    frame['exclusion_reason'] = reasons
    return frame
