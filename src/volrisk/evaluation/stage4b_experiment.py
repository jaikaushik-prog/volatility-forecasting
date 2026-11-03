"""Isolated immutable Stage 4B runs. Never republishes or overwrites Stage 4 reports."""
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

from volrisk.data.storage import sha256, write_json, write_parquet
from volrisk.data.stage4b_dataset import load_stage4, assert_unchanged, HARD_CUTOFF
from volrisk.forecasting.base import _json_ready
from .walk_forward import PeriodSplits
from .experiment import package_versions
from .vix_diagnostics import reproduce_stage4, diagnose_levels
from .stage4b import tune_ridge, evaluate_models, compare_models, sample_alignment, STATUS
from .har_metrics import summarize_har


def publish(run, root, manifest):
    assert_unchanged(manifest['historical_artifact_hashes'])
    for relative, expected in manifest['output_sha256'].items():
        source = run/relative
        if sha256(source) != expected:
            raise ValueError('Stage 4B artifact changed: '+relative)
        if not relative.startswith('reports/'):
            continue
        target = root/'reports'/Path(relative).relative_to('reports')
        if str(target.resolve()) in manifest['historical_artifact_hashes']:
            raise ValueError('Refusing to overwrite a historical Stage 4 report')
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name+'.'+uuid4().hex+'.tmp')
        shutil.copyfile(source,temp); os.replace(temp,target)
    pointer = {'run_id':manifest['run_id'],'run_dir':str(run.resolve()),
               'manifest_sha256':sha256(run/'manifest.json'),'status':STATUS,
               'holdout_evaluated':False,'independent_confirmation':False}
    write_json(pointer,root/'reports/latest_stage4b.json')
    assert_unchanged(manifest['historical_artifact_hashes'])


