"""Daily NIFTY risk brief: explicit inputs, reproducible forecasts, immutable issuance.

This is a separate, narrow monitoring MVP. It does not execute the full H4 study.
Preview accepts only pre-2025 dates. Live issuance requires a frozen registration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import tomllib

import numpy as np
import pandas as pd

from volrisk.data.models import DataError
from volrisk.data.nse_csv import read_tri_csv
from volrisk.data.nse_json import read_tri_json
from volrisk.data.storage import sha256, write_json, write_text
from volrisk.forecasting.base import _json_ready
from volrisk.forecasting.registry import build_model
from volrisk.evaluation.walk_forward import run_walk_forward
from .alerts import LEVELS, RANK, raw_level, exceedance_probability
from .ledger import Ledger, digest


def load_settings(path):
    path = Path(path).resolve()
    with path.open('rb') as handle:
        cfg = tomllib.load(handle)
    root = path.parent.parent
    if cfg['protocol']['status'] not in {'DRAFT','FROZEN'} or cfg['protocol']['advisory_only'] is not True:
        raise ValueError('Expected an advisory-only DRAFT or FROZEN protocol')
    r = cfg['report']
    if r['asset'] != 'NIFTY50_TRI' or r['alert_model'] not in r['models']:
        raise ValueError('NIFTY50_TRI and an explicitly designated alert model are required')
    if len(set(r['models'])) != len(r['models']) or set(r['models']) != {'gjr_normal','ewma_094','rolling_20'}:
        raise ValueError('The MVP runs GJR, EWMA and rolling-20 only')
    if r['sessions_per_year'] != 252 or r['probability_method'] != 'normal':
        raise ValueError('MVP uses 252 sessions/year and explicitly unvalidated normal probabilities')
    if type(r['deescalation_sessions']) is not int or r['deescalation_sessions'] < 1:
        raise ValueError('deescalation_sessions must be a positive integer')
    if pd.Timestamp(r['preview_cutoff']) > pd.Timestamp('2024-12-31'):
        raise ValueError('Preview must not use the sealed later period')
    paths = {k:(root/v).resolve() for k,v in cfg['inputs'].items()}
    with paths['model_config'].open('rb') as handle:
        models = tomllib.load(handle)['models']
    for name in r['models']:
        if name not in models: raise ValueError(f'Missing model specification: {name}')
    cfg['_paths'] = paths; cfg['_models'] = {n:models[n] for n in r['models']}
    cfg['_config_path'] = path
    return cfg


def fingerprint(cfg):
    package = Path(__file__).resolve().parents[1]
    return dict(config=sha256(cfg['_config_path']),python=platform.python_version(),
        inputs={k:sha256(v) for k,v in cfg['_paths'].items()},
        code={str(p.relative_to(package)).replace('\\','/'):sha256(p) for p in sorted(package.rglob('*.py'))},
        packages={p:version(p) for p in ('numpy','pandas','scipy','arch','statsmodels','pyarrow')})


def utc_timestamp(value):
    ts = pd.Timestamp(value)
    if ts.tzinfo is None: raise ValueError('Timestamp must contain a UTC offset')
    return ts.tz_convert('UTC')


def register(config_path, destination, approved_by):
    cfg = load_settings(config_path)
    if cfg['protocol']['status'] != 'FROZEN' or not approved_by.strip():
        raise ValueError('Registration needs FROZEN status and a recorded reviewer')
    payload = dict(protocol=cfg['protocol'],approved_by=approved_by.strip(),
        registered_at=datetime.now(timezone.utc).isoformat(),fingerprint=fingerprint(cfg))
    destination = Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('x',encoding='utf-8') as handle:
        json.dump(payload,handle,indent=2,allow_nan=False)
    return payload


class Calendar:
    def __init__(self, path):
        self.market = json.loads(Path(path).read_text(encoding='utf-8'))['markets']['NSE']

    def verified(self, day):
        day = pd.Timestamp(day)
        m = self.market
        return (pd.Timestamp(m['verified_start']) <= day <= pd.Timestamp(m['verified_end'])
            and day.year not in m.get('unverified_years',[])
            and day.strftime('%Y-%m-%d') not in m.get('unverified_dates',[]))

    def is_session(self, day):
        day = pd.Timestamp(day); key = day.strftime('%Y-%m-%d')
        return key in self.market.get('special_sessions',[]) or (
            day.dayofweek < 5 and key not in self.market.get('holidays',[]))

    def sessions(self, start, end):
        return pd.DatetimeIndex([d for d in pd.date_range(start,end) if self.is_session(d)])

    def next_session(self, day):
        for d in pd.date_range(pd.Timestamp(day)+pd.Timedelta(days=1),periods=31):
            if not self.verified(d): raise ValueError('Next session is outside verified calendar coverage')
            if self.is_session(d): return d
        raise ValueError('No verified next session found')


def _thresholds(cfg):
    r = cfg['report']; paths = cfg['_paths']
    a = pd.read_csv(paths['alert_thresholds'])
    a = a[(a.asset==r['asset'])&(a.model==r['alert_model'])]
    e = pd.read_csv(paths['event_thresholds']); e = e[e.asset==r['asset']]
    if len(a) != 1 or len(e) != 1: raise ValueError('Threshold rows must be unique and match asset/model')
    a,e = a.iloc[0],e.iloc[0]
    values = [a.threshold_elevated,a.threshold_critical,e.event_elevated_abs_return,e.event_critical_abs_return]
    if not np.isfinite(values).all() or not 0 < values[0] < values[1] or not 0 < values[2] < values[3]:
        raise ValueError('Invalid alert/event thresholds')
    return dict(elevated=float(values[0]),critical=float(values[1]),
        event_elevated=float(values[2]),event_critical=float(values[3]),
        basis='Saved development thresholds; no thresholds fitted to report outcomes')


def read_prices(source, as_of, calendar):
    """Read one official export. No fills; missing sessions break the return history."""
    source = Path(source)
    reader = read_tri_json if source.suffix.lower()=='.json' else read_tri_csv
    frame, issues, metadata = reader(source)
    if frame.date.isna().any(): raise DataError('Invalid dates in source')
    # Reject future observations before converting price strings or computing returns.
    if (frame.date > as_of).any(): raise DataError('Source contains observations after the report date; provide an as-of export')
    if frame.date.duplicated().any(): raise DataError('Duplicate source dates; reconcile the export before issuance')
    frame = frame.sort_values('date')
    numeric = pd.to_numeric(frame.price,errors='coerce')
    if frame.price.map(lambda x: isinstance(x,(bool,np.bool_))).any(): raise DataError('Boolean values are not prices')
    if not np.isfinite(numeric).all() or (numeric <= 0).any(): raise DataError('Prices must be finite and positive')
    dates = pd.DatetimeIndex(frame.date)
    if any(not calendar.verified(d) for d in dates): raise DataError('Source history includes unverified calendar dates')
    if any(not calendar.is_session(d) for d in dates): raise DataError('Source contains a non-trading date')
    expected = calendar.sessions(dates.min(),as_of)
    prices = pd.Series(numeric.to_numpy(dtype=float),index=dates).reindex(expected)
    missing = prices.index[prices.isna()].strftime('%Y-%m-%d').tolist()
    if missing:
        issues.append(dict(code='missing_sessions',severity='warning',message=f'{len(missing)} missing sessions; no prices filled',dates=missing))
    returns = np.log(prices/prices.shift(1)).iloc[1:]
    extremes = returns.index[returns.abs() > np.log(1.10)].strftime('%Y-%m-%d').tolist()
    if extremes:
        issues.append(dict(code='large_moves',severity='warning',message='Large moves retained for review',dates=extremes))
    unchanged = prices.eq(prices.shift(1))
    if unchanged.rolling(3,min_periods=3).sum().eq(3).any():
        issues.append(dict(code='unchanged_prices',severity='warning',message='At least three consecutive unchanged returns; review source'))
    return returns,issues,dict(metadata,last_return_date=str(dates.max().date()),
        observations=len(frame),missing_sessions=len(missing))


def forecast_models(returns, cfg):
    forecasts = []
    for name in cfg['report']['models']:
        try:
            model = build_model(name,cfg['_models'][name])
            run = run_walk_forward(returns,model,asset='NIFTY50_TRI',min_history=252,missing_policy='reset')
            final = run.forecasts.iloc[-1] if len(run.forecasts) else None
            valid = (final is not None and final.origin_date==returns.index[-1]
                     and bool(final.forecast_valid) and final.converged is not False)
            # Unlike historical research, a nonconverged optimizer cannot issue an MVP alert.
            if final is not None and pd.notna(final.converged) and not bool(final.converged): valid = False
            forecasts.append(dict(model=name,variance=float(final.forecast_variance) if valid else None,
                annualized_volatility=float(final.forecast_volatility_annualized) if valid else None,
                status=str(final.fit_status) if valid else 'failed',
                message=str(final.fit_message) if final is not None else 'Insufficient contiguous history',
                last_fit_date=str(pd.Timestamp(final.last_fit_date).date()) if valid else None))
        except Exception as exc:
            forecasts.append(dict(model=name,variance=None,annualized_volatility=None,status='failed',
                message=f'{type(exc).__name__}: {exc}',last_fit_date=None))
    return forecasts


def advance(previous, raw, consecutive, interrupted=False):
    """MVP policy: missing sessions reset the consecutive-session counter, retaining last risk level."""
    state = dict(previous or dict(held_level='NORMAL',below_count=0))
    if interrupted or raw not in LEVELS:
        state['below_count'] = 0
    if raw not in LEVELS: return state
    if RANK[raw] > RANK[state['held_level']]:
        state = dict(held_level=raw,below_count=0)
    elif RANK[raw] < RANK[state['held_level']]:
        state['below_count'] += 1
        if state['below_count'] >= consecutive:
            state = dict(held_level=LEVELS[RANK[state['held_level']]-1],below_count=0)
    else:
        state['below_count'] = 0
    return state


def _authorize(cfg, mode, as_of, registration, now, source_confirmed):
    if mode in {'demo','preview'}:
        if as_of > pd.Timestamp(cfg['report']['preview_cutoff']):
            raise ValueError('Preview is restricted to pre-2025 dates. Live reports require frozen registration.')
        return
    if mode != 'live': raise ValueError('Unknown report mode')
    if cfg['protocol']['status'] != 'FROZEN' or not registration:
        raise ValueError('Live issuance requires a FROZEN protocol and registration')
    registered = json.loads(Path(registration).read_text(encoding='utf-8'))
    if registered.get('fingerprint') != fingerprint(cfg) or not registered.get('approved_by','').strip():
        raise ValueError('Registration does not match the reviewed code, inputs, configuration and packages')
    start = utc_timestamp(registered['registered_at'])
    origin_open = (as_of+pd.Timedelta(hours=9,minutes=15)).tz_localize('Asia/Kolkata').tz_convert('UTC')
    if not start < origin_open or start > now:
        raise ValueError('Live origin session must start strictly after registration')
    close = (as_of+pd.Timedelta(hours=15,minutes=30)).tz_localize('Asia/Kolkata').tz_convert('UTC')
    if now < close: raise ValueError('The origin session has not closed')
    if not source_confirmed: raise ValueError('Confirm official NIFTY gross TRI source identity for live reports')


@contextmanager
def issuance_lock(directory):
    """Serialize issuances, including state reads. Crashed locks require explicit inspection/removal."""
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    lock=directory/'.issuance.lock'
    try:
        handle=lock.open('x',encoding='utf-8')
    except FileExistsError:
        raise ValueError(f'An issuance is running or its lock needs recovery: {lock}') from None
    try:
        with handle: json.dump(dict(pid=os.getpid(),started_at=datetime.now(timezone.utc).isoformat()),handle)
        yield
    finally:
        lock.unlink()


def run_daily(*, config, source, as_of, output, mode='preview', registration=None,
              source_confirmed=False, retrieved_at=None, now=None):
    if mode not in {'demo','preview','live'}: raise ValueError('Unknown report mode')
    with issuance_lock(Path(output)/mode):
        return _run_daily(config=config,source=source,as_of=as_of,output=output,mode=mode,
            registration=registration,source_confirmed=source_confirmed,retrieved_at=retrieved_at,now=now)


def _run_daily(*, config, source, as_of, output, mode='preview', registration=None,
              source_confirmed=False, retrieved_at=None, now=None):
    cfg = load_settings(config); as_of = pd.Timestamp(as_of)
    if as_of.tzinfo is not None or as_of != as_of.normalize(): raise ValueError('as_of must be a session date')
    now = utc_timestamp(now or datetime.now(timezone.utc))
    _authorize(cfg,mode,as_of,registration,now,source_confirmed)
    retrieved = utc_timestamp(retrieved_at) if retrieved_at else None
    if retrieved is not None and retrieved > now: raise ValueError('Retrieval timestamp cannot be in the future')
    output = Path(output).resolve()/mode; output.mkdir(parents=True,exist_ok=True)
    calendar = Calendar(cfg['_paths']['calendar']); thresholds = _thresholds(cfg)
    source = Path(source).resolve()
    source_hash = sha256(source) if source.is_file() else None
    context = dict(as_of=str(as_of.date()),source_sha256=source_hash,mode=mode,
        settings=fingerprint(cfg),source_confirmed=bool(source_confirmed),
        retrieved_at=str(retrieved) if retrieved is not None else None)
    run_id = f'{as_of.date()}_{digest(context)[:16]}'
    with Ledger(output/'ledger.sqlite3') as ledger:
        existing = ledger.get('alert',run_id)
        if existing is not None:
            return publish(existing,output,ledger)
        prior = ledger.records('alert')
        if prior:
            if prior[-1]['as_of'] > str(as_of.date()): raise ValueError('Reports must be issued in chronological order')
            if any(p['as_of']==str(as_of.date()) and p['level'] in LEVELS for p in prior):
                raise ValueError('A valid forecast was already issued for this session; it cannot be replaced')
        issues=[]; metadata={}; forecasts=[]; target=None; status=None
        if not calendar.verified(as_of) or not calendar.is_session(as_of):
            status='DATA_UNAVAILABLE'; issues.append(dict(code='calendar',severity='error',message='Origin is not a verified trading session'))
        else:
            try: target=calendar.next_session(as_of)
            except ValueError as exc:
                status='DATA_UNAVAILABLE'; issues.append(dict(code='calendar',severity='error',message=str(exc)))
        if mode=='live' and target is not None:
            deadline=(target+pd.Timedelta(hours=9,minutes=15)).tz_localize('Asia/Kolkata').tz_convert('UTC')
            if now >= deadline: raise ValueError('Next session has already opened; refusing late forecast issuance')
            # Special session hours must be independently supplied in a later protocol.
            special=set(calendar.market.get('special_sessions',[]))
            if str(as_of.date()) in special or str(target.date()) in special:
                status='DATA_UNAVAILABLE'; issues.append(dict(code='special_session',severity='error',message='Live special-session timing is not verified by this MVP'))
        if source_hash is None:
            status='DATA_UNAVAILABLE'; issues.append(dict(code='source_missing',severity='error',message='Official TRI input file is unavailable'))
        if status is None:
            try:
                returns,input_issues,metadata=read_prices(source,as_of,calendar); issues.extend(input_issues)
                if metadata['last_return_date'] != str(as_of.date()):
                    status='DATA_STALE'; issues.append(dict(code='stale',severity='error',message='Source does not include the just-closed session'))
                elif len(returns) < 500 or not np.isfinite(returns.iloc[-500:]).all():
                    status='DATA_UNAVAILABLE'; issues.append(dict(code='history',severity='error',message='At least 500 contiguous valid daily returns are required'))
                else:
                    forecasts=forecast_models(returns,cfg)
            except (DataError,ValueError,OSError) as exc:
                status='DATA_UNAVAILABLE'; issues.append(dict(code='invalid_source',severity='error',message=str(exc)))
        if source_hash is not None and sha256(source) != source_hash:
            raise ValueError('Input changed during processing; retry with a stable export')
        active=next((f for f in forecasts if f['model']==cfg['report']['alert_model']),None)
        variance=active['variance'] if active else None
        if status is None and variance is None: status='MODEL_FAILURE'
        vol=float(np.sqrt(252*variance)) if variance is not None and status is None else None
        raw=status or raw_level(vol,thresholds['elevated'],thresholds['critical'])
        previous=prior[-1] if prior else None
        interrupted=bool(previous and target is not None and previous['target_session'] != str(as_of.date()))
        state=advance(previous['state'] if previous else None,raw,cfg['report']['deescalation_sessions'],interrupted)
        level=state['held_level'] if raw in LEVELS else raw
        reasons={
            'NORMAL':'Forecast volatility is below the elevated threshold.',
            'ELEVATED':'Forecast volatility meets the elevated threshold.',
            'CRITICAL':'Forecast volatility meets the critical threshold.',
            'DATA_UNAVAILABLE':'Required source data or calendar verification is unavailable.',
            'DATA_STALE':'The latest input does not include the just-closed session.',
            'MODEL_FAILURE':'The designated alert model failed; comparison models are not substituted.'}
        reason=reasons[level]
        if level in LEVELS and level != raw:
            reason=f"Previous risk level retained until {cfg['report']['deescalation_sessions']} consecutive valid sessions justify a step down."
        actions={
            'NORMAL':'Record the routine review and continue monitoring.',
            'ELEVATED':'Review planned exposure and concentration; acknowledge before the next session opens.',
            'CRITICAL':'Escalate for a risk review; record the review and rationale before the next session opens.',
            'DATA_UNAVAILABLE':'Resolve the source or calendar issue before relying on a new estimate.',
            'DATA_STALE':'Obtain the latest official TRI export and rerun the report.',
            'MODEL_FAILURE':'Inspect model diagnostics; record the failure and rerun only after remediation.'}
        record=dict(run_id=run_id,as_of=str(as_of.date()),target_session=str(target.date()) if target is not None else None,
            mode=mode,protocol=cfg['protocol'],asset='NIFTY50_TRI',level=level,raw_level=raw,state=state,
            previous_level=previous['level'] if previous else None,reason=reason,review_action=actions[level],
            alert_model=cfg['report']['alert_model'],variance=variance if level in LEVELS else None,
            annualized_volatility=vol,daily_volatility=vol/np.sqrt(252) if vol is not None else None,
            thresholds=thresholds,forecasts=forecasts,quality_issues=issues,source_metadata=metadata,
            source_name=source.name,source_sha256=source_hash,source_confirmed=source_confirmed,
            imported_at=now.isoformat(),retrieved_at=retrieved.isoformat() if retrieved is not None else None,
            probability_method='Normal innovations, zero mean; tail probabilities are not prospectively calibrated',
            probability_elevated=exceedance_probability(variance,thresholds['event_elevated']) if level in LEVELS else None,
            probability_critical=exceedance_probability(variance,thresholds['event_critical']) if level in LEVELS else None,
            context=context,limitations=[
                'Market-index risk; this is not the risk of a stock portfolio.',
                'Volatility measures movement in either direction and is not a directional trading signal.',
                'Advisory only. Review tasks do not change positions.',
                'Normal-distribution probabilities can underestimate tail risk and are unvalidated.',
                'Preview and demo outputs provide no independent evidence of forecasting performance.'])
        record=_json_ready(record)
        if fingerprint(cfg)!=context['settings']:
            raise ValueError('Code or configuration changed during issuance; retry after changes are complete')
        run_dir=output/'runs'/run_id; run_dir.mkdir(parents=True,exist_ok=True)
        if source_hash:
            snapshot=run_dir/f'source{source.suffix.lower()}'
            if snapshot.exists():
                if sha256(snapshot)!=source_hash: raise ValueError('Snapshot integrity check failed')
            else:
                payload=source.read_bytes()
                if hashlib.sha256(payload).hexdigest()!=source_hash: raise ValueError('Source changed before snapshot')
                with snapshot.open('xb') as handle: handle.write(payload)
        ledger.append_batch([('forecast',run_id,dict(run_id=run_id,as_of=record['as_of'],forecasts=forecasts,
            source_sha256=source_hash,context=context)),('alert',run_id,record)])
        return publish(record,output,ledger)


def publish(record, output, ledger):
    from .daily_reporting import render_html, render_markdown
    run_dir=Path(output)/'runs'/record['run_id']; run_dir.mkdir(parents=True,exist_ok=True)
    write_json(record,run_dir/'report.json')
    write_text(render_markdown(record),run_dir/'report.md')
    write_text(render_html(record),run_dir/'report.html')
    # Never move latest backwards when an old, identical report is requested again.
    latest=ledger.records('alert')[-1]
    write_text(render_html(latest),Path(output)/'report.html')
    write_text(render_markdown(latest),Path(output)/'report.md')
    write_json(latest,Path(output)/'report.json')
    write_json(dict(run_id=latest['run_id'],report=f"runs/{latest['run_id']}/report.json"),Path(output)/'latest.json')
    return record,run_dir/'report.html'
