"""Separate exploratory economics command; no live execution capability."""
import argparse
from volrisk.economics.experiment import register, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='config/stage5.toml')
    parser.add_argument('command',choices=['register','run'])
    args=parser.parse_args()
    if args.command=='register':
        value=register(args.config)
        print('Stage 5 registered:',value['registered_at_utc'])
    else:
        run(args.config)


if __name__=='__main__':
    main()
