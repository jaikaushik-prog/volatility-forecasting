"""Parse manually downloaded official NSE Indices TRI CSVs, never scrape NSE."""

import csv
from datetime import datetime
import io
from pathlib import Path
import re

import pandas as pd

from volrisk.data.models import DataError, issue


DATE_HEADERS = {"date", "indexdate", "historicaldate", "pricedate", "timestamp"}
TRI_HEADERS = {"tri", "trivalue", "totalreturnindex", "totalreturnsindex",
               "totalreturnindexvalue", "totalreturnsindexvalue", "totalreturnsindexvalues",
               "nifty50tri", "nifty50totalreturnindex", "nifty50totalreturnsindex"}
NAME_HEADERS = {"index", "indexname", "name"}
NIFTY_NAMES = {"nifty50", "nifty50tri", "nifty50totalreturnindex", "nifty50totalreturnsindex"}
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d-%b-%Y", "%d-%B-%Y",
                "%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
                "%d-%b-%y")


def key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower())


def parse_date(value: str, date_format: str = "") -> pd.Timestamp:
    for fmt in (date_format,) if date_format else DATE_FORMATS:
        try:
            return pd.Timestamp(datetime.strptime(value.strip(), fmt))
        except ValueError:
            pass
    return pd.NaT


def read_tri_csv(path: Path, date_format: str = "") -> tuple[pd.DataFrame, list[dict], dict]:
    payload = path.read_bytes()
    encoding = "utf-16" if payload.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    try:
        text = payload.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp1252"
        text = payload.decode(encoding)
    header = None
    for delimiter in (",", ";", "\t"):
        rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
        for offset, row in enumerate(rows[:50]):
            keys = [key(c) for c in row]
            dates = [i for i, k in enumerate(keys) if k in DATE_HEADERS]
            prices = [i for i, k in enumerate(keys) if k in TRI_HEADERS]
            if dates and prices:
                if len(dates) != 1 or len(prices) != 1:
                    raise DataError(f"{path.name}: ambiguous date/TRI columns")
                header = (rows, offset, row, keys, dates[0], prices[0], delimiter)
                break
        if header is not None:
            break
    if header is None:
        raise DataError(f"{path.name}: require Date and an explicit gross TRI column, e.g. "
                        "'Total Returns Index'. Close/Price/Net Total Return Index are not substitutes.")
    rows, offset, columns, keys, date_col, price_col, delimiter = header
    name_cols = [i for i, k in enumerate(keys) if k in NAME_HEADERS]
    records = []
    for line, row in enumerate(rows[offset + 1:], start=offset + 2):
        if not any(cell.strip() for cell in row):
            continue
        # Accommodate NSE's trailing empty CSV fields, but never discard nonempty cells.
        while len(row) > len(columns) and not row[-1].strip():
            row.pop()
        if len(row) != len(columns):
            raise DataError(f"{path.name}:{line}: expected {len(columns)} CSV fields, got {len(row)}")
        if any(key(row[i]) not in NIFTY_NAMES for i in name_cols):
            raise DataError(f"{path.name}:{line}: Index Name is not NIFTY 50; refusing to relabel it")
        records.append({
            "date": parse_date(row[date_col], date_format),
            "price": row[price_col].strip().replace(",", ""),
            "source_file": path.name, "source_row": line,
        })
    if not records:
        raise DataError(f"{path.name}: CSV has no observations")
    frame = pd.DataFrame(records)
    issues = []
    dates = frame["date"].dropna()
    if not dates.is_monotonic_increasing:
        issues.append(issue("source_non_monotonic", "warning",
                            "Source dates were not ascending; normalized output is sorted.",
                            source_file=path.name))
    if not name_cols:
        issues.append(issue("index_identity_from_manual_selection", "info",
                            "CSV omits index identity. NIFTY 50 selection and official origin must be verified by the importer.",
                            source_file=path.name))
    return frame, issues, {
        "file": path.name, "encoding": encoding, "delimiter": delimiter,
        "header_row": offset + 1, "date_column": columns[date_col],
        "price_column": columns[price_col], "input_rows": len(frame),
        "date_format": date_format or "ISO/named-month/day-first numeric",
        "index_identity_in_csv": bool(name_cols),
    }
