"""Registered, cutoff-enforced Stage 5 runner. Never touches frozen protocols."""
from __future__ import annotations
import dataclasses
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import platform
import shutil
import time
import tomllib
import importlib.metadata
import numpy as np
import pandas as pd
from volrisk.data.storage import sha256
from volrisk.data.returns import load_canonical_returns
from volrisk.forecasting.base import params_to_json
from . import STATUS, INDEX_STATUS
from .alignment import bounded_parquet, Instrument, TZ
from .forecasts import generate_forecasts
from .accounting import Policy, run_close, gross_policy
from .metrics import summarize, match_constant, expost_constant, forecast_scores, paired_uncertainty, holm
from .attribution import decompose

REPORT_NAMES = ['position_sizing_experiment.md','economic_model_comparison.csv','exposure_attribution.md',
                'trading_cost_sensitivity.md','forecast_vs_economic_value.md']


def json_text(value):
    def clean(x):
        if x is pd.NaT or x is pd.NA:
            return None
        if isinstance(x,dict):
            return {str(k):clean(v) for k,v in x.items()}
        if isinstance(x,(tuple,list)):
            return [clean(v) for v in x]
        return x
    return params_to_json(clean(value))


def write_json(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json_text(value)+'\n',encoding='utf-8')


def write_ledger(path,frame):
    """Entry metadata has its own JSON; do not duplicate non-JSON pandas attrs."""
    persisted=frame.rename_axis('date').reset_index()
    persisted.attrs={}
    persisted.to_parquet(path,index=False)


def load_config(path):
    config=tomllib.loads(Path(path).read_text(encoding='utf-8'))
    if config['data']['cutoff'] != '2024-12-31' or config['periods']['evaluation_end'] > '2024-12-31':
        raise ValueError('Stage 5 cannot access future-period data')
    if config['data']['asset']!='NIFTY50_TRI' or config['data']['instrument_status']!=INDEX_STATUS:
        raise ValueError('This registration authorizes only the theoretical TRI empirical panel')
    if config['periods']['development_end'] >= config['periods']['evaluation_start']:
        raise ValueError('Development and evaluation periods overlap')
    return config


