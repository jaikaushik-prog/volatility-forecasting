"""Parse saved official NIFTY TRI responses without changing their source files."""

import json
from pathlib import Path

import pandas as pd

from volrisk.data.models import DataError, issue
from volrisk.data.nse_csv import key, NIFTY_NAMES, parse_date


def read_tri_json(path: Path, date_format: str = "") -> tuple[pd.DataFrame, list[dict], dict]:
    rows = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or not rows:
        raise DataError(f"{path.name}: expected a nonempty JSON array of TRI observations")
    records = []
    for number, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or not {"Index Name", "Date", "TotalReturnsIndex"} <= row.keys():
            raise DataError(f"{path.name}:{number}: require Index Name, Date and explicit gross TotalReturnsIndex")
        if key(str(row["Index Name"])) not in NIFTY_NAMES:
            raise DataError(f"{path.name}:{number}: Index Name is not NIFTY 50")
        value = row["TotalReturnsIndex"]
        records.append({"date": parse_date(str(row["Date"]), date_format),
                        "price": value.replace(",", "") if isinstance(value, str) else value,
                        "source_file": path.name, "source_row": number})
    frame = pd.DataFrame(records)
    issues = []
    if not frame["date"].dropna().is_monotonic_increasing:
        issues.append(issue("source_non_monotonic", "warning",
                            "Source dates were not ascending; normalized output is sorted.", source_file=path.name))
    return frame, issues, {"file": path.name, "format": "NSE JSON response", "input_rows": len(frame),
                           "price_column": "TotalReturnsIndex", "source_row_convention": "1-based JSON array position"}
