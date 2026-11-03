"""H4 monitoring command line (DRAFT). Validates the draft and computes development-only draft thresholds.

`start` deliberately refuses to run until the protocol is FROZEN and registered. No trading exists here.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from volrisk.data.storage import sha256, write_json
from volrisk.monitoring import spec
from volrisk.monitoring.thresholds import production_thresholds, provisional_thresholds


def draft_thresholds(config_path, root='.', out='reports/h4_draft'):
    config = spec.load(config_path); root = Path(root); out = root/out; out.mkdir(parents=True,exist_ok=True)
    thr, evt, bur, z = production_thresholds(config,root)
    prov = provisional_thresholds(config,root)
    pd.concat([thr,prov]).to_csv(out/'draft_alert_thresholds.csv',index=False)
    evt.to_csv(out/'draft_event_thresholds.csv',index=False)
    bur.to_csv(out/'draft_alert_burden_development.csv',index=False)
    zq = pd.DataFrame([dict(asset=a,n=len(v),q01=float(np.quantile(v,.01)),q05=float(np.quantile(v,.05)),
                            es05=float(v[v<=np.quantile(v,.05)].mean()),sd=float(v.std(ddof=1))) for a,v in z.items()])
    zq.to_csv(out/'draft_standardized_return_quantiles.csv',index=False)
    pd.DataFrame(spec.model_inventory(config)).to_csv(out/'model_inventory.csv',index=False)
    manifest = dict(status=config['protocol']['status'],config=str(config_path),config_sha256=sha256(Path(config_path)),
                    note='DRAFT development-only thresholds for review; not frozen; no prospective data read',
                    latest_target_date_read=max(config['models']['development_window'][1],config['models']['provisional']['existing_development_window'][1]),
                    outputs={p.name:sha256(p) for p in sorted(out.glob('*.csv'))})
    write_json(manifest,out/'draft_manifest.json')
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['validate','draft-thresholds','start'])
    parser.add_argument('--config',default='config/h4_monitoring.toml')
    parser.add_argument('--root',default='.')
    parser.add_argument('--registration',default=None)
    args = parser.parse_args()
    config = spec.load(args.config)
    if args.command == 'validate':
        print('H4 configuration valid; status:',config['protocol']['status'])
    elif args.command == 'draft-thresholds':
        print('Draft thresholds written to',draft_thresholds(args.config,args.root))
    else:
        registration = json.loads(Path(args.registration).read_text()) if args.registration else None
        spec.assert_prospective_allowed(config,args.config,registration)
        raise NotImplementedError('Prospective collection is not implemented in the draft; build after freeze')


if __name__ == '__main__':
    main()
