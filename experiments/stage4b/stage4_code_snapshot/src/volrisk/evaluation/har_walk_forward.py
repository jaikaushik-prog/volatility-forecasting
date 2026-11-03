"""Target-explicit, session-preserving walk-forward estimation for Stage 4."""
from __future__ import annotations
import time
import numpy as np
import pandas as pd

from volrisk.forecasting.base import FIT_FAILED, FitReport, annualized_volatility, params_to_json
from volrisk.forecasting.har import HARRV, RVBenchmark, origin_features, RV_FEATURES, ON_FEATURES, VIX_FEATURES
from volrisk.forecasting.ewma import EWMAVariance
from volrisk.forecasting.garch import ArchGARCH
from .walk_forward import classify_forecast, PeriodSplits


def model_specs(asset, target, config, *, include_daily=False):
    est = config['estimation']
    common = RV_FEATURES+ON_FEATURES+(VIX_FEATURES if asset=='NIFTY' else [])
    shared = {k:est[k] for k in ('window','min_observations','refit_every','floor_fraction',
                                 'nonpositive_policy','log_bias_correction')}
    shared.update(target=target,common_columns=common if est['common_training'] else [])
    specs = {'har':{'type':'har_rv',**shared},'log_har':{'type':'har_rv',**shared,'transform':'log'},
             'har_overnight':{'type':'har_rv',**shared,'overnight':True}}
    if asset=='NIFTY':
        specs.update(har_vix={'type':'har_rv',**shared,'vix':True},
                     har_vix_overnight={'type':'har_rv',**shared,'vix':True,'overnight':True})
    for name,method,window in [('previous','previous',1),('mean5','mean',5),('mean22','mean',22),('rv_ewma','ewma',22)]:
        specs[name]={'type':'rv_benchmark','target':target,'method':method,'window':window,
            'decay':config['benchmarks']['rv_ewma_decay'],'init_window':config['benchmarks']['rv_ewma_init']}
    if include_daily:
        b=config['benchmarks']
        specs['spot_ewma']={'type':'ewma','min_observations':b['daily_min_observations'],
                           'init_window':b['daily_min_observations'],'decay':.94}
        for name,vol,o in [('spot_garch','GARCH',0),('spot_egarch','EGARCH',1),('spot_gjr','GARCH',1)]:
            specs[name]={'type':'garch','vol':vol,'o':o,'dist':'normal','scale':100.,
                'window':b['daily_window'],'min_observations':b['daily_min_observations'],
                'refit_every':b['daily_refit_every']}
    return specs


