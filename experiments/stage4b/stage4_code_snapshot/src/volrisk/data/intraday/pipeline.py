"""Content-addressed intraday audit/build, with immutable runs and stable published paths."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import tomllib
from uuid import uuid4

import pandas as pd

from volrisk.data.calendar_audit import verify_calendar_evidence
from volrisk.data.storage import sha256, write_json, write_parquet
from .calendar import SessionCalendar
from .normalize import read_source, normalize_frames
from .realized import daily_measures
from .features import realized_features, vix_features, coverage
from . import VERSION


def _publish(run, root, manifest):
    for relative,digest in manifest['output_sha256'].items():
        source=run/relative
        if sha256(source)!=digest:
            raise ValueError(f'Immutable intraday output has changed: {source}')
        if relative.startswith(('intraday/','features/')):
            target=root/manifest['config']['output_root']/relative
        elif relative.startswith('reports/'):
            target=root/manifest['config']['reports_root']/Path(relative).relative_to('reports')
        else:
            continue
        target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_name(target.name+'.'+uuid4().hex+'.tmp')
        shutil.copyfile(source,temp)
        os.replace(temp,target)
    write_json({'run_id':manifest['run_id'],'run_dir':str(run.resolve()),'manifest':str((run/'manifest.json').resolve()),
                'manifest_sha256':sha256(run/'manifest.json'),'complete':True},
               root/manifest['config']['reports_root']/'latest_intraday.json')


def run_integration(config_path, *, make_figures=True):
    path=Path(config_path).resolve()
    root=path.parent.parent
    config=tomllib.loads(path.read_text(encoding='utf-8'))
    if config['quality']['minimum_session_completeness'] != 1.0:
        raise ValueError('This implementation requires 100% valid expected minutes for full-session RV')
    calendar_path=root/config['calendar_file']
    daily_path=root/config['daily_calendar_file']
    calendars=json.loads(calendar_path.read_text(encoding='utf-8'))
    daily_calendar=json.loads(daily_path.read_text(encoding='utf-8'))
    evidence=verify_calendar_evidence(daily_calendar,daily_path)
    source_paths=[root/f for spec in config['assets'].values() for f in spec['files']]
    missing=[str(p) for p in source_paths if not p.is_file()]
    if missing:
        raise FileNotFoundError('Required source CSVs unavailable; no substitute generated: '+', '.join(missing))
    code_paths=sorted(Path(__file__).parent.glob('*.py'))+[
        Path(__file__).parents[2]/'intraday_cli.py',
        Path(__file__).parents[1]/'storage.py',Path(__file__).parents[1]/'calendar_audit.py']
    inputs={str(p.relative_to(root)):sha256(p) for p in [path,calendar_path,daily_path]+source_paths+sorted(evidence)}
    omitted=[]
    for spec in config['assets'].values():
        if spec.get('omitted_pickle'):
            p=root/spec['omitted_pickle']
            omitted.append({'path':str(p),'exists':p.is_file(),'bytes':p.stat().st_size if p.is_file() else None,
                'sha256':sha256(p) if p.is_file() else None,'policy':'never deserialized; CSV is sufficient for this integration; pickle contents and coverage unknown'})
    package_root=Path(__file__).resolve().parents[4]
    codes={str(p.relative_to(package_root)):sha256(p) for p in code_paths}
    versions={name:importlib.metadata.version(name) for name in ['numpy','pandas','pyarrow','matplotlib']}
    fingerprint={'inputs':inputs,'code':codes,'versions':versions,'make_figures':make_figures,'omitted':omitted}
    run_id=hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()[:24]
    run=root/config['output_root']/'intraday_runs'/run_id
    manifest_path=run/'manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        _publish(run,root,manifest)
        return manifest
    # Incomplete runs are never published; the next run must not overwrite their evidence.
    if run.exists():
        raise FileExistsError(f'Incomplete run exists at {run}; inspect it before retrying with a changed code/config version')
    run.mkdir(parents=True)
    normalized,dailies,source_reports,actions={},{},[],{}
    manifest={'schema_version':1,'implementation_version':VERSION,'run_id':run_id,
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'config':config,
        'inputs_sha256':inputs,'implementation_sha256':codes,'versions':versions,'python':sys.version,
        'omitted_pickle':omitted,'source_verification':'USER_CONFIRMED_UNKNOWN_VENDOR_TIMEZONE_BAR_CONVENTION',
        'research_readiness':'PROVISIONAL_NOT_CERTIFIED','figures_enabled':make_figures}
    session_tables=[]
    for key,spec in config['assets'].items():
        print(f'Inspecting and normalizing {spec["asset"]}...',flush=True)
        frames=[]
        for name in spec['files']:
            frame,report=read_source(root/name,spec)
            report['asset']=spec['asset']
            source_reports.append(report)
            frames.append(frame)
        calendar=SessionCalendar(spec['exchange'],daily_calendar,calendars)
        frame,rejected,action=normalize_frames(frames,spec,calendar,config['quality'])
        normalized[key]=frame
        actions[key]=action
        write_parquet(frame,run/'intraday'/f'{key}.parquet')
        write_parquet(rejected,run/'audit'/f'{key}_quarantined.parquet')
        suspicious=frame[frame.quality_flags.ne('')]
        write_parquet(suspicious,run/'audit'/f'{key}_flagged_observations.parquet')
        print(f'  {len(frame):,} rows; building session audit and realized measures...',flush=True)
        daily,bars=daily_measures(frame,calendar,frequencies=() if key=='india_vix' else config['frequencies'],
            annualization=config['sessions_per_year'],jump_min_intervals=config['quality']['jump_min_intervals'])
        session_tables.append(daily)
        if key!='india_vix':
            dailies[key]=realized_features(daily,config['features']['rv_frequency'])
            write_parquet(dailies[key],run/'features'/f'{key}_realized_vol_daily.parquet')
            for frequency,table in bars.items():
                if frequency!=1:
                    write_parquet(table,run/'intraday'/f'{key}_{frequency}min.parquet')
        del frames, rejected, suspicious, bars
    vix=vix_features(dailies['nifty'],normalized['india_vix'],annualization=config['sessions_per_year'],
        calendar_days=config['calendar_days_per_year'],max_age_seconds=config['quality']['vix_max_age_seconds'],
        percentile_window=config['features']['vix_percentile_window'],percentile_min_history=config['features']['vix_percentile_min_history'])
    write_parquet(vix,run/'features'/'nifty_vix_features_daily.parquet')
    sessions=pd.concat([f[[c for c in f if not any(c.startswith(p) for p in ('rv_','full_','realized_vol','annualized_',
        'positive_semi','negative_semi','return_intervals','bipower','jump_'))]] for f in session_tables],ignore_index=True)
    write_parquet(sessions,run/'audit'/'sessions.parquet')
    (run/'reports').mkdir(exist_ok=True)
    sessions.to_csv(run/'reports'/'intraday_session_quality.csv',index=False)
    cov=pd.concat([coverage(f,key) for key,f in {**dailies,'nifty_vix':vix}.items()],ignore_index=True)
    cov.to_csv(run/'reports'/'intraday_feature_coverage.csv',index=False)
    manifest['source_files']=source_reports
    manifest['cleaning_actions']=actions
    manifest['calendar_evidence']=calendars['evidence']
    # Confirm source bytes stayed unchanged throughout processing.
    for name,digest in inputs.items():
        if sha256(root/name)!=digest: raise ValueError(f'Input changed during run: {name}')
    from .reporting import build_reports
    print('Writing descriptive reports and figures...',flush=True)
    manifest['summary']=build_reports(run,manifest,normalized,dailies,vix,sessions,cov,make_figures=make_figures)
    manifest['output_sha256']={str(p.relative_to(run)).replace('\\','/'):sha256(p) for p in sorted(run.rglob('*')) if p.is_file()}
    manifest['complete']=True
    write_json(manifest,manifest_path)
    _publish(run,root,manifest)
    return manifest
