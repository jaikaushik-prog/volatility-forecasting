"""Exploratory positive-VIX research using only saved pre-2025 Stage 4 panels."""
import argparse
import json
import sys
from .evaluation.stage4b_experiment import run_stage4b


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='config/stage4b.toml')
    parser.add_argument('--no-figures',action='store_true')
    args=parser.parse_args(argv)
    try:
        result=run_stage4b(args.config,make_figures=not args.no_figures)
    except (ValueError,KeyError,FileNotFoundError,FileExistsError,AssertionError) as exc:
        print(f'Stage 4B blocked: {exc}',file=sys.stderr)
        return 2
    print(json.dumps({k:result[k] for k in ('run_id','status','holdout_evaluated','independent_confirmation',
                                          'reproduction_passed','historical_artifacts_unchanged','summary')},indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
