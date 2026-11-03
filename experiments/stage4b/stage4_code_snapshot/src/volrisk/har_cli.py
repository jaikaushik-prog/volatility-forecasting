"""Stage 4 provisional HAR-RV workflow; no holdout-unsealing or trading command."""
import argparse
import json
import sys
from volrisk.evaluation.har_experiment import run_har_experiment


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='config/har_rv.toml')
    parser.add_argument('--no-figures',action='store_true')
    parser.add_argument('command',choices=['run','check'],nargs='?',default='run')
    args=parser.parse_args(argv)
    try:
        result=run_har_experiment(args.config,make_figures=not args.no_figures,readiness_only=args.command=='check')
    except (ValueError,FileNotFoundError,FileExistsError,KeyError) as exc:
        print(f'Stage 4 could not run: {exc}',file=sys.stderr)
        return 2
    print(json.dumps({k:result[k] for k in ('status','run_id','holdout_evaluated','forecast_rows','summary','blocker') if k in result},indent=2))
    return 3 if result['status']=='BLOCKED_CRITICAL_DATA_GATE' else 0


if __name__=='__main__':
    raise SystemExit(main())
