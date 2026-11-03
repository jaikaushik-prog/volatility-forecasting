import json
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from volrisk.cli import main
from volrisk.data.pipeline import run_pipeline
from volrisk.data.storage import sha256, write_parquet


def add_tri(settings):
    settings.nifty_csv_dir.mkdir(parents=True)
    path = settings.nifty_csv_dir / "official.CSV"
    path.write_bytes(b"Index Name,Date,Total Returns Index\r\nNIFTY 50,2024-01-02,1000\r\nNIFTY 50,2024-01-03,1010\r\nNIFTY 50,2024-01-04,990\r\n")
    return path


def test_full_run_snapshots_reports_and_parquet_roundtrip(raw_frame, settings):
    source = add_tri(settings)
    result = run_pipeline(settings, downloader=lambda **kw: raw_frame)
    assert result["complete"] is True
    assert set(result["processed"]) == {"SPY", "VT", "NIFTY50_TRI"}
    report_dir = Path(result["report_dir"])
    assert (report_dir / "data_quality.md").exists()
    quality = json.loads((report_dir / "data_quality.json").read_text(encoding="utf-8"))
    assert all(a["status"] == "passed" for a in quality["assets"])
    manifest = json.loads((report_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["return_definitions"]["volatility_primary"] == "log_return"
    assert manifest["versions"]["pandas"]
    assert manifest["configuration"]["start"] == "2024-01-02"
    for asset in manifest["assets"]:
        raw = Path(asset["raw"][0]["path"])
        assert sha256(raw) == asset["raw"][0]["sha256"]
        frame = pd.read_parquet(result["processed"][asset["symbol"]])
        assert {"simple_return", "log_return", "daily_return"} <= set(frame)
        assert frame["asset"].nunique() == frame["currency"].nunique() == 1
        if asset["symbol"] == "NIFTY50_TRI":
            assert raw.read_bytes() == source.read_bytes()
            assert asset["acquisition"]["retrieved_at_utc"] is None
        else:
            # Parquet preserves timestamps/values, but not pandas' inferred frequency cache.
            assert_frame_equal(pd.read_parquet(raw), raw_frame, check_freq=False)


def test_missing_nifty_is_explicit_and_does_not_block_etfs(raw_frame, settings):
    result = run_pipeline(settings, downloader=lambda **kw: raw_frame)
    assert result["complete"] is False
    assert set(result["processed"]) == {"SPY", "VT"}
    missing = result["assets"][-1]
    assert missing["status"] == "missing_input"
    assert str(settings.nifty_csv_dir) in missing["issues"][0]["message"]


def test_failed_rerun_does_not_reuse_old_success(raw_frame, settings):
    first = run_pipeline(settings, downloader=lambda **kw: raw_frame)
    failed = run_pipeline(settings, downloader=lambda **kw: None)
    assert failed["processed"] == {}
    assert all(Path(p).exists() for p in first["processed"].values())
    latest = json.loads((settings.reports_dir / "latest.json").read_text())
    assert latest["run_id"] == failed["run_id"]
    assert latest["processed"] == {}
    manifest = json.loads(Path(failed["manifest"]).read_text())
    assert len(manifest["assets"][0]["failed_download_attempts"]) == 2


def test_bad_asset_not_published_and_other_asset_survives(raw_frame, settings):
    def fake(**kwargs):
        output = raw_frame.copy()
        if kwargs["tickers"] == "SPY":
            output["Close"] = [100, 0, 110]
        return output

    result = run_pipeline(settings, downloader=fake)
    assert result["assets"][0]["status"] == "failed"
    assert set(result["processed"]) == {"VT"}
    manifest = json.loads(Path(result["manifest"]).read_text())
    assert Path(manifest["assets"][0]["raw"][0]["path"]).exists()


def test_raw_parquet_cannot_be_overwritten(raw_frame, tmp_path):
    target = tmp_path / "raw.parquet"
    write_parquet(raw_frame, target, raw=True)
    with pytest.raises(FileExistsError):
        write_parquet(raw_frame, target, raw=True)


def test_cli_exit_codes_and_printed_missing_input(monkeypatch, settings, capsys):
    monkeypatch.setattr("volrisk.cli.load_settings", lambda path: settings)
    # Provide an existing config path for the provenance hash.
    config = settings.reports_dir.parent / "test_config.toml"
    config.write_text("# test only", encoding="utf-8")
    assert main(["--config", str(config), "--skip-download"]) == 1
    assert "missing_input" in capsys.readouterr().out


def test_missing_config_has_actionable_error(tmp_path, capsys):
    assert main(["--config", str(tmp_path / "absent.toml")]) == 2
    assert "Ingestion could not run" in capsys.readouterr().err
