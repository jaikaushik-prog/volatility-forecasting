"""Target-specific metrics and gap-aware paired inference. No pooling across assets/targets."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from scipy import stats
from .metrics import qlike, squared_error, absolute_error, holm_adjust

KEYS=['asset','frequency','scenario','target']


def attach_har_losses(frame):
    out=frame.copy()
    good=out.forecast_valid & out.target_observed & out.forecast_variance.gt(0) & out.observed_variance.ge(0)
    for name,fn in [('qlike',qlike),('se',squared_error),('ae',absolute_error)]:
        out['loss_'+name]=np.nan
        out.loc[good,'loss_'+name]=fn(out.loc[good,'forecast_variance'],out.loc[good,'observed_variance'])
    return out


def summarize_har(frame,fits):
    records=[]
    for keys,g in frame.groupby(KEYS+['period','model'],sort=True):
        base=dict(zip(KEYS+['period','model'],keys))
        fit_group=fits
        for col in KEYS+['period','model']:
            if col in fit_group: fit_group=fit_group[fit_group[col].eq(base[col])]
        for sample in ('all_available','common'):
            ok=g.loss_qlike.notna() & (g.common if sample=='common' else True)
            selected=g.loc[ok].sort_values('origin_index')
            h,y=selected.forecast_variance,selected.observed_variance
            mh,my=h.mean(),y.mean()
            changes=np.log(h).diff().where(selected.origin_index.diff().eq(1))
            attempted=g.forecast_flag.ne('warmup')
            records.append(base | {'sample':sample,'status':'PROVISIONAL','n_origins':len(g),'n_evaluated':len(selected),
                'n_warmup':int((~attempted).sum()),'prediction_failure_rate':float((~g.loc[attempted,'forecast_valid']).mean()) if attempted.any() else np.nan,
                'n_missing_targets':int((~g.target_observed).sum()),'qlike':selected.loss_qlike.mean(),
                'mse':selected.loss_se.mean(),'mae':selected.loss_ae.mean(),'bias':mh-my,
                'calibration_ratio':my/mh if mh>0 else np.nan,
                'forecast_stability':changes.abs().mean(),'underprediction_fraction':float((h<y).mean()) if len(h) else np.nan,
                'runtime_seconds':float(g.runtime_seconds.sum()),'fit_attempts':len(fit_group),
                'estimation_failure_rate':float(fit_group.status.eq('failed').mean()) if len(fit_group) else np.nan,
                'prediction_floor_count':int(g.prediction_floored.sum()),
                'first_target':selected.target_date.min(),'last_target':selected.target_date.max()})
    table=pd.DataFrame(records)
    if len(table):
        table['rank_qlike']=np.nan
        table['rank_calibration']=np.nan
        mask=table['sample'].eq('common') & table.n_evaluated.gt(0)
        table.loc[mask,'rank_qlike']=table.loc[mask].groupby(KEYS+['period']).qlike.rank(method='min')
        distance=np.abs(np.log(table.loc[mask,'calibration_ratio']))
        table.loc[mask,'rank_calibration']=distance.groupby([table.loc[mask,k] for k in KEYS+['period']]).rank(method='min')
    return table


def paired_inference(differences, session_positions, *, draws=1000, block=10, seed=20261103, min_n=30):
    """Negative loss difference favours challenger. Gaps break HAC lags/bootstrap blocks."""
    d=np.asarray(differences,dtype=float)
    positions=np.asarray(session_positions,dtype=int)
    finite=np.isfinite(d)
    d,positions=d[finite],positions[finite]
    n=len(d)
    out={'n':n,'mean_loss_difference':float(d.mean()) if n else np.nan,'hac_p_value':np.nan,
         'hac_t':np.nan,'bootstrap_p_value':np.nan,'ci_low':np.nan,'ci_high':np.nan,'inference_status':'insufficient_sample'}
    if n<min_n: return out
    if len(np.unique(positions))!=n or (np.diff(positions)<=0).any():
        raise ValueError('Paired inference requires sorted unique session positions')
    centered=d-d.mean()
    lags=max(1,int(np.floor(4*(n/100)**(2/9))))
    lrv=float(centered@centered/n)
    lookup=dict(zip(positions,centered))
    for lag in range(1,lags+1):
        cov=sum(value*lookup.get(pos-lag,0.) for pos,value in zip(positions,centered))/n
        lrv+=2*(1-lag/(lags+1))*cov
    if lrv>0:
        t=float(d.mean()/np.sqrt(lrv/n))
        out.update(hac_t=t,hac_p_value=float(2*stats.t.sf(abs(t),df=n-1)))
    rng=np.random.default_rng(seed)
    # Vectorize across bootstrap replications, preserving geometric contiguous blocks.
    idx=rng.integers(n,size=draws)
    sums=centered[idx].copy()
    for _ in range(1,n):
        following=np.minimum(idx+1,n-1)
        restart=(idx+1>=n) | (positions[following]!=positions[idx]+1) | (rng.random(draws)<1/block)
        idx=np.where(restart,rng.integers(n,size=draws),following)
        sums+=centered[idx]
    means=sums/n
    low,high=np.quantile(means,[.025,.975])
    out.update(bootstrap_p_value=float((1+(np.abs(means)>=abs(d.mean())).sum())/(draws+1)),
               ci_low=float(d.mean()+low),ci_high=float(d.mean()+high),hac_lags=lags,
               contiguous_blocks=int(1+(np.diff(positions)>1).sum()),inference_status='approximate_exploratory')
    return out


def comparisons(frame,config):
    records=[]
    validation=frame[frame.period.eq('validation') & frame.common]
    for keys,g in validation.groupby(KEYS,sort=True):
        wide=g.pivot(index=['origin_index','target_date'],columns='model',values='loss_qlike').sort_index()
        if 'har' not in wide: continue
        pairs=[(name,'har') for name in wide if name!='har']
        if {'har_vix_overnight','har_overnight'}<=set(wide): pairs.append(('har_vix_overnight','har_overnight'))
        if {'har_vix_overnight','har_vix'}<=set(wide): pairs.append(('har_vix_overnight','har_vix'))
        for challenger,reference in pairs:
            diff=wide[challenger]-wide[reference]
            infer=paired_inference(diff,wide.index.get_level_values('origin_index'),draws=config['bootstrap_draws'],
                block=config['bootstrap_block'],seed=config['seed'],min_n=config['minimum_inference_observations'])
            by_date=g[g.model.eq(reference)].set_index('target_date')
            shock=by_date.reindex(wide.index.get_level_values('target_date')).retrospective_shock.to_numpy(dtype=bool)
            total_abs=np.abs(diff).sum()
            concentration=float(np.sort(np.abs(diff.to_numpy()))[-5:].sum()/total_abs) if total_abs>0 else np.nan
            records.append(dict(zip(KEYS,keys)) | {'challenger':challenger,'reference':reference,**infer,
                'mean_difference_without_shocks':float(diff.iloc[np.flatnonzero(~shock)].mean()),
                'top5_share_absolute_loss_difference':concentration,'status':'PROVISIONAL'})
    out=pd.DataFrame(records)
    if len(out):
        out['hac_p_holm']=holm_adjust(out.hac_p_value)
        out['bootstrap_p_holm']=holm_adjust(out.bootstrap_p_value)
        out['significant_after_multiplicity']=(out.hac_p_holm<config['alpha']) & (out.bootstrap_p_holm<config['alpha'])
        out['multiplicity_family']='all_predeclared_validation_asset_frequency_target_scenario_comparisons'
    return out


def label_regimes(panel,config):
    rv=panel.rv
    mean=rv.rolling(22,min_periods=22).mean()
    labels=[]
    for i,current in enumerate(mean):
        prior=mean.iloc[:i].dropna()
        if not np.isfinite(current) or len(prior)<60: labels.append('unknown');continue
        low,high=prior.quantile([1/3,2/3])
        labels.append('low' if current<=low else 'high' if current>high else 'medium')
    out=pd.DataFrame(index=panel.index)
    out['origin_regime']=labels
    out['origin_transition']=out.origin_regime.ne(out.origin_regime.shift()) & out.origin_regime.ne('unknown') & out.origin_regime.shift().isin(['low','medium','high'])
    sd=np.sqrt(panel.spot_return.pow(2).rolling(22,min_periods=22).mean())
    shock=(rv>config['shock_multiple']*mean.shift()) | (panel.spot_return < -config['shock_multiple']*sd.shift())
    recovery=shock.shift(fill_value=False).rolling(config['recovery_sessions'],min_periods=1).max().eq(1) & ~shock
    out['retrospective_shock']=shock
    out['retrospective_recovery']=recovery
    change=np.log(panel.vix_implied_variance).diff().abs()
    threshold=change.expanding(min_periods=60).quantile(.9).shift()
    out['origin_rapid_vix_change']=change.gt(threshold)
    return out


def attach_regimes(forecasts,panel,config):
    labels=label_regimes(panel,config)
    out=forecasts.copy()
    for c in labels:
        dates=out.target_date if c.startswith('retrospective') else out.origin_date
        out[c]=labels[c].reindex(dates).to_numpy()
    return out


def regime_metrics(frame):
    rows=[]
    for keys,g in frame[frame.period.eq('validation') & frame.common].groupby(KEYS+['model']):
        masks={f'origin_{x}':g.origin_regime.eq(x) for x in ('low','medium','high')}
        masks.update({c:g[c].eq(True) for c in ['origin_transition','origin_rapid_vix_change','retrospective_shock','retrospective_recovery']})
        # Fixed calendar quarters, not selected after inspecting losses.
        masks.update({f'validation_Q{q}':g.target_date.dt.quarter.eq(q) for q in (1,2,3,4)})
        for label,mask in masks.items():
            s=g.loc[mask]
            rows.append(dict(zip(KEYS+['model'],keys)) | {'regime':label,'n':len(s),'qlike':s.loss_qlike.mean(),
                'calibration_ratio':s.observed_variance.mean()/s.forecast_variance.mean() if len(s) else np.nan,
                'underprediction_fraction':float((s.forecast_variance<s.observed_variance).mean()) if len(s) else np.nan,
                'status':'PROVISIONAL'})
    return pd.DataFrame(rows)


def parameter_stability(fits):
    rows=[]
    if fits.empty: return pd.DataFrame()
    for keys,g in fits[fits.status.ne('failed')].groupby(KEYS+['model','period']):
        data=pd.DataFrame([json.loads(x) for x in g.sort_values('origin_date').params]).select_dtypes('number')
        for col in data:
            values=data[col]
            rows.append(dict(zip(KEYS+['model','period'],keys)) | {'parameter':col,'fits':len(values),
                'mean':values.mean(),'std':values.std(ddof=0),'min':values.min(),'max':values.max(),
                'maximum_absolute_change':values.diff().abs().max(),'status':'PROVISIONAL'})
    return pd.DataFrame(rows)


def sensitivity_tables(frame):
    """Reassess exclusions on identical dates, plus separately ranked frequency panels."""
    data=frame[frame.common & frame.period.eq('validation')]
    scenario_rows=[]
    for keys,g in data.groupby(['asset','frequency','target']):
        by={name:part for name,part in g.groupby('scenario')}
        if not {'eligible','exclude_questionable'}<=set(by): continue
        dates=set(by['eligible'].target_date)&set(by['exclude_questionable'].target_date)
        for model in sorted(g.model.unique()):
            a=by['eligible'];b=by['exclude_questionable']
            a=a[a.target_date.isin(dates) & a.model.eq(model)].sort_values('target_date')
            b=b[b.target_date.isin(dates) & b.model.eq(model)].sort_values('target_date')
            if len(a)!=len(b): raise ValueError('Sensitivity model dates differ')
            scenario_rows.append(dict(zip(['asset','frequency','target'],keys)) | {'model':model,'n':len(a),
                'eligible_qlike':a.loss_qlike.mean(),'excluded_qlike':b.loss_qlike.mean(),
                'excluded_minus_eligible_qlike':b.loss_qlike.mean()-a.loss_qlike.mean(),'status':'PROVISIONAL'})
    frequency_rows=[]
    for keys,g in data.groupby(['asset','scenario','target']):
        if keys[-1]=='spot_c2c_squared': continue
        by={freq:part for freq,part in g.groupby('frequency')}
        if set(by)!={1,5,10,15}: continue
        dates=set.intersection(*(set(x.target_date) for x in by.values()))
        for (freq,model),part in g.groupby(['frequency','model']):
            p=part[part.target_date.isin(dates)]
            frequency_rows.append(dict(zip(['asset','scenario','target'],keys)) | {'frequency':freq,'model':model,
                'n_same_dates_across_frequencies':len(p),'qlike':p.loss_qlike.mean(),
                'calibration_ratio':p.observed_variance.mean()/p.forecast_variance.mean() if len(p) else np.nan,'status':'PROVISIONAL'})
    frequency=pd.DataFrame(frequency_rows)
    if len(frequency):
        frequency['rank_within_frequency']=frequency.groupby(['asset','scenario','target','frequency']).qlike.rank(method='min')
    return pd.DataFrame(scenario_rows),frequency
