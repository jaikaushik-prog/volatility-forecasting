from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from volrisk.data.models import ASSETS, DataError
from volrisk.data.normalization import normalize_nifty
from volrisk.data.validation import validate


def load(paths, settings, date_format=""):
    return normalize_nifty(paths, ASSETS[2], settings.start, settings.end, date_format)


def test_multiple_periods_variations_and_overlap(tmp_path, settings):
    first, second = tmp_path / "a.csv", tmp_path / "b.CSV"
    first.write_text('Official export\nIndex Name,Date,Total Returns Index,Net Total Return Index\n'
                     'NIFTY 50,03-Jan-2024,"1,100.00",1050\nNIFTY 50,02-Jan-2024,"1,000.00",950\n', encoding="utf-8-sig")
    second.write_text("DATE;TOTAL_RETURN_INDEX\n03/01/2024;1100\n2024-01-04;990\n", encoding="utf-8")
    data = load([second, first], settings)
    assert data.frame["price"].tolist() == [1000, 1100, 990]
    np.testing.assert_allclose(data.frame["simple_return"].iloc[1:], [.1, -.1])
    assert data.frame["currency"].eq("INR").all()
    assert any(i["code"] == "source_non_monotonic" for i in data.issues)
    assert any(i["code"] == "identical_duplicates_collapsed" for i in data.issues)
    assert len(data.details["files"]) == 2


@pytest.mark.parametrize("header", ["Close", "Price", "NIFTY 50", "Net Total Return Index"])
def test_price_and_net_return_columns_rejected(tmp_path, settings, header):
    path = tmp_path / "wrong.csv"
    path.write_text(f"Date,{header}\n2024-01-02,100\n", encoding="utf-8")
    with pytest.raises(DataError, match="explicit gross TRI"):
        load([path], settings)


def test_wrong_index_identity_rejected(tmp_path, settings):
    path = tmp_path / "wrong.csv"
    path.write_text("IndexName,Date,Total Returns Index\nNIFTY NEXT 50,2024-01-02,100\n", encoding="utf-8")
    with pytest.raises(DataError, match="not NIFTY 50"):
        load([path], settings)


def test_conflicting_periods_rejected(tmp_path, settings):
    paths = [tmp_path / "a.csv", tmp_path / "b.csv"]
    for path, price in zip(paths, [100, 101]):
        path.write_text(f"Date,Total Returns Index\n2024-01-02,{price}\n", encoding="utf-8")
    with pytest.raises(DataError, match="Conflicting duplicate"):
        load(paths, settings)


def test_invalid_dates_and_prices_retained_for_validation(tmp_path, settings):
    path = tmp_path / "bad.csv"
    path.write_text("Date,TRI\n2024-01-02,100\n2024-01-03,N/A\n31/02/2024,110\n", encoding="utf-8")
    data = load([path], settings)
    report = validate(data, ASSETS[2], settings.start, settings.end, settings.validation)
    assert len(data.frame) == 3
    assert report["status"] == "failed"
    assert {"invalid_date", "missing_or_invalid_price"} <= {i["code"] for i in report["issues"]}


def test_day_first_default_and_explicit_month_first(tmp_path, settings):
    path = tmp_path / "numeric.csv"
    path.write_text("Date,TRI\n01/02/2024,100\n", encoding="utf-8")
    wide = replace(settings, start=date(2024, 1, 1), end=date(2024, 2, 10))
    assert load([path], wide).frame["date"].iloc[0].date() == date(2024, 2, 1)
    assert load([path], wide, "%m/%d/%Y").frame["date"].iloc[0].date() == date(2024, 1, 2)


def test_utf16_tab_separated_and_trailing_empty_field(tmp_path, settings):
    path = tmp_path / "unicode.csv"
    path.write_text("Date\tTotal Returns Index\t\n02-Jan-2024\t100\t\n", encoding="utf-16")
    data = load([path], settings)
    assert data.frame["price"].tolist() == [100]


def test_malformed_row_not_silently_dropped(tmp_path, settings):
    path = tmp_path / "broken.csv"
    path.write_text("Date,TRI\n2024-01-02,1,000\n", encoding="utf-8")
    with pytest.raises(DataError, match="CSV fields"):
        load([path], settings)