def run_stage4b(config_path='config/stage4b.toml', *, make_figures=True):
    path=Path(config_path).resolve(); root=path.parent.parent
    config=tomllib.loads(path.read_text(encoding='utf-8'))
    if pd.Timestamp(config['evaluation']['end']) > HARD_CUTOFF:
        raise ValueError('No 2025–2026 numerical evaluation is permitted')
    if config['evaluation']['targets'] != ['intraday','intraday_overnight']:
        raise ValueError('The two predeclared variance targets must remain separate')
    started=time.perf_counter()
    panel, old_forecasts, old_fits, previous, hashes=load_stage4(config,root)
    splits=PeriodSplits.from_config(previous['config']['splits'])
    if pd.Timestamp(config['tuning']['cutoff']) >= pd.Timestamp(config['evaluation']['start']):
        raise ValueError('Tuning overlaps exploratory evaluation')
    source_root=Path(__file__).resolve().parents[3]
    code={str(p.relative_to(source_root)).replace('\\','/'):sha256(p) for p in sorted((source_root/'src/volrisk').rglob('*.py'))}
    fingerprint={'config':config,'config_file_sha256':sha256(path),'code':code,'versions':package_versions(),
                 'stage4_run':previous['run_id'],'source_artifacts':hashes,'figures':make_figures}
    run_id=hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()[:24]
    run=root/config['outputs']['root']/run_id
    if (run/'manifest.json').exists():
        m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
        publish(run,root,m)
        return m
    if run.exists():
        raise FileExistsError('Incomplete Stage 4B run preserved for inspection: '+str(run))
    (run/'reports').mkdir(parents=True)
    manifest={'run_id':run_id,'status':STATUS,'independent_confirmation':False,'holdout_evaluated':False,
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'numerical_cutoff':'2024-12-31',
        'stage4_run_id':previous['run_id'],'config':config,'fingerprint':fingerprint,
        'historical_artifact_hashes':hashes,'prior_research_exposure':'2024 informed specifications; earlier research exposed some 2025–2026 values',
        'configuration_counts':{'ridge_grid_candidates':len(config['tuning']['alphas'])*2,
            'final_model_target_cells':12,'distinct_model_target_configurations':(5+len(config['tuning']['alphas']))*2,
            'formal_paired_comparisons':len(config['evaluation']['pairs'])*2,
            'legacy_floor_counterfactuals':len(config['evaluation']['diagnostic_floor_fractions']),
            'development_fold_designs_considered':2 if 'amendment' in config['tuning'] else 1,
            'aborted_primary_grid_candidates':config['tuning'].get('amendment',{}).get('aborted_primary_grid_candidates',0)}}
    # Persist registration BEFORE tuning or new-model evaluation.
    write_json(manifest,run/'registration.json')
    for relative in code:
        dest=run/'code'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source_root/relative,dest)
    shutil.copyfile(path,run/'stage4b.toml')
    write_parquet(panel.reset_index(),run/'panel.parquet')
    reproduction=reproduce_stage4(panel,old_forecasts,previous)
    reproduction.to_csv(run/'reports/stage4b_stage4_reproduction.csv',index=False)
    events, coefficients, correlations, floors=diagnose_levels(panel,old_forecasts,previous,
                                config['evaluation']['diagnostic_floor_fractions'])
    for name, table in [('legacy_events',events),('legacy_coefficients',coefficients),
                         ('legacy_correlations',correlations),('floor_sensitivity',floors)]:
        table.to_csv(run/'reports'/f'stage4b_{name}.csv',index=False)
    all_forecasts, all_fits, selections, scores, tuning_forecasts, tuning_fits=[],[],{},[],[],[]
    with (run/'forecast_issuance.jsonl').open('w',encoding='utf-8') as stream:
        def persist(record):
            assert 'observed_variance' not in record
            stream.write(json.dumps(_json_ready(record),allow_nan=False)+'\n')
        for target in config['evaluation']['targets']:
            selection,score,tf,tfit=tune_ridge(panel,config,target,splits)
            selections[target]=selection;scores.append(score);tuning_forecasts.append(tf);tuning_fits.append(tfit)
            f, fit, specs=evaluate_models(panel,config,target,selection,splits,save_forecast=persist)
            manifest.setdefault('model_specifications',{})[target]=specs
            all_forecasts.append(f);all_fits.append(fit)
    forecasts=pd.concat(all_forecasts,ignore_index=True)
    fits=pd.concat(all_fits,ignore_index=True)
    scores=pd.concat(scores,ignore_index=True)
    manifest['ridge_selection']=selections
    write_json(selections,run/'ridge_selection.json')
    metrics,tests,slices,stability=compare_models(forecasts,fits,config)
    alignment=sample_alignment(forecasts,fits,old_forecasts,old_fits)
    alignment.to_csv(run/'reports/stage4b_sample_alignment.csv',index=False)
    # Keep the original unsuccessful predictions, unchanged, outside the six-model ranking.
    legacy=old_forecasts[old_forecasts.model.eq('har_vix') & old_forecasts.period.eq('validation')
                        & old_forecasts.target.isin(config['evaluation']['targets'])].copy()
    for target in config['evaluation']['targets']:
        dates=forecasts.loc[forecasts.target.eq(target)&forecasts.common,'target_date'].unique()
        mask=legacy.target.eq(target)
        legacy.loc[mask,'common']=legacy.loc[mask,'forecast_valid'] & legacy.loc[mask,'target_observed'] & legacy.loc[mask,'target_date'].isin(dates)
    legacy_metrics=summarize_har(legacy,old_fits)
    legacy_metrics['comparison_group']='archived_unsuccessful_comparator'
    legacy_metrics['model']='legacy_levels_har_vix'
    legacy_metrics['status']=STATUS
    legacy_metrics[['rank_qlike','rank_calibration']]=np.nan
    # Align new diagnostic columns explicitly; avoids all-NA concat dtype inference warnings.
    for column in metrics.columns:
        if column not in legacy_metrics:
            legacy_metrics[column]=np.nan
    metrics=pd.concat([metrics,legacy_metrics[metrics.columns]],ignore_index=True)
    for name,frame in [('forecasts',forecasts),('fits',fits),('legacy_comparator',legacy),
                       ('tuning_forecasts',pd.concat(tuning_forecasts,ignore_index=True)),
                       ('tuning_fits',pd.concat(tuning_fits,ignore_index=True))]:
        write_parquet(frame,run/f'{name}.parquet')
    for name,table in [('comparison',metrics),('paired_tests',tests),('loss_slices',slices),
                       ('coefficient_stability',stability),('ridge_tuning',scores)]:
        table.to_csv(run/'reports'/f'stage4b_{name}.csv',index=False)
    manifest['forecast_records']=len(forecasts)
    manifest['fit_records']=len(fits)
    manifest['last_forecast_target']=str(forecasts.target_date.max().date())
    manifest['reproduction_passed']=bool(reproduction.exact_forecast_and_coefficient_reproduction.all())
    from .stage4b_reporting import write_stage4b_reports
    manifest['summary']=write_stage4b_reports(run,manifest,panel,forecasts,fits,metrics,tests,slices,
        stability,events,coefficients,correlations,floors,scores,reproduction,alignment,make_figures=make_figures)
    assert_unchanged(hashes)
    manifest['historical_artifacts_unchanged']=True
    manifest['runtime_seconds']=time.perf_counter()-started
    manifest['output_sha256']={str(p.relative_to(run)).replace('\\','/'):sha256(p) for p in sorted(run.rglob('*')) if p.is_file()}
    manifest['complete']=True
    write_json(_json_ready(manifest),run/'manifest.json')
    publish(run,root,manifest)
    return manifest
