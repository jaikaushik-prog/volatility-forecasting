"""NEXUS daily risk brief. Run `python -m volrisk.daily_cli demo` to try it offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from volrisk.monitoring.daily import Calendar, fingerprint, load_settings, register, run_daily, utc_timestamp
from volrisk.monitoring.ledger import Ledger, digest


def demo(config, output):
    """Deterministic synthetic prices, segregated from research and real report inputs."""
    cfg=load_settings(config); calendar=Calendar(cfg['_paths']['calendar'])
    dates=calendar.sessions('2020-01-01','2023-12-29')
    dates=pd.DatetimeIndex([d for d in dates if calendar.verified(d)])
    rng=np.random.default_rng(20261105)
    returns=rng.normal(.0002,.009,len(dates)); returns[-12:]*=2.2
    prices=10000*np.exp(np.cumsum(returns))
    destination=Path(output)/'demo_inputs'; destination.mkdir(parents=True,exist_ok=True)
    frame=pd.DataFrame({'Date':dates.strftime('%Y-%m-%d'),'Index Name':'NIFTY 50','Total Returns Index':prices})
    payload=frame.to_csv(index=False,lineterminator='\n').encode('utf-8')
    source=destination/f'SYNTHETIC_NIFTY_TRI_{digest(payload.hex())[:12]}.csv'
    if source.exists() and source.read_bytes() != payload:
        raise ValueError('Existing demo source differs; use a new output directory')
    if not source.exists(): source.write_bytes(payload)
    # Each implementation version gets its own demo ledger; earlier demonstrations remain intact.
    demo_output=Path(output)/'demo_versions'/digest(fingerprint(cfg))[:12]
    return run_daily(config=config,source=source,as_of=str(dates[-1].date()),output=demo_output,mode='demo')


def record_review(ledger_path, run_id, reviewer, note, kind='acknowledgement'):
    if kind not in {'acknowledgement','decision'}: raise ValueError('Unknown review record type')
    if not Path(ledger_path).is_file(): raise ValueError('Ledger does not exist')
    if not reviewer.strip() or not note.strip(): raise ValueError('Reviewer and note are required')
    with Ledger(ledger_path) as ledger:
        if ledger.get('alert',run_id) is None: raise ValueError('Unknown alert run ID')
        payload=dict(run_id=run_id,reviewer=reviewer.strip(),note=note.strip())
        key=digest(payload)
        ledger.append_batch([(kind,key,payload)])
        return payload


def record_outcome(ledger_path, run_id, source, retrieved_at=None):
    """Attach an observed return separately; no forecast or alert can be edited."""
    from volrisk.data.nse_csv import read_tri_csv
    from volrisk.data.nse_json import read_tri_json
    from volrisk.data.storage import sha256
    from volrisk.forecasting.base import _json_ready
    source=Path(source)
    if not Path(ledger_path).is_file(): raise ValueError('Ledger does not exist')
    source_hash=sha256(source)
    with Ledger(ledger_path) as ledger:
        alert=ledger.get('alert',run_id)
        if alert is None or alert['target_session'] is None: raise ValueError('Unknown alert or target session')
        if alert['level'] not in {'NORMAL','ELEVATED','CRITICAL'}: raise ValueError('Cannot score an unissued forecast')
        now=pd.Timestamp.now(tz='UTC')
        if alert['mode']=='live':
            close=(pd.Timestamp(alert['target_session'])+pd.Timedelta(hours=15,minutes=30)).tz_localize('Asia/Kolkata')
            if now < close: raise ValueError('Target session has not closed')
        reader=read_tri_json if source.suffix.lower()=='.json' else read_tri_csv
        frame,_,_=reader(source)
        if frame.date.isna().any() or frame.date.duplicated().any(): raise ValueError('Outcome source has invalid or duplicate dates')
        if alert['mode']!='live' and (frame.date>pd.Timestamp('2024-12-31')).any():
            raise ValueError('Preview outcomes must not read the sealed period')
        pair=frame.set_index('date').reindex(pd.to_datetime([alert['as_of'],alert['target_session']]))
        p=pd.to_numeric(pair.price,errors='coerce').to_numpy(dtype=float)
        if pair.price.map(lambda x:isinstance(x,(bool,np.bool_))).any(): raise ValueError('Boolean values are not prices')
        if not np.isfinite(p).all() or (p<=0).any(): raise ValueError('Outcome requires valid origin and target prices')
        # Check origin against the exact input vintage used at issuance.
        original=Path(ledger_path).parent/'runs'/run_id
        snapshots=list(original.glob('source.*'))
        if len(snapshots)!=1 or sha256(snapshots[0])!=alert['source_sha256']:
            raise ValueError('Issuance source snapshot is missing or changed')
        old_reader=read_tri_json if snapshots[0].suffix=='.json' else read_tri_csv
        old,_,_=old_reader(snapshots[0])
        old_p=float(old.set_index('date').loc[pd.Timestamp(alert['as_of']),'price'])
        if p[0]!=old_p: raise ValueError('Origin price was revised; reconcile vintages without rewriting the forecast')
        ret=float(np.log(p[1]/p[0]))
        retrieved=utc_timestamp(retrieved_at) if retrieved_at else None
        if retrieved is not None and retrieved>now: raise ValueError('Retrieval timestamp is in the future')
        payload=dict(run_id=run_id,target_session=alert['target_session'],log_return=ret,squared_return=ret*ret,
            event_elevated=abs(ret)>alert['thresholds']['event_elevated'],
            event_critical=abs(ret)>alert['thresholds']['event_critical'],source_sha256=source_hash,
            retrieved_at=retrieved.isoformat() if retrieved is not None else None)
        snapshot=original/f'outcome_{source_hash}{source.suffix.lower()}'
        raw=source.read_bytes()
        import hashlib
        if hashlib.sha256(raw).hexdigest()!=source_hash: raise ValueError('Outcome source changed during processing')
        if snapshot.exists():
            if sha256(snapshot)!=source_hash: raise ValueError('Outcome snapshot has changed')
        else:
            with snapshot.open('xb') as handle: handle.write(raw)
        ledger.append_batch([('outcome',run_id,_json_ready(payload))])
        return payload


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for command in ('demo','report'):
        p=sub.add_parser(command)
        p.add_argument('--config',default='config/daily_monitoring.toml')
        p.add_argument('--output',default='outputs/daily_risk')
        if command=='report':
            p.add_argument('--source',required=True,help='Official NIFTY gross TRI CSV or JSON export')
            p.add_argument('--as-of',required=True,help='Completed NSE session, YYYY-MM-DD')
            p.add_argument('--mode',choices=['preview','live'],default='preview')
            p.add_argument('--registration')
            p.add_argument('--source-confirmed',action='store_true')
            p.add_argument('--retrieved-at',help='Actual source retrieval timestamp including UTC offset, if known')
    p=sub.add_parser('register')
    p.add_argument('--config',default='config/daily_monitoring.toml'); p.add_argument('--output',required=True)
    p.add_argument('--approved-by',required=True)
    for command in ('acknowledge','decision','outcome','verify'):
        p=sub.add_parser(command); p.add_argument('--ledger',required=True)
        if command!='verify': p.add_argument('--run-id',required=True)
        if command in ('acknowledge','decision'):
            p.add_argument('--reviewer',required=True); p.add_argument('--note',required=True)
        if command=='outcome':
            p.add_argument('--source',required=True); p.add_argument('--retrieved-at')
    args=parser.parse_args(argv)
    try:
        if args.command=='demo': result,path=demo(args.config,args.output)
        elif args.command=='report':
            result,path=run_daily(config=args.config,source=args.source,as_of=args.as_of,output=args.output,
                mode=args.mode,registration=args.registration,source_confirmed=args.source_confirmed,retrieved_at=args.retrieved_at)
        elif args.command=='register':
            print(json.dumps(register(args.config,args.output,args.approved_by),indent=2)); return 0
        elif args.command=='verify':
            if not Path(args.ledger).is_file(): raise ValueError('Ledger does not exist')
            with Ledger(args.ledger) as ledger: print(f'Ledger verified: {ledger.verify()} records')
            return 0
        elif args.command in ('acknowledge','decision'):
            result=record_review(args.ledger,args.run_id,args.reviewer,args.note,
                'acknowledgement' if args.command=='acknowledge' else 'decision')
            print(json.dumps(result,indent=2)); return 0
        else:
            print(json.dumps(record_outcome(args.ledger,args.run_id,args.source,args.retrieved_at),indent=2)); return 0
        print(f"{result['mode'].upper()} | {result['level']} | {result['run_id']}\nReport: {path}")
        return 0 if result['level'] in {'NORMAL','ELEVATED','CRITICAL'} else 1
    except (ValueError,KeyError,OSError) as exc:
        print(f'Cannot complete command: {exc}',file=sys.stderr); return 2


if __name__=='__main__':
    raise SystemExit(main())
