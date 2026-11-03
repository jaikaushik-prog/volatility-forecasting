"""Acquire only historical NIFTYBEES bars ending 2024-12-31; immutable source frames."""
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parents[1]


def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=ROOT/'data/raw/stage5'/stamp
    folder.mkdir(parents=True)
    yf.set_tz_cache_location(str(ROOT/'data/raw/stage5/cache'))
    request=dict(tickers='NIFTYBEES.NS',start='2012-01-01',end='2025-01-01',interval='1d',
                 auto_adjust=False,back_adjust=False,actions=True,repair=False,keepna=True,
                 rounding=False,threads=False,progress=False,ignore_tz=True,multi_level_index=False,timeout=20)
    record={'request':request,'started_utc':datetime.now(timezone.utc).isoformat(),
            'raw_representation':'Unmodified yfinance DataFrame; Yahoo Close can already be split-adjusted; Adj Close includes vendor total-return adjustments',
            'status':'started','cutoff':'2024-12-31'}
    try:
        frame=yf.download(**request)
        if frame is None or frame.empty:raise ValueError('No historical rows returned')
        if pd.Timestamp(frame.index.max()).date().isoformat()>'2024-12-31':
            raise ValueError('Provider returned observations beyond permitted cutoff')
        frame.to_parquet(folder/'niftybees_source.parquet',index=True)
        record.update(status='RECEIVED_UNVERIFIED',rows=len(frame),first=str(frame.index.min()),
                      last=str(frame.index.max()),columns=list(frame.columns))
    except Exception as exc:
        record.update(status='FAILED',error=f'{type(exc).__name__}: {exc}')
    record['finished_utc']=datetime.now(timezone.utc).isoformat()
    (folder/'request.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,indent=2));print(str(folder))
    return 0 if record['status']=='RECEIVED_UNVERIFIED' else 2


if __name__=='__main__':raise SystemExit(main())
