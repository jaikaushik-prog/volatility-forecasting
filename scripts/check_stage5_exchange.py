"""Archive narrowly dated exchange evidence; no post-2024 requests."""
from pathlib import Path
from datetime import datetime, timezone
import io,json,zipfile
import pandas as pd
from curl_cffi import requests

ROOT=Path(__file__).resolve().parents[1]


def main():
    folder=ROOT/'data/raw/stage5'/('exchange_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True)
    dates=['2023-11-12','2024-01-20','2024-03-02','2024-05-18','2024-06-03','2024-06-04','2024-06-05','2024-11-01']
    records=[]
    for day in dates:
        d=pd.Timestamp(day)
        if d<pd.Timestamp('2024-07-08'):
            url=f'https://nsearchives.nseindia.com/content/historical/EQUITIES/{d.year}/{d.strftime("%b").upper()}/cm{d.strftime("%d%b%Y").upper()}bhav.csv.zip'
        else:url=f'https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d.strftime("%Y%m%d")}_F_0000.csv.zip'
        record={'date':day,'url':url,'requested_utc':datetime.now(timezone.utc).isoformat()}
        try:
            response=requests.get(url,impersonate='chrome',timeout=20)
            record['http_status']=response.status_code
            (folder/(day+'.response')).write_bytes(response.content)
            if response.status_code!=200:raise ValueError('HTTP '+str(response.status_code))
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                frame=pd.read_csv(archive.open(archive.namelist()[0]))
            frame.columns=frame.columns.str.strip()
            key='SYMBOL' if 'SYMBOL' in frame else 'TckrSymb'
            rows=frame[frame[key].astype(str).str.strip().eq('NIFTYBEES')]
            if rows.empty:raise ValueError('NIFTYBEES not present')
            rows.to_csv(folder/(day+'_niftybees.csv'),index=False)
            record.update(status='received',rows=len(rows),columns=list(rows.columns))
        except Exception as exc:record.update(status='failed',error=str(exc))
        records.append(record)
        print(day,record['status'],flush=True)
    (folder/'manifest.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    print(folder)


if __name__=='__main__':main()