def register(config_path):
    config=load_config(config_path)
    path=Path('experiments/stage5/registration.json')
    config_hash=sha256(Path(config_path))
    if path.exists():
        registration=json.loads(path.read_text(encoding='utf-8'))
        if registration['config_sha256']!=config_hash:
            raise ValueError('Registered configuration changed; create a distinct experiment registration')
        return registration
    protected={}
    for root in [Path('reports'),Path('experiments'),Path('config')]:
        for item in root.rglob('*'):
            if not item.is_file() or 'stage5' in item.parts or item.name in REPORT_NAMES or item.name=='stage5.toml':
                continue
            protected[item.as_posix()]=sha256(item)
    registration=dict(stage='5',registered_at_utc=datetime.now(timezone.utc).isoformat(),status=STATUS,
        config=config,config_sha256=config_hash,protected_artifacts=protected,
        primary=dict(target='daily close-to-close TRI log-return variance at origin+2 sessions',
            execution='origin+1 close; weights apply only subsequent returns',target_vol=.12,cost_bps=10.,
            rebalance='daily',band=0.,cash='zero-rate scenario, ACT/365',failure='hold existing units'),
        models=config['estimation']['models'],
        tested_configuration_count={'dynamic_factorial':180,'dynamic_one_factor_sensitivity':25,
                                    'static_and_development_matched':12,'static_cost_sensitivity':4,
                                    'total_economic_paths':221,'zero_cost_shadow_paths':221,
                                    'direct_model_horizon_specifications':10,'formal_sharpe_contrasts':15},
        matching='Development-only October-December 2023 exposure/risk calibration; no 2024 fitting of benchmarks',
        statistics='15 primary dynamic-vs-buyhold/development-exposure/development-risk Sharpe contrasts, stationary bootstrap block10 draws2000, Holm across all15; other metrics descriptive',
        selection='No model/configuration promotion. All 2024 results exploratory and previously inspected.',
        metrics=['gross and net cumulative return','CAGR if >=180 calendar days','cash-excess Sharpe','annualized volatility',
            'drawdown and duration','worst5/20','ES95','exposure','one-way turnover','cost/cash drag','rebound participation'],
        sensitivity='180 target/frequency/band/cost combinations; primary-only min25%, cash4%, extra execution session, failure-to-cash, deterministic every20th signal unavailable',
        limitations=['NON-EXECUTABLE index, fractional theoretical exposure; no ETF/actual fills',
            'TRI gross dividend reinvestment index; taxes, management fees, funding mechanics and tracking error not modeled',
            'RV/VIX vendor, timezone and bar conventions unverified; NSE spot confirmed by user only',
            'Illustrative costs and cash rate, not observed actual execution or risk-free returns',
            '2024 repeatedly inspected; development benchmark calibration sample short; fixed-path bootstrap conditional on estimated forecasts',
            'Panel B blocked: no verified execution-aligned adjusted OHLC/action history and risk-mapped intraday instrument'],
        inspection_exposure_incident={
            'description':'Initial repository inspection displayed pre-existing review rows dated 2025-04-04 and 2025-04-09, full-window audit aggregates, and a live NSE search snippet before strict filtering.',
            'response':'Disclosed to user. No such values enter Stage 5 datasets, fits, returns, decisions or evaluation. All numerical dataset reads use <=2024 predicate filters. No 2025-2026 evaluation.',
            'consequence':'Do not claim zero incidental later-period exposure or a pristine historic holdout.'},
        source_references={
            'canonical_pointer':config['data']['audit_pointer'],'rv_vix_panel':config['data']['stage4_panel'],
            'niftybees_yahoo':'data/raw/stage5/20261103T162735654075Z/niftybees_source.parquet',
            'exchange_checks':'data/raw/stage5/exchange_20261103T163636918604Z/manifest.json',
            'official_actions':'https://investeasy.nipponindiaim.com/rmfGsamnew/Products/NiftyBeES/CorporateAction.aspx',
            'official_june2022_factsheet':'https://mf.nipponindiaim.com/investorservices/factsheetsdocuments/fundamentals-july-2022/Innerpage/ETF-Nifty-BeES.html'})
    write_json(path,registration)
    return registration


def verify_protected(registration):
    changed=[p for p,digest in registration['protected_artifacts'].items() if not Path(p).exists() or sha256(Path(p))!=digest]
    if changed:
        raise ValueError(f'Prior experiment artifacts changed: {changed[:5]}')


def load_inputs(config):
    asset=config['data']['asset']
    returns=load_canonical_returns(config['data']['audit_pointer'],[asset],end_date=config['data']['cutoff'],
        preserve_gaps=True,require_verified_intervals=True)[asset]
    intraday=bounded_parquet(config['data']['stage4_panel'],'session_date').set_index('session_date')
    panel=pd.DataFrame({'simple_return':returns.simple_returns,'log_return':returns.log_returns})
    for col in ['rv','overnight_squared','vix_implied_variance','vix_available_at','vix_source_session','rv_eligible','origin_timestamp']:
        panel[col]=intraday[col].reindex(panel.index)
    # Timestamp is a session-close metadata field, not a filled price or feature.
    # No origin before the existing audited intraday panel is ever forecast.
    needed=panel.loc[config['estimation']['forecast_start']:]
    if needed.origin_timestamp.isna().any():
        raise ValueError('Missing verified session-close timestamp for a forecast/execution session')
    if needed.simple_return.isna().any():
        raise ValueError('Daily execution grid is incomplete; no path compression allowed')
    finite=panel.log_return.notna() & panel.simple_return.notna()
    if not np.allclose(np.log1p(panel.loc[finite,'simple_return']),panel.loc[finite,'log_return'],atol=1e-12,rtol=1e-10):
        raise ValueError('Simple/log return identity failed')
    Instrument(asset,'INR',True,False,'official NIFTY 50 gross Total Return Index').require_panel('A')
    info=dict(asset=asset,currency='INR',instrument_status=INDEX_STATUS,
        daily_source=returns.provenance(),feature_source=config['data']['stage4_panel'],
        feature_sha256=sha256(Path(config['data']['stage4_panel'])),
        input_first=str(panel.index.min().date()),input_last=str(panel.index.max().date()),
        daily_rows=len(panel),daily_valid=int(finite.sum()),
        complete_rv_pre2025=int(panel.rv.notna().sum()),lagged_iv_pre2025=int(panel.vix_implied_variance.notna().sum()),
        execution_period_missing_returns=int(needed.simple_return.isna().sum()))
    return panel,info


