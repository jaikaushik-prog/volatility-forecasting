"""Read a versionable TOML configuration using the Python standard library."""

from dataclasses import asdict, dataclass, field
from datetime import date
import math
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class DownloadSettings:
    attempts: int = 3
    timeout_seconds: int = 20
    retry_backoff_seconds: float = 2.0


@dataclass(frozen=True)
class ValidationSettings:
    extreme_simple_return: float = 0.10
    max_calendar_gap_days: int = 7
    stale_observations: int = 3
    min_observations: int = 200
    coverage_tolerance_days: int = 7


@dataclass(frozen=True)
class AuditSettings:
    calendar_file: Path | None = None
    evidence_dir: Path | None = None
    return_rtol: float = 1e-10
    return_atol: float = 1e-12
    mad_z_threshold: float = 8.0
    mad_min_abs_return: float = 0.03
    mad_min_observations: int = 30
    reversal_min_move: float = 0.08
    reversal_max_log_residual: float = 0.02
    split_log_tolerance: float = 0.03
    adjustment_rtol: float = 1e-5
    adjustment_factor_atol: float = 1e-4
    annualization_sessions: int = 252
    event_plot_limit: int = 8

    def __post_init__(self):
        for name, value in asdict(self).items():
            if name.endswith('_file') or name.endswith('_dir'):
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be finite and positive')
        for name in ('mad_min_observations', 'annualization_sessions', 'event_plot_limit'):
            if type(getattr(self, name)) is not int:
                raise ValueError(f'{name} must be an integer')
        if self.mad_min_observations < 3:
            raise ValueError('mad_min_observations must be at least 3')


@dataclass(frozen=True)
class Settings:
    start: date
    end: date
    raw_dir: Path
    processed_dir: Path
    reports_dir: Path
    nifty_csv_dir: Path
    etf_snapshot_dir: Path | None = None
    nifty_json_dir: Path | None = None
    nifty_date_format: str = ""
    download: DownloadSettings = field(default_factory=DownloadSettings)
    validation: ValidationSettings = field(default_factory=ValidationSettings)
    audit: AuditSettings = field(default_factory=AuditSettings)

    def __post_init__(self):
        if self.start > self.end:
            raise ValueError("start must not be after end")
        integers = {
            "attempts": (self.download.attempts, 1),
            "timeout_seconds": (self.download.timeout_seconds, 1),
            "max_calendar_gap_days": (self.validation.max_calendar_gap_days, 1),
            "stale_observations": (self.validation.stale_observations, 2),
            "min_observations": (self.validation.min_observations, 1),
            "coverage_tolerance_days": (self.validation.coverage_tolerance_days, 0),
        }
        for name, (value, minimum) in integers.items():
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        for name, value in (("retry_backoff_seconds", self.download.retry_backoff_seconds),
                            ("extreme_simple_return", self.validation.extreme_simple_return)):
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.validation.extreme_simple_return == 0:
            raise ValueError("extreme_simple_return must be positive")

    def as_dict(self) -> dict:
        return asdict(self)


def load_settings(path: Path) -> Settings:
    path = path.resolve()
    with path.open("rb") as handle:
        document = tomllib.load(handle)
    extra = set(document) - {"ingestion", "download", "validation", "audit"}
    if extra:
        raise ValueError(f"Unknown configuration sections: {sorted(extra)}")
    section = dict(document["ingestion"])
    # Paths are relative to the repository (parent of config/), never the shell cwd.
    root = path.parent.parent
    for name in ("raw_dir", "processed_dir", "reports_dir", "nifty_csv_dir"):
        section[name] = (root / section[name]).resolve()
    for name in ("etf_snapshot_dir", "nifty_json_dir"):
        if name in section:
            section[name] = (root / section[name]).resolve() if section[name] else None
    for name in ("start", "end"):
        section[name] = date.fromisoformat(str(section[name]))
    audit = dict(document.get('audit', {}))
    for name in ('calendar_file', 'evidence_dir'):
        if name in audit:
            audit[name] = (root / audit[name]).resolve() if audit[name] else None
    return Settings(**section,
                    download=DownloadSettings(**document.get("download", {})),
                    validation=ValidationSettings(**document.get("validation", {})),
                    audit=AuditSettings(**audit))
