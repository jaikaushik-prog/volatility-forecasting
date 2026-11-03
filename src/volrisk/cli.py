"""One entry point for acquisition, validation, storage and reporting."""

import argparse
from dataclasses import replace
from pathlib import Path
import sys

from volrisk.config import load_settings
from volrisk.data.pipeline import run_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NEXUS ingestion and Sprint 1B research data audit")
    parser.add_argument("--config", type=Path, default=Path("config/ingestion.toml"))
    parser.add_argument("--audit", action="store_true", help="Audit the saved ingestion run offline; do not download or reingest")
    parser.add_argument("--input-manifest", type=Path, help="Explicit ingestion manifest for --audit (default reports/latest.json)")
    nifty_group = parser.add_mutually_exclusive_group()
    nifty_group.add_argument("--nifty-csv-dir", type=Path, help="Use official NSE TRI CSVs instead of configured JSON snapshots")
    nifty_group.add_argument("--nifty-json-dir", type=Path, help="Use saved NSE responses and their provenance.json")
    etf_group = parser.add_mutually_exclusive_group()
    etf_group.add_argument("--etf-snapshot-dir", type=Path, help="Use saved yfinance Parquet files and retrieval metadata")
    etf_group.add_argument("--download-etfs", action="store_true", help="Retrieve fresh SPY and VT data instead of configured snapshots")
    etf_group.add_argument("--skip-download", action="store_true", help="Import local NSE files only; ETF status will be skipped")
    parser.add_argument("--fail-on-warning", action="store_true", help="Return exit code 1 for validation warnings as well")
    args = parser.parse_args(argv)
    if args.input_manifest and not args.audit:
        parser.error('--input-manifest requires --audit')
    if args.audit and any((args.nifty_csv_dir, args.nifty_json_dir, args.etf_snapshot_dir, args.download_etfs, args.skip_download)):
        parser.error('--audit uses the selected saved manifest; ingestion overrides cannot be combined with it')
    try:
        settings = load_settings(args.config)
        if args.audit:
            from volrisk.data.audit import run_audit
            result = run_audit(settings, input_manifest=args.input_manifest, config_path=args.config)
            for detail in result['assets']:
                item = detail['summary']
                print(f"{item['asset']} ({item['currency']}): {item['validation_status']} | observations={item.get('observation_count')} | research_ready={item['research_ready']}")
                if item.get('failure'):
                    print(f"  {item['failure']}")
            print(f"Audit: {result['audit_id']} | cache reused={result['cache_reused']} | reports={result['report_dir']}")
            warnings = any(d['summary']['validation_status'] == 'WARNING' for d in result['assets'])
            return 0 if result['complete'] and not (args.fail_on_warning and warnings) else 1
        if args.nifty_csv_dir:
            settings = replace(settings, nifty_csv_dir=args.nifty_csv_dir.resolve(), nifty_json_dir=None)
        if args.nifty_json_dir:
            settings = replace(settings, nifty_json_dir=args.nifty_json_dir.resolve())
        if args.etf_snapshot_dir:
            settings = replace(settings, etf_snapshot_dir=args.etf_snapshot_dir.resolve())
        if args.download_etfs:
            settings = replace(settings, etf_snapshot_dir=None)
        result = run_pipeline(settings, skip_download=args.skip_download, config_path=args.config)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        label = 'Audit' if args.audit else 'Ingestion'
        print(f"{label} could not run: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for item in result["assets"]:
        print(f"{item['asset']}: {item['status']} | observations={item.get('observation_count', 'n/a')} "
              f"| {item.get('earliest', 'n/a')} .. {item.get('latest', 'n/a')}")
        for notice in item["issues"]:
            if notice["severity"] != "info":
                print(f"  {notice['code']}: {notice['message']}")
    print(f"Reports: {result['report_dir']}")
    warnings = any(item["status"] == "warning" for item in result["assets"])
    return 0 if result["complete"] and not (args.fail_on_warning and warnings) else 1
