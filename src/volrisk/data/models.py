"""Small shared contracts; no forecasting or portfolio logic."""

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class Asset:
    symbol: str
    name: str
    currency: str
    source: str
    source_url: str
    price_convention: str
    timezone: str = "America/New_York"
    calendar: str = "NYSE"


ASSETS = (
    Asset("SPY", "SPDR S&P 500 ETF", "USD", "Yahoo Finance via yfinance",
          "https://finance.yahoo.com/quote/SPY/history/",
          "yfinance_auto_adjusted_close_dividends_and_splits"),
    Asset("VT", "Vanguard Total World Stock ETF", "USD", "Yahoo Finance via yfinance",
          "https://finance.yahoo.com/quote/VT/history/",
          "yfinance_auto_adjusted_close_dividends_and_splits"),
    Asset("NIFTY50_TRI", "NIFTY 50 Total Returns Index", "INR", "NSE Indices official CSV",
          "https://www.niftyindices.com/reports/historical-data",
          "official_gross_total_return_index_level", "Asia/Kolkata", "NSE"),
)


class DataError(ValueError):
    """An actionable source or data-contract failure."""


class DownloadError(DataError):
    def __init__(self, message: str, attempts: list[dict]):
        super().__init__(message)
        self.attempts = attempts


@dataclass
class NormalizedData:
    frame: pd.DataFrame
    issues: list[dict] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def issue(code: str, severity: str, message: str, **details) -> dict:
    return {"code": code, "severity": severity, "message": message, **details}
