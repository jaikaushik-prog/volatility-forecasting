"""Alert classification with hysteresis and complete, self-explaining alert records.

Alerts are advisory and non-directional. Nothing here reads positions or emits orders. A record has two
separate blocks: `risk` (the forecast risk level) and `reliability` (how far to trust it).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import norm

LEVELS = ('NORMAL','ELEVATED','CRITICAL')
RANK = {level:i for i,level in enumerate(LEVELS)}
OPERATIONAL = ('DATA_UNAVAILABLE','DATA_STALE','MODEL_FAILURE')
BANNED_PHRASES = ('sell','buy','reduce position','rebalance','crash','bearish','decline expected','will fall')


def raw_level(vol, elevated, critical):
    if not np.isfinite(vol) or vol <= 0:
        return 'MODEL_FAILURE'
    if vol >= critical: return 'CRITICAL'
    if vol >= elevated: return 'ELEVATED'
    return 'NORMAL'


def classify(vols, elevated, critical, deescalate_after=3, operational=None):
    """Escalate immediately; step down one level only after `deescalate_after` sessions below the lower bound.

    An operational state (missing, stale or failed forecast) is reported as itself and never as NORMAL.
    It does not reset the hysteresis counter, so the last valid level resumes when data return.
    """
    if not 0 < elevated < critical:
        raise ValueError('Require 0 < elevated < critical')
    if deescalate_after < 1:
        raise ValueError('deescalate_after must be at least 1')
    vols = np.asarray(vols,dtype=float)
    operational = [None]*len(vols) if operational is None else list(operational)
    out, current, below = [], 'NORMAL', 0
    for vol, op in zip(vols, operational):
        if op is not None:
            if op not in OPERATIONAL: raise ValueError(f'Unknown operational state {op!r}')
            out.append(op); continue
        level = raw_level(vol, elevated, critical)
        if level == 'MODEL_FAILURE':
            out.append(level); continue
        if RANK[level] > RANK[current]:
            current, below = level, 0
        elif RANK[level] < RANK[current]:
            below += 1
            if below >= deescalate_after:
                current, below = LEVELS[RANK[current]-1], 0
        else:
            below = 0
        out.append(current)
    return out


def exceedance_probability(variance, threshold_abs_return, method='normal', standardized=None):
    """Secondary measure: P(|r_next| > c) = P(|z| > c / sigma), non-directional by construction."""
    if not np.isfinite(variance) or variance <= 0 or threshold_abs_return <= 0:
        return np.nan
    k = threshold_abs_return/np.sqrt(variance)
    if method == 'normal':
        return float(2*norm.sf(k))
    if method == 'filtered_historical':
        z = np.asarray(standardized,dtype=float); z = z[np.isfinite(z)]
        if len(z) < 250: raise ValueError('Filtered historical probability needs at least 250 standardized returns')
        return float(np.mean(np.abs(z) > k))
    raise ValueError(f'Unknown probability method {method!r}')


def percentile_of(value, reference):
    reference = np.asarray(reference,dtype=float); reference = reference[np.isfinite(reference)]
    return float(100*np.mean(reference <= value)) if len(reference) else np.nan


REASONS = {
    'NORMAL':'Forecast volatility is below the elevated threshold.',
    'ELEVATED':'Forecast volatility is at or above the development {p_e:g}th percentile ({t_e:.1%} annualized).',
    'CRITICAL':'Forecast volatility is at or above the development {p_c:g}th percentile ({t_c:.1%} annualized).',
    'DATA_UNAVAILABLE':'Required input data for the just-closed session are unavailable; no forecast was issued.',
    'DATA_STALE':'Latest input data do not include the just-closed session; no forecast was issued.',
    'MODEL_FAILURE':'The alert model produced no valid forecast; no substitute model is used.',
}


def consensus(production_vols, critical):
    """Model disagreement among PRODUCTION models only."""
    v = np.array([x for x in production_vols.values() if np.isfinite(x) and x > 0])
    if not len(v):
        return dict(available=0,above_critical=0,dispersion=np.nan)
    return dict(available=len(v),above_critical=int((v>=critical).sum()),
                dispersion=float(v.max()/v.min()-1) if len(v) > 1 else 0.)


def provisional_panel(provisional_vols, elevated, critical):
    """Provisional models are shown with their own label; they never feed level or consensus."""
    return [dict(model=k,grade='PROVISIONAL',forecast_volatility_annualized=float(v) if np.isfinite(v) else np.nan,
                 would_be_level=raw_level(v,elevated,critical)) for k,v in sorted(provisional_vols.items())]


def build_record(*, asset, report_date, target_session, level, previous_level, forecast_variance, thresholds,
                 events, percentile, model, model_version, production_vols, provisional_vols, reliability,
                 limitations, standardized=None, probability_method='normal', held_level=None):
    valid = level in LEVELS and np.isfinite(forecast_variance) and forecast_variance > 0
    vol = float(np.sqrt(252*forecast_variance)) if valid else np.nan
    prob = lambda c: exceedance_probability(forecast_variance,c,probability_method,standardized) if valid else np.nan
    reason = REASONS[level].format(p_e=thresholds['elevated_percentile'],p_c=thresholds['critical_percentile'],
                                   t_e=thresholds['elevated'],t_c=thresholds['critical'])
    if valid and held_level is not None and RANK[held_level] > RANK[raw_level(vol,thresholds['elevated'],thresholds['critical'])]:
        reason += ' Level held by the de-escalation rule although the latest forecast is lower.'
    c = consensus(production_vols,thresholds['critical'])
    risk = dict(asset=asset,report_date=str(report_date),target_session=str(target_session),horizon_sessions=1,
        alert_level=level,previous_alert_level=previous_level,forecast_volatility_annualized=vol,
        forecast_variance=float(forecast_variance) if valid else np.nan,
        threshold_elevated=thresholds['elevated'],threshold_critical=thresholds['critical'],
        forecast_percentile_vs_development=percentile,
        prob_abs_return_above_elevated_event=prob(events['elevated']),
        prob_abs_return_above_critical_event=prob(events['critical']),probability_method=probability_method,
        reason=reason,model=model,model_version=model_version)
    rel = dict(reliability)
    rel.update(production_models_available=c['available'],production_models_above_critical=c['above_critical'],
               production_forecast_dispersion=c['dispersion'],
               provisional_panel=provisional_panel(provisional_vols,thresholds['elevated'],thresholds['critical']))
    return dict(risk=risk,reliability=rel,limitations=list(limitations))


def validate_record(record, risk_fields, reliability_fields, required_limitations=()):
    for block, fields in (('risk',risk_fields),('reliability',reliability_fields)):
        missing = [k for k in fields if k not in record.get(block,{})]
        if missing: raise ValueError(f'Alert {block} block missing fields: {missing}')
    risk = record['risk']
    if risk['alert_level'] not in LEVELS+OPERATIONAL: raise ValueError('Invalid alert level')
    if risk['horizon_sessions'] != 1: raise ValueError('Primary horizon is one session')
    if not record.get('limitations'): raise ValueError('Alert must state model limitations')
    for text in required_limitations:
        if text not in record['limitations']: raise ValueError(f'Missing limitation: {text}')
    for entry in record['reliability']['provisional_panel']:
        if entry.get('grade') != 'PROVISIONAL': raise ValueError('Provisional panel entries must be labelled')
    lowered = risk['reason'].lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered: raise ValueError('Alert reasons must be non-directional and must not recommend trades')
    return True


def burden(levels, sessions_per_year=252):
    """Descriptive alert burden: share of sessions per level and entries per year into each escalated level."""
    s = pd.Series(levels)
    entries = {lvl:int(((s==lvl)&(s.shift(1)!=lvl)).sum()) for lvl in ('ELEVATED','CRITICAL')}
    years = len(s)/sessions_per_year
    return dict(sessions=len(s),**{f'share_{l.lower()}':float((s==l).mean()) for l in LEVELS},
                **{f'entries_per_year_{k.lower()}':v/years for k,v in entries.items()},
                mean_critical_episode_sessions=float((s=='CRITICAL').sum()/entries['CRITICAL']) if entries['CRITICAL'] else np.nan)
