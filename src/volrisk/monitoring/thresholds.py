"""Draft development-only thresholds. Rows after each development window are filtered at read time."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from .alerts import classify, burden

DAILY_COLUMNS = ['asset','model','target_date','forecast_variance','forecast_volatility_annualized','forecast_valid',
                 'realized_log_return','realized_squared_return']
STAGE4_COLUMNS = ['asset','model','target','frequency','scenario','target_date','forecast_variance',
                  'forecast_volatility_annualized','forecast_valid','observed_variance']


def read_window(path, columns, start, end, extra_filter=None):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    expression = (ds.field('target_date') >= start) & (ds.field('target_date') <= end)
    if extra_filter is not None: expression = expression & extra_filter
    frame = ds.dataset(Path(path)).to_table(columns=columns,filter=expression).to_pandas()
    if len(frame) and frame.target_date.max() > end:
        raise ValueError('Read returned a row after the development window')
    return frame


def _percentiles(values, lower, upper):
    v = np.asarray(values,dtype=float); v = v[np.isfinite(v)&(v>0)]
    return len(v), (float(np.percentile(v,lower)) if len(v) else np.nan), (float(np.percentile(v,upper)) if len(v) else np.nan)


def production_thresholds(config, root='.'):
    m = config['models']; a = config['alerts']; e = config['events']; prod = m['production']
    start, end = m['development_window']
    frames = [read_window(Path(root)/m[key]/'forecasts.parquet',DAILY_COLUMNS,start,end,
                          ds.field('asset').isin(prod['assets'])&ds.field('model').isin(prod['names']))
              for key in ('source_run','advanced_source_run')]
    f = pd.concat(frames,ignore_index=True).drop_duplicates(['asset','model','target_date'])
    f = f[f.forecast_valid.astype(bool)]
    rows, burdens, standardized = [], [], {}
    for (asset,model),g in f.groupby(['asset','model']):
        n, te, tc = _percentiles(g.forecast_volatility_annualized,a['elevated_percentile'],a['critical_percentile'])
        rows.append(dict(grade='PRODUCTION',asset=asset,model=model,role='alert_model' if model == m['alert_model'] else 'production_shadow',
                         development_start=start,development_end=end,development_forecasts=n,
                         first_target=str(g.target_date.min().date()),last_target=str(g.target_date.max().date()),
                         threshold_elevated=te,threshold_critical=tc))
        if model == m['alert_model']:
            g = g.sort_values('target_date')
            burdens.append(dict(grade='PRODUCTION',asset=asset,model=model,
                                **burden(classify(g.forecast_volatility_annualized,te,tc,a['deescalation_consecutive_sessions']))))
            z = g.realized_log_return/np.sqrt(g.forecast_variance)
            standardized[asset] = z[np.isfinite(z)].to_numpy()
    events = []
    for asset,g in f.drop_duplicates(['asset','target_date']).groupby('asset'):
        absr = np.sqrt(g.realized_squared_return.to_numpy())
        n, ce, cc = _percentiles(absr,e['elevated_realized_percentile'],e['critical_realized_percentile'])
        events.append(dict(grade='PRODUCTION',asset=asset,measure=e['measure'],development_sessions=n,
                           event_elevated_abs_return=ce,event_critical_abs_return=cc,
                           base_rate_elevated=float(np.mean(absr>ce)),base_rate_critical=float(np.mean(absr>cc))))
    return pd.DataFrame(rows),pd.DataFrame(events),pd.DataFrame(burdens),standardized


def provisional_thresholds(config, root='.', frequency=5, scenario='eligible'):
    """Stage 4 models on the common close-to-close target (NIFTY/SENSEX spot). Labelled PROVISIONAL throughout."""
    prov = config['models']['provisional']; a = config['alerts']
    start, end = prov['existing_development_window']
    flt = (ds.field('frequency').isin([frequency])&ds.field('scenario').isin([scenario])
           &ds.field('target').isin(['spot_c2c_squared'])&ds.field('model').isin(prov['existing_close_to_close']))
    f = read_window(Path(root)/prov['existing_source_run']/'forecasts.parquet',STAGE4_COLUMNS,start,end,flt)
    f = f[f.forecast_valid.astype(bool)]
    rows = []
    for (asset,model),g in f.groupby(['asset','model']):
        n, te, tc = _percentiles(g.forecast_volatility_annualized,a['elevated_percentile'],a['critical_percentile'])
        rows.append(dict(grade='PROVISIONAL',asset=f'{asset}_spot',model=model,role='provisional_shadow',
                         development_start=start,development_end=end,development_forecasts=n,
                         first_target=str(g.target_date.min().date()),last_target=str(g.target_date.max().date()),
                         threshold_elevated=te,threshold_critical=tc))
    return pd.DataFrame(rows)