def primary_policy(config):
    p=config['policy']
    return Policy(target_vol=p['primary_target_vol'],cost_bps=p['primary_cost_bps'],frequency='daily',
        minimum=p['minimum_exposure'],maximum=p['maximum_exposure'],annual_cash=p['annual_cash_rate'],
        failure=p['failure_policy'],initial_capital=p['initial_capital'])


def run(config_path='config/stage5.toml'):
    started=time.perf_counter()
    config=load_config(config_path)
    registration=register(config_path)
    verify_protected(registration)
    addendum_path=Path('experiments/stage5/expost_fairness_addendum.json')
    if not addendum_path.exists():
        write_json(addendum_path,dict(created_utc=datetime.now(timezone.utc).isoformat(),
            status='POST_RESULT_EXPLORATORY_DIAGNOSTIC_ONLY',
            reason='After seeing the first Stage5 primary results, development-only matching left different 2024 risk. User explicitly permits ex-post matching diagnostics. Add exact full-2024 exposure and risk matches, visibly non-deployable.',
            additional_configurations=10,additional_formal_tests=0,
            unchanged='Primary policies, development matching, forecasts, formal15-test family, previous runs and frozen forecasting protocol',
            original_completed_run='4c569a4834c9fa96d32560c5'))
    source_files=sorted(list(Path('src/volrisk/economics').glob('*.py'))+[Path('src/volrisk/stage5_cli.py')]
        +[Path('src/volrisk/forecasting')/f for f in ['base.py','historical.py','ewma.py','garch.py','har.py','positive_har.py','registry.py']]
        +[Path('src/volrisk/data')/f for f in ['returns.py','storage.py']])
    code_hashes={p.as_posix():sha256(p) for p in source_files}
    panel,data_info=load_inputs(config)
    identity=dict(config_sha256=registration['config_sha256'],code_hashes=code_hashes,addendum_sha256=sha256(addendum_path),
                  daily_sha256=data_info['daily_source']['source_sha256'],feature_sha256=data_info['feature_sha256'])
    run_id=hashlib.sha256(params_to_json(identity).encode()).hexdigest()[:24]
    out=Path(config['outputs']['root'])/run_id
    if (out/'manifest.json').exists():
        manifest=json.loads((out/'manifest.json').read_text())
        for rel,digest in manifest['output_hashes'].items():
            if sha256(out/rel)!=digest: raise ValueError('Completed Stage 5 artifact was modified')
        print(f'Existing immutable Stage 5 run verified: {out}',flush=True)
        publish(out,config)
        return out
    if out.exists():
        raise FileExistsError(f'Incomplete run retained for inspection: {out}; use a distinct code/config version')
    out.mkdir(parents=True)
    shutil.copy2(config_path,out/'stage5.toml')
    shutil.copy2('experiments/stage5/registration.json',out/'registration.json')
    shutil.copy2(addendum_path,out/'expost_fairness_addendum.json')
    for path in source_files:
        dest=out/'source'/path
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    write_json(out/'data_readiness.json',data_info)
    # Immutable inputs contain only bounded development/evaluation observations.
    panel.rename_axis('date').reset_index().to_parquet(out/'bounded_inputs.parquet',index=False)
    print('Generating causal h=2/h=3 daily-risk forecasts; cutoff 2024-12-31',flush=True)
    with (out/'forecast_creation_ledger.jsonl').open('w',encoding='utf-8') as log:
        def save(record):
            log.write(json_text(record)+'\n');log.flush()
        forecasts=generate_forecasts(panel,config,save=save)
    forecasts.to_parquet(out/'forecasts.parquet',index=False)
    period=config['periods']; base=primary_policy(config); models=config['estimation']['models']
    kwargs=dict(start=period['evaluation_start'],end=period['evaluation_end'],asset=config['data']['asset'])
    model_metrics,common=forecast_scores(forecasts,models,panel.index[panel.index>pd.Timestamp(period['evaluation_start'])][0],period['evaluation_end'])
    model_metrics.to_csv(out/'forecast_metrics.csv',index=False)
    common.to_parquet(out/'common_forecasts.parquet',index=False)
    print('Calibrating constant benchmarks using development observations only',flush=True)
    matches=[]
    for model in models:
        for metric in ['average_equity_exposure','realized_volatility']:
            matches.append(match_constant(panel,forecasts,model,base,start=period['development_start'],
                                          end=period['development_end'],metric=metric))
    pd.DataFrame(matches).to_csv(out/'benchmark_calibration.csv',index=False)
    ledgers={}; summaries=[]; policy_records=[]; primary_names={}
    (out/'ledgers').mkdir()
    def execute(name,model,policy,*,constant=None,buy_hold=False,kind='sensitivity',input_forecasts=None):
        fc=forecasts if input_forecasts is None else input_forecasts
        path=run_close(panel,fc,model,policy,constant=constant,buy_hold=buy_hold,**kwargs)
        gross=run_close(panel,fc,model,gross_policy(policy),constant=constant,buy_hold=buy_hold,**kwargs)
        summary=summarize(path,policy.initial_capital); gm=summarize(gross,policy.initial_capital)
        summary.update(strategy=name,model=model,kind=kind,**dataclasses.asdict(policy),constant=constant,
            gross_cumulative_return=gm['net_cumulative_return'],gross_sharpe=gm['net_sharpe'],
            gross_volatility=gm['realized_volatility'],gross_maximum_drawdown=gm['maximum_drawdown'],
            transaction_cost_drag=gm['net_cumulative_return']-summary['net_cumulative_return'],
            status=STATUS,instrument_status=INDEX_STATUS,panel='A',
            first_return=str(path.index.min().date()),last_return=str(path.index.max().date()))
        summaries.append(summary)
        policy_records.append(dict(strategy=name,model=model,policy=dataclasses.asdict(policy),constant=constant,buy_hold=buy_hold,kind=kind))
        # Persist the initial execution event separately from daily P&L rows.
        write_json(out/'ledgers'/f'{name}_entry.json',path.attrs['initial_action'])
        write_ledger(out/'ledgers'/f'{name}.parquet',path)
        write_ledger(out/'ledgers'/f'{name}_gross.parquet',gross)
        if kind=='primary': ledgers[name]=path
        return path
    execute('buy_hold','static',base,constant=1.,buy_hold=True,kind='primary')
    execute('constant_60','static',base,constant=config['policy']['constant_exposure'],kind='primary')
    print('Running registered exposure/cost/rebalance scenarios',flush=True)
    for model in models:
        for target,cost,frequency,band in itertools.product(config['policy']['targets'],config['policy']['cost_bps'],
                                                           config['policy']['frequencies'],config['policy']['bands']):
            policy=dataclasses.replace(base,target_vol=target,cost_bps=cost,frequency=frequency,band=band)
            primary=policy==base
            name=f'{model}_v{int(target*100)}_c{int(cost)}_{frequency}_b{int(band*100)}'
            execute(name,model,policy,kind='primary' if primary else 'factorial_sensitivity')
            if primary: primary_names[model]=name
        for label,change in [('minimum25',{'minimum':.25}),('cash4',{'annual_cash':config['policy']['cash_sensitivity']}),
                              ('delay_one_session',{'horizon':3}),('failure_to_cash',{'failure':'cash'})]:
            execute(f'{model}_{label}',model,dataclasses.replace(base,**change),kind='one_factor_sensitivity')
        stressed=forecasts.copy()
        loc=stressed.index[stressed.model.eq(model)&stressed.horizon.eq(2)&stressed.execution_date.ge(pd.Timestamp(period['evaluation_start']))]
        loc=loc[::20]
        stressed.loc[loc,'forecast_variance']=np.nan
        stressed.loc[loc,'failure_reason']='PREDECLARED_OPERATIONAL_STRESS_every20th_signal'
        execute(f'{model}_failure_injection',model,base,kind='operational_stress',input_forecasts=stressed)
        for match in [x for x in matches if x['model']==model]:
            short='exposure' if match['criterion']=='average_equity_exposure' else 'risk'
            execute(f'matched_{short}_{model}','static',base,constant=match['weight'],kind='primary')
    for cost in [x for x in config['policy']['cost_bps'] if x!=base.cost_bps]:
        execute(f'buy_hold_cost{int(cost)}','static',dataclasses.replace(base,cost_bps=cost),constant=1.,buy_hold=True,kind='static_cost_sensitivity')
        execute(f'constant_60_cost{int(cost)}','static',dataclasses.replace(base,cost_bps=cost),constant=.60,kind='static_cost_sensitivity')
    expost=[]
    for model in models:
        for metric in ['average_equity_exposure','realized_volatility']:
            match=expost_constant(panel,forecasts,model,base,metric=metric,**kwargs)
            short='exposure' if metric=='average_equity_exposure' else 'risk'
            execute(f'expost_{short}_{model}','static',base,constant=match['weight'],kind='EX_POST_NON_DEPLOYABLE_DIAGNOSTIC')
            expost.append(match)
    pd.DataFrame(expost).to_csv(out/'expost_matching.csv',index=False)
    economic=pd.DataFrame(summaries)
    economic.to_csv(out/'economic_model_comparison.csv',index=False)
    write_json(out/'policies.json',policy_records)
    stats=[];attributions=[]
    print('Calculating paired uncertainty and exact P&L attribution',flush=True)
    for model in models:
        dynamic=ledgers[primary_names[model]]
        for benchmark in ['buy_hold',f'matched_exposure_{model}',f'matched_risk_{model}']:
            pair=paired_uncertainty(dynamic,ledgers[benchmark],draws=config['statistics']['bootstrap_draws'],
                block=config['statistics']['block_length'],seed=config['statistics']['seed'])
            stats.append(dict(model=model,benchmark=benchmark,**pair))
            daily=decompose(dynamic,ledgers[benchmark]);daily['model']=model;daily['benchmark']=benchmark
            attributions.append(daily.reset_index())
    stats=pd.DataFrame(stats);stats['holm_p_value']=holm(stats.p_value)
    stats.to_csv(out/'economic_uncertainty.csv',index=False)
    attribution=pd.concat(attributions,ignore_index=True)
    attribution.to_csv(out/'attribution_daily.csv',index=False)
    from .reporting import create_reports
    create_reports(out,config,data_info,economic,model_metrics,stats,pd.DataFrame(matches),ledgers,primary_names,attribution,common)
    verify_protected(registration)
    packages={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','arch','pyarrow','matplotlib','yfinance']}
    manifest=dict(run_id=run_id,status=STATUS,created_utc=datetime.now(timezone.utc).isoformat(),identity=identity,
        package_versions=packages,python_version=platform.python_version(),data=data_info,
        raw_acquisition_hashes={p.as_posix():sha256(p) for p in Path('data/raw/stage5').rglob('*') if p.is_file() and 'cache' not in p.parts},
        total_economic_paths=len(economic),forecast_records=len(forecasts),matched_forecast_dates=int(model_metrics.observations.iloc[0]),
        protected_artifacts_verified=len(registration['protected_artifacts']),future_period_evaluated=False,
        runtime_seconds=time.perf_counter()-started,
        output_hashes={p.relative_to(out).as_posix():sha256(p) for p in out.rglob('*') if p.is_file()})
    write_json(out/'manifest.json',manifest)
    publish(out,config)
    print(f'Completed {out}: {len(economic)} exploratory theoretical paths; prior artifacts verified unchanged',flush=True)
    return out


def publish(out,config):
    reports=Path(config['outputs']['reports']);reports.mkdir(exist_ok=True)
    for name in REPORT_NAMES:
        shutil.copy2(out/name,reports/name)
    shutil.copytree(out/'figures',reports/'figures'/'stage5',dirs_exist_ok=True)
    write_json(reports/'latest_stage5.json',dict(run=str(out),manifest_sha256=sha256(out/'manifest.json'),status=STATUS))
