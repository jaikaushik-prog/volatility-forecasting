"""Provisional Stage 4 experiments; reused audited artifacts, no ingestion or holdout runs."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import tomllib
from uuid import uuid4

import numpy as np
import pandas as pd

from volrisk.data.har_dataset import load_har_inputs, prepare_panel, protected_splits, ReadinessError
from volrisk.data.storage import sha256, write_json, write_parquet, write_text
from volrisk.forecasting.base import _json_ready
from volrisk.forecasting.har import origin_features, RV_FEATURES, ON_FEATURES, VIX_FEATURES
from volrisk.forecasting.registry import build_model
from .experiment import package_versions
from .har_walk_forward import walk_forward, model_specs, common_dates
from .har_metrics import (attach_har_losses, summarize_har, comparisons, attach_regimes,
                          regime_metrics, parameter_stability, sensitivity_tables, KEYS)


def load_config(path):
    path=Path(path).resolve()
    config=tomllib.loads(path.read_text(encoding='utf-8'))
    if set(config['data']['frequencies'])!={1,5,10,15}:
        raise ValueError('Predeclared sensitivity study requires 1/5/10/15-minute frequencies')
    if config['data']['sessions_per_year']!=252:
        raise ValueError('Stage 4 annualization is fixed at 252 sessions')
    if config['data']['vix_extra_lag']<1:
        raise ValueError('Provisional experiments require an additional full-session VIX lag')
    if not config['estimation']['common_training']:
        raise ValueError('Incremental-value study requires identical HAR training samples')
    protected_splits(config,path.parent.parent)
    return path,config


def _publish(run,root,manifest):
    for relative,digest in manifest['output_sha256'].items():
        source=run/relative
        if sha256(source)!=digest: raise ReadinessError(f'Changed experiment artifact: {relative}')
        if not relative.startswith('reports/'): continue
        target=root/manifest['config']['outputs']['reports']/Path(relative).relative_to('reports')
        target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_name(target.name+'.'+uuid4().hex+'.tmp')
        shutil.copyfile(source,temporary)
        os.replace(temporary,target)
    pointer={'run_id':manifest['run_id'],'run_dir':str(run.resolve()),'manifest':str((run/'manifest.json').resolve()),
             'manifest_sha256':sha256(run/'manifest.json'),'status':manifest['status'],'holdout_evaluated':False}
    write_json(pointer,root/'reports/latest_har_rv.json')
    write_json(pointer,root/'experiments/har_rv/latest.json')


def _coverage(panel,asset,frequency,scenario,splits):
    feats=origin_features(panel)
    cols=RV_FEATURES+ON_FEATURES+(VIX_FEATURES if asset=='NIFTY' else [])
    common=np.isfinite(feats[cols]).all(axis=1)
    records=[]
    for period in ('development','validation'):
        selected=splits.label(panel.index)==period
        p=panel.loc[selected]
        records.append({'asset':asset,'frequency':frequency,'scenario':scenario,'period':period,'session_rows':len(p),
            'complete_sessions':int(p.rv.notna().sum()),'complete_special_duration_sessions':int((p.rv.notna() & p.nonstandard_duration).sum()),
            'valid_overnight':int(p.overnight_squared.notna().sum()),
            'valid_lagged_vix':int(p.vix_implied_variance.notna().sum()),'all_har_origin_features':int(common[selected].sum()),
            'questionable_sessions':int(p.questionable.sum()),'excluded_sessions':int(p.exclusion_reason.ne('').sum()),
            'first_session':p.index.min(),'last_session':p.index.max(),'status':'PROVISIONAL'})
    return records


def run_har_experiment(config_path='config/har_rv.toml', *, make_figures=True, readiness_only=False):
    path,config=load_config(config_path)
    root=path.parent.parent
    splits=protected_splits(config,root)
    began=time.perf_counter()
    try:
        datasets,vix,readiness=load_har_inputs(config,root)
    except (ReadinessError,FileNotFoundError,KeyError,ValueError) as exc:
        # A blocker report contains no fabricated forecast or metric results.
        message=f'{type(exc).__name__}: {exc}'
        from .har_reporting import write_blocked_reports
        write_blocked_reports(root/config['outputs']['reports'],message)
        return {'status':'BLOCKED_CRITICAL_DATA_GATE','blocker':message,'holdout_evaluated':False}
    code_root=Path(__file__).resolve().parents[3]
    code={str(p.relative_to(code_root)):sha256(p) for p in sorted((code_root/'src/volrisk').rglob('*.py'))}
    versions=package_versions()
    fingerprint={'config':config,'input_hashes':readiness['input_hashes'],'code':code,'versions':versions,
                 'figures':make_figures,'readiness_only':readiness_only}
    run_id=hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()[:24]
    run=root/config['outputs']['root']/run_id
    if (run/'manifest.json').exists():
        manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
        _publish(run,root,manifest)
        return manifest
    if run.exists(): raise FileExistsError(f'Incomplete run preserved at {run}; inspect before retrying')
    (run/'reports').mkdir(parents=True)
    manifest={'run_id':run_id,'status':'PROVISIONAL','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'config':config,'config_sha256':sha256(path),'implementation_sha256':code,'versions':versions,
        'data_readiness':readiness,'holdout_evaluated':False,'numerical_data_cutoff':str(splits.validation[1].date()),
        'user_authorization':'Provisional real-data study requested; extra full-session VIX lag; no holdout evaluation',
        'protocol':'Five fixed HAR specifications; no hyperparameter search; validation QLIKE primary, multiplicity-adjusted paired evidence',
        'forecast_timing':'Historical simulation: forecast_created_at = origin close + 1 microsecond; not an actual historical timestamp'}
    write_json(config,run/'predeclared_protocol.json')
    panels={}
    coverage=[]
    exclusions=[]
    for asset,daily in datasets.items():
        for frequency in config['data']['frequencies']:
            for scenario in config['data']['scenarios']:
                panel=prepare_panel(daily,vix,frequency=frequency,scenario=scenario,
                    vix_extra_lag=config['data']['vix_extra_lag'],full_session_minutes=config['data']['full_session_minutes'],
                    questionable_stale_minutes=config['data']['questionable_stale_minutes'],
                    vix_end=readiness['vix_source_last_session'])
                panels[(asset,frequency,scenario)]=panel
                coverage.extend(_coverage(panel,asset,frequency,scenario,splits))
                e=panel.reset_index()[['session_date','asset','exclusion_reason','questionable','rv_eligible']]
                exclusions.append(e.assign(frequency=frequency,scenario=scenario))
                write_parquet(panel.reset_index(),run/'panels'/f'{asset}_{frequency}m_{scenario}.parquet')
    cov=pd.DataFrame(coverage)
    cov.to_csv(run/'reports/har_rv_sample_sizes.csv',index=False)
    pd.concat(exclusions,ignore_index=True).to_csv(run/'reports/har_rv_exclusions.csv',index=False)
    if readiness_only:
        from .har_reporting import readiness_report
        write_text(readiness_report(manifest,cov),run/'reports/forecast_readiness.md')
        manifest['status']='PROVISIONAL_READINESS_ONLY'
    else:
        all_forecasts,all_fits,specifications=[],[],{}
        with (run/'forecast_issuance.jsonl').open('x',encoding='utf-8') as issued:
            for (asset,frequency,scenario),panel in panels.items():
                targets=['intraday','intraday_overnight']+(['spot_c2c_squared'] if frequency==5 else [])
                for target in targets:
                    print(f'{asset} {frequency}m {scenario} {target}: walk-forward through {splits.validation[1].date()}',flush=True)
                    specs=model_specs(asset,target,config,include_daily=target=='spot_c2c_squared')
                    specifications[f'{asset}/{frequency}/{scenario}/{target}']=specs
                    pieces=[]
                    for name,spec in specs.items():
                        def persist(row):
                            if 'observed_variance' in row: raise RuntimeError('Outcome exposed before forecast persistence')
                            row.update(frequency=frequency,scenario=scenario)
                            issued.write(json.dumps(_json_ready(row),allow_nan=False,default=str,sort_keys=True)+'\n')
                        forecasts,fits=walk_forward(panel,build_model(name,spec),target=target,splits=splits,
                            max_annualized_vol=config['estimation']['max_annualized_vol'],save_forecast=persist)
                        forecasts=forecasts.assign(frequency=frequency,scenario=scenario)
                        pieces.append(forecasts)
                        if len(fits): all_fits.append(fits.assign(frequency=frequency,scenario=scenario))
                    group=pd.concat(pieces,ignore_index=True)
                    group=common_dates(group,list(specs))
                    group=attach_regimes(group,panel,config['evaluation'])
                    all_forecasts.append(group)
        forecasts=attach_har_losses(pd.concat(all_forecasts,ignore_index=True))
        fits=pd.concat(all_fits,ignore_index=True)
        metrics=summarize_har(forecasts,fits)
        tests=comparisons(forecasts,config['evaluation'])
        regimes=regime_metrics(forecasts)
        stability=parameter_stability(fits)
        sensitivity,frequency_sensitivity=sensitivity_tables(forecasts)
        write_parquet(forecasts,run/'forecasts.parquet')
        write_parquet(forecasts[forecasts.common],run/'forecasts_common.parquet')
        write_parquet(fits,run/'fits.parquet')
        for name,table in [('har_rv_model_comparison',metrics),('har_rv_statistical_tests',tests),
                           ('har_rv_regime_metrics',regimes),('har_rv_parameter_stability',stability),
                           ('har_rv_sensitivity',sensitivity),('har_rv_frequency_sensitivity',frequency_sensitivity)]:
            table.to_csv(run/'reports'/f'{name}.csv',index=False)
        manifest['model_specifications']=specifications
        manifest['forecast_rows']=len(forecasts)
        manifest['common_forecast_rows']=int(forecasts.common.sum())
        manifest['fit_records']=len(fits)
        manifest['rankings_are_target_and_frequency_specific']=True
        from .har_reporting import write_reports
        manifest['summary']=write_reports(run,manifest,forecasts,fits,metrics,tests,regimes,cov,panels,make_figures=make_figures)
    manifest['runtime_seconds']=time.perf_counter()-began
    manifest['output_sha256']={str(p.relative_to(run)).replace('\\','/'):sha256(p) for p in sorted(run.rglob('*')) if p.is_file()}
    manifest['complete']=True
    write_json(manifest,run/'manifest.json')
    _publish(run,root,manifest)
    return manifest
