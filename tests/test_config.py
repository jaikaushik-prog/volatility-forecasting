from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from volrisk.config import DownloadSettings, ValidationSettings, load_settings


def test_default_configuration_is_reproducible_from_other_cwd(tmp_path, monkeypatch):
    config = Path(__file__).resolve().parents[1] / "config/ingestion.toml"
    monkeypatch.chdir(tmp_path)
    settings = load_settings(config)
    assert settings.start == date(2012, 1, 1)
    assert settings.end == date(2026, 11, 2)
    assert settings.raw_dir == config.parent.parent / "data/raw"
    assert settings.etf_snapshot_dir == config.parent.parent / "data/raw/source_snapshots/20261103/yahoo"
    assert settings.nifty_json_dir == config.parent.parent / "data/raw/source_snapshots/20261103/nifty"


@pytest.mark.parametrize("change", [
    {"start": date(2025, 1, 1)},
    {"download": DownloadSettings(attempts=0)},
    {"download": DownloadSettings(retry_backoff_seconds=-1)},
    {"validation": ValidationSettings(extreme_simple_return=float("nan"))},
    {"validation": ValidationSettings(stale_observations=1)},
])
def test_invalid_configuration_rejected(settings, change):
    with pytest.raises(ValueError):
        replace(settings, **change)
