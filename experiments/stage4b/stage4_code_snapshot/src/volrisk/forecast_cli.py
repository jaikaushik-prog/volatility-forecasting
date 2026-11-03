"""Command-line entry point for the volatility forecasting experiments (Sprint 2)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NEXUS volatility forecasting: walk-forward experiments and evaluation")
    parser.add_argument("--config", type=Path, default=Path("config/forecasting.toml"))
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a configured experiment end to end")
    run.add_argument("--experiment", required=True, help="Experiment name from [experiments.*]")
    run.add_argument("--assets", help="Comma-separated subset of assets")
    run.add_argument("--models", help="Comma-separated subset of the experiment's models")
    run.add_argument("--workers", type=int, default=1, help="Parallel (asset, model) tasks")
    run.add_argument("--include-holdout", action="store_true",
                     help="Unseal and evaluate the final holdout period (use only for the final report)")
    run.add_argument("--max-origins", type=int, help="Limit forecast origins per task (smoke tests only)")
    run.add_argument("--bootstrap-draws", type=int, help="Override bootstrap draws for the statistical tests")
    run.add_argument("--no-figures", action="store_true")
    run.add_argument("--publish", action="store_true", help="Copy tables/figures to reports/ regardless of configuration")
    run.add_argument("--no-publish", action="store_true", help="Never copy tables/figures to reports/")

    sub.add_parser("list-models", help="List registered model types and their implementation status")
    sub.add_parser("data-check", help="Report availability of options-surface and intraday data for Stage 4 families")

    args = parser.parse_args(argv)
    try:
        if args.command == "list-models":
            from volrisk.forecasting.registry import available_model_types
            for name, info in available_model_types().items():
                print(f"{name:18s} {info['family']:22s} {info['version']:16s} {info['implementation_status']}")
            return 0
        if args.command == "data-check":
            from volrisk.forecasting.realized_volatility import check_intraday_availability
            from volrisk.forecasting.stochastic_volatility import check_options_surface_availability
            root = args.config.resolve().parent.parent / "data"
            print(json.dumps({"options_surface": check_options_surface_availability(root),
                              "intraday": check_intraday_availability(root)}, indent=2))
            return 0
        from volrisk.evaluation.experiment import load_forecasting_config, run_experiment
        config = load_forecasting_config(args.config)
        if args.publish and args.no_publish:
            parser.error("--publish and --no-publish are mutually exclusive")
        publish = True if args.publish else (False if args.no_publish else None)
        manifest = run_experiment(config, args.experiment,
                                  assets=args.assets.split(",") if args.assets else None,
                                  models=args.models.split(",") if args.models else None,
                                  workers=args.workers, include_holdout=args.include_holdout,
                                  max_origins=args.max_origins, bootstrap_draws=args.bootstrap_draws,
                                  publish=publish, make_figures=not args.no_figures)
    except NotImplementedError as exc:
        print(f"Experiment cannot run: {exc}", file=sys.stderr)
        return 3
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Experiment could not run: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for summary in manifest["run_summaries"]:
        print(f"{summary['asset']:12s} {summary['model']:15s} origins={summary['n_origins']:5d} "
              f"valid={summary['n_valid_forecasts']:5d} missing={summary['n_missing_forecasts']:4d} "
              f"fits={summary['fit_attempts']:5d} failed={summary['fit_failures']:3d} "
              f"nonconv={summary['fit_nonconverged']:3d} runtime={summary['runtime_seconds']:.1f}s")
    print(f"Run {manifest['run_id']} | holdout sealed={manifest['holdout_sealed']} | published={manifest['published']} "
          f"| {manifest['run_dir']} | {manifest['runtime_seconds']:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