def walk_forward(panel, model, *, target, splits:PeriodSplits, max_annualized_vol=5., save_forecast=None):
    """save_forecast is called before reading the target value; it receives no outcome."""
    if not splits.holdout_sealed:
        raise ValueError('Holdout must remain sealed in Stage 4')
    if not panel.index.is_unique or not panel.index.is_monotonic_increasing:
        raise ValueError('Panel dates must be sorted and unique')
    # Defense in depth for callers bypassing the Parquet loader. No features see holdout values.
    panel=panel.loc[(panel.index>=splits.development[0]) & (panel.index<=splits.validation[1])].copy()
    features=origin_features(panel)
    daily_model=getattr(model,'input_kind','daily_log_returns')=='daily_log_returns'
    if daily_model and target!='spot_c2c_squared':
        raise ValueError('Daily-return models cannot be directly ranked against intraday RV targets')
    model.reset()
    if isinstance(model,HARRV):
        columns=model.config['common_columns'] or model.columns
        predictor_valid=np.isfinite(features[columns]).all(axis=1) & features[columns].ge(0).all(axis=1)
        # Aligned to the date a supervised target becomes observed, not its predictor date.
        completed=predictor_valid.shift(fill_value=False) & np.isfinite(panel[target]) & panel[target].ge(0)
        training_counts=completed.rolling(model.config['window'],min_periods=1).sum()
    records,fits=[],[]
    last_fit=None
    report=None
    asset=panel.asset.iloc[0] if len(panel) else ''
    for i in range(len(panel)-1):
        tick=time.perf_counter()
        date=panel.index[i]
        target_date=panel.index[i+1]
        period=str(splits.label([target_date])[0])
        if period not in ('development','validation'): continue
        history=panel.iloc[:i+1]
        flag=''
        variance=np.nan
        count=0
        fit_due=last_fit is None or i-last_fit>=model.refit_every or not model.fitted or not model.supports_update
        if isinstance(model,HARRV):
            count=int(training_counts.iloc[i])
            warmup=count<model.min_observations
            fit_input=history
        elif isinstance(model,RVBenchmark):
            values=history[target].to_numpy(dtype=float)
            bad=np.flatnonzero(~np.isfinite(values) | (values<0))
            contiguous=len(values)-(int(bad[-1])+1 if len(bad) else 0)
            method=model.config['method']
            required=1 if method=='previous' else model.config['window'] if method=='mean' else model.config['init_window']
            warmup=contiguous<required
            fit_input=history
        else:
            r=history.spot_return
            bad=np.flatnonzero(~np.isfinite(r.to_numpy()))
            start=int(bad[-1])+1 if len(bad) else 0
            fit_input=r.iloc[start:]
            warmup=len(fit_input)<model.min_observations
            if not len(fit_input): model.reset();last_fit=None
            if start and (last_fit is None or last_fit<start):
                model.reset();fit_due=True
        if warmup:
            flag='warmup'
        elif fit_due:
            try:
                if daily_model:
                    report=model.fit(fit_input.to_numpy(),fit_input.index)
                elif isinstance(model,HARRV):
                    report=model.fit(fit_input,features=features.iloc[:i+1])
                else:
                    report=model.fit(fit_input)
                if report.converged is False:
                    report.status=FIT_FAILED
                    report.message='Nonconverged fit rejected: '+report.message
                if not report.usable: model.reset()
            except Exception as exc:
                model.reset()
                report=FitReport(FIT_FAILED,message=f'{type(exc).__name__}: {exc}',converged=False)
            last_fit=i
            fits.append({'asset':asset,'model':model.name,'target':target,'origin_date':date,'target_date':target_date,
                'period':period,'origin_index':i,**report.as_dict(),'params':params_to_json(report.params),
                'diagnostics':params_to_json(report.diagnostics)})
        elif model.fitted:
            try:
                model.update(float(history.spot_return.iloc[-1]),date) if daily_model else model.update(features.iloc[i],date)
            except Exception as exc:
                model.reset()
                flag='update_failed:'+str(exc)
        if not flag and model.fitted:
            try:
                if isinstance(model,HARRV):
                    cols=model.config['common_columns'] or model.columns
                    if not np.isfinite(features.iloc[i][cols].to_numpy(dtype=float)).all():
                        raise ValueError('Missing common origin features; no imputation')
                variance=float(model.forecast(1)[0])
                flag=classify_forecast(variance,252,0.,max_annualized_vol)
            except Exception as exc:
                flag='forecast_failed:'+str(exc)
        elif not flag:
            flag='fit_failed'
        if flag: variance=np.nan
        state=model.state_diagnostics() if model.fitted else {}
        row={'asset':asset,'model':model.name,'model_version':model.version,'target':target,
            'origin_date':date,'target_date':target_date,'origin_timestamp':panel.origin_timestamp.iloc[i],
            'target_open_timestamp':panel.session_open.iloc[i+1],
            'target_close_timestamp':panel.origin_timestamp.iloc[i+1],
            'forecast_created_at':panel.origin_timestamp.iloc[i]+pd.Timedelta(microseconds=1),
            'origin_index':i,'period':period,'forecast_variance':variance,
            'forecast_volatility_annualized':annualized_volatility(variance),
            'forecast_valid':not bool(flag),'forecast_flag':flag,
            'fit_status':'warmup' if flag=='warmup' else report.status if report else FIT_FAILED,
            'fit_message':report.message if report else '', 'training_observations':report.training_observations if report else count,
            'training_start':report.training_start if report else None,'training_end':report.training_end if report else None,
            'last_fit_date':panel.index[last_fit] if last_fit is not None else pd.NaT,
            'params':params_to_json(model.params if model.fitted else (report.params if report else {})),
            'raw_prediction':state.get('raw_prediction',variance), 'prediction_floored':state.get('prediction_floored',False),
            'runtime_seconds':time.perf_counter()-tick,'data_quality_status':panel.data_quality_status.iloc[i],
            'vix_source_session':panel.vix_source_session.iloc[i], 'vix_available_at':panel.vix_available_at.iloc[i]}
        if save_forecast is not None: save_forecast(dict(row))
        # The model and persistence callback cannot see these future outcomes.
        observed=panel[target].iloc[i+1]
        row['observed_variance']=float(observed) if np.isfinite(observed) and observed>=0 else np.nan
        row['target_observed']=bool(np.isfinite(row['observed_variance']))
        records.append(row)
    return pd.DataFrame(records),pd.DataFrame(fits)


def common_dates(forecasts, model_names):
    """Missing/failed models stay in the required set, even if they never produce a forecast."""
    out=forecasts.copy()
    if out.duplicated(['model','target_date']).any():
        raise ValueError('Duplicate model/target forecast')
    valid=out.forecast_valid & out.target_observed & np.isfinite(out.forecast_variance) & out.forecast_variance.gt(0)
    counts=out.loc[valid].groupby('target_date').model.nunique()
    dates=counts[counts==len(set(model_names))].index
    out['common']=valid & out.target_date.isin(dates)
    return out
