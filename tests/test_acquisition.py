from datetime import date

import pandas as pd
import pytest

from volrisk.config import DownloadSettings
from volrisk.data.acquisition import download_etf
from volrisk.data.models import DownloadError


def test_request_is_adjusted_inclusive_and_keeps_actions(raw_frame):
    requests = []

    def fake(**kwargs):
        requests.append(kwargs)
        return raw_frame

    actual, audit = download_etf("SPY", date(2012, 1, 1), date(2026, 10, 30),
                                DownloadSettings(), downloader=fake)
    assert actual is raw_frame
    request = requests[0]
    assert request["start"] == "2012-01-01"
    assert request["end"] == "2026-10-31"
    assert request["auto_adjust"] is True
    assert request["actions"] is True
    assert request["keepna"] is True
    assert request["repair"] is False
    assert request["interval"] == "1d"
    assert audit["retrieved_at_utc"].endswith("+00:00")


def test_retry_empty_then_exception_then_success(raw_frame):
    calls, delays = [], []

    def fake(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return pd.DataFrame()
        if len(calls) == 2:
            raise TimeoutError("test timeout")
        return raw_frame

    _, audit = download_etf("VT", date(2024, 1, 2), date(2024, 1, 4),
                            DownloadSettings(), downloader=fake, sleep=delays.append)
    assert delays == [2.0, 4.0]
    assert [a["status"] for a in audit["attempts"]] == ["failed", "failed", "success"]


@pytest.mark.parametrize("response", [None, pd.DataFrame(), "not a dataframe"])
def test_explicit_failure_on_empty_or_invalid_download(response):
    with pytest.raises(DownloadError) as error:
        download_etf("SPY", date(2024, 1, 2), date(2024, 1, 4),
                     DownloadSettings(attempts=2, retry_backoff_seconds=0),
                     downloader=lambda **kw: response, sleep=lambda seconds: None)
    assert len(error.value.attempts) == 2
    assert "download failed" in str(error.value)
