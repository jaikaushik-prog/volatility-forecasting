"""Prospective H4 evaluation statistics. Defined now; applied only after a frozen, registered collection period."""
from __future__ import annotations
import numpy as np
from scipy.stats import norm


def wilson(successes, n, alpha=.05):
    if n == 0: return (np.nan,np.nan)
    z = norm.ppf(1-alpha/2); p = successes/n
    centre = (p+z*z/(2*n))/(1+z*z/n); half = z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return (float(centre-half),float(centre+half))


def detection(alert, event, alpha=.05):
    """Precision, recall, false-positive rate and missed-event rate on matched sessions."""
    a = np.asarray(alert,dtype=bool); e = np.asarray(event,dtype=bool)
    if a.shape != e.shape: raise ValueError('Alert and event series must align')
    tp, fp = int((a&e).sum()), int((a&~e).sum()); fn, tn = int((~a&e).sum()), int((~a&~e).sum())
    n = len(a)
    out = dict(sessions=n,alerts=tp+fp,events=tp+fn,true_positive=tp,false_positive=fp,false_negative=fn,true_negative=tn,
        base_rate=(tp+fn)/n if n else np.nan,alert_rate=(tp+fp)/n if n else np.nan,
        precision=tp/(tp+fp) if tp+fp else np.nan,recall=tp/(tp+fn) if tp+fn else np.nan,
        false_positive_rate=fp/(fp+tn) if fp+tn else np.nan,missed_event_rate=fn/(tp+fn) if tp+fn else np.nan,
        false_discovery_rate=fp/(tp+fp) if tp+fp else np.nan)
    out['precision_ci'] = wilson(tp,tp+fp,alpha); out['recall_ci'] = wilson(tp,tp+fn,alpha)
    out['false_positive_rate_ci'] = wilson(fp,fp+tn,alpha); out['missed_event_rate_ci'] = wilson(fn,tp+fn,alpha)
    out['lift'] = out['precision']/out['base_rate'] if out['base_rate'] else np.nan
    return out


def _clean(h, y):
    h = np.asarray(h,dtype=float); y = np.asarray(y,dtype=float)
    ok = np.isfinite(h)&(h>0)&np.isfinite(y)
    return h[ok], y[ok]


def qlike(forecast_variance, realized):
    h, y = _clean(forecast_variance,realized)
    return float(np.mean(np.log(h)+y/h)) if len(h) else np.nan


def calibration_ratio(forecast_variance, realized):
    h, y = _clean(forecast_variance,realized)
    return float(y.mean()/h.mean()) if len(h) else np.nan


def mincer_zarnowitz(forecast_variance, realized):
    """OLS of realized on forecast variance; a calibrated forecast has intercept 0 and slope 1."""
    h, y = _clean(forecast_variance,realized)
    if len(h) < 3: return dict(n=len(h),intercept=np.nan,slope=np.nan,r2=np.nan)
    X = np.c_[np.ones(len(h)),h]; beta, *_ = np.linalg.lstsq(X,y,rcond=None)
    resid = y-X@beta; r2 = 1-resid.var()/y.var() if y.var() > 0 else np.nan
    return dict(n=len(h),intercept=float(beta[0]),slope=float(beta[1]),r2=float(r2))


def brier(probability, event):
    p = np.asarray(probability,dtype=float); e = np.asarray(event,dtype=float)
    ok = np.isfinite(p)&np.isfinite(e)
    if not ok.any(): return dict(n=0,brier=np.nan,reference=np.nan,skill=np.nan)
    p, e = p[ok], e[ok]
    score = float(np.mean((p-e)**2))
    return dict(n=len(p),brier=score)


def brier_skill(probability, event, base_rate):
    """Skill against a constant development base-rate forecast (fixed before evaluation, not fitted to outcomes)."""
    b = brier(probability,event)
    e = np.asarray(event,dtype=float)[np.isfinite(np.asarray(probability,dtype=float))]
    ref = float(np.mean((base_rate-e)**2)) if len(e) else np.nan
    b.update(reference=ref,skill=1-b['brier']/ref if ref else np.nan)
    return b


def reliability_bins(probability, event, edges=(0,.05,.10,.20,.30,.50,1.0)):
    p = np.asarray(probability,dtype=float); e = np.asarray(event,dtype=float)
    ok = np.isfinite(p)&np.isfinite(e); p, e = p[ok], e[ok]
    rows = []
    for lo, hi in zip(edges[:-1],edges[1:]):
        mask = (p>=lo)&((p<hi) if hi < edges[-1] else (p<=hi))
        n = int(mask.sum())
        rows.append(dict(bin_low=lo,bin_high=hi,n=n,mean_probability=float(p[mask].mean()) if n else np.nan,
                         observed_frequency=float(e[mask].mean()) if n else np.nan,
                         observed_ci=wilson(int(e[mask].sum()),n) if n else (np.nan,np.nan)))
    return rows


def operational(statuses, published_on_time):
    """Availability counts only timely, valid alert-model reports against all scheduled sessions."""
    s = np.asarray(statuses,dtype=object); t = np.asarray(published_on_time,dtype=bool)
    valid = np.isin(s,['NORMAL','ELEVATED','CRITICAL'])
    return dict(scheduled_sessions=len(s),valid_reports=int(valid.sum()),timely_valid_reports=int((valid&t).sum()),
                availability=float((valid&t).mean()) if len(s) else np.nan,
                **{f'count_{k.lower()}':int((s==k).sum()) for k in ('DATA_UNAVAILABLE','DATA_STALE','MODEL_FAILURE')})
