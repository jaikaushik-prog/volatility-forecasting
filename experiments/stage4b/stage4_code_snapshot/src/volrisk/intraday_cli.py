"""One command for intraday ingestion, normalization, measures and quality reports."""
import argparse
import json
import sys
from volrisk.data.intraday.pipeline import run_integration


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='config/intraday.toml')
    parser.add_argument('--no-figures',action='store_true')
    args=parser.parse_args(argv)
    try:
        manifest=run_integration(args.config,make_figures=not args.no_figures)
    except (ValueError,FileNotFoundError,FileExistsError) as exc:
        print(f'Intraday integration failed: {exc}',file=sys.stderr)
        return 2
    print(json.dumps({'run_id':manifest['run_id'],'readiness':manifest['research_readiness'],
                      'summary':manifest['summary']},indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
