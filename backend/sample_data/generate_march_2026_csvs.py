"""
Generate daily synthetic SFTR reconciliation CSVs for March 2026.

Output:
  backend/sample_data/march_2026/
    - sftr_reconciliation_2026-03-01.csv
    - ...
    - sftr_reconciliation_2026-03-31.csv
    - audit_summary.json

Design goals:
  - One CSV per day in March 2026
  - 21, 25, or 30 operations per day
  - Every generated trade has controlled UNMATCH counts
  - Target mismatch levels cycle through: 10, 20, 30, 40, 50, 60
  - Data is deterministic and valid for the current parser/comparison engine
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

FIELDS_PATH = ROOT.parent / "app" / "data" / "sftr_fields.json"
OUT_DIR = ROOT / "march_2026"
AUDIT_PATH = OUT_DIR / "audit_summary.json"

with FIELDS_PATH.open(encoding="utf-8") as f:
    FIELDS = json.load(f)


def normalize_col(name: str) -> str:
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


FIELD_COLS = [(normalize_col(field["name"]), field) for field in FIELDS]

MISMATCH_LEVELS = [10, 20, 30, 40, 50, 60]
OPS_PATTERN = [21, 25, 30]

LEI_POOL = [
    "7LTWFZYICNSX8D621K86",
    "VUJNWIVNFNEBFQSQE965",
    "R0MUWSFPU8MPRO8K5P81",
    "5493001KJTIIGC8Y1R12",
]

ISIN_POOL = [
    "DE0001135275",
    "FR0013451524",
    "XS0971721963",
    "US0378331005",
]

CURRENCY_POOL = ["EUR", "USD", "GBP", "CHF"]
COUNTRY_POOL = ["ES", "FR", "DE", "IT", "NL", "BE"]
TEXT_POOL = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT"]


def stable_index(*parts: object, modulo: int) -> int:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:12], 16) % modulo


def day_operation_count(day: date) -> int:
    return OPS_PATTERN[(day.day - 1) % len(OPS_PATTERN)]


def target_unmatches(day: date, trade_index: int) -> int:
    return MISMATCH_LEVELS[(day.day + trade_index) % len(MISMATCH_LEVELS)]


def get_obligation(field: dict, sft_type: str, action_type: str) -> str:
    return field.get("obligation", {}).get(sft_type, {}).get(action_type, "-")


def mismatch_candidates(sft_type: str, action_type: str) -> list[dict]:
    eligible = []
    order = {"M": 0, "C": 1, "O": 2}
    for field in FIELDS:
        obligation = get_obligation(field, sft_type, action_type)
        if obligation == "-":
            continue
        eligible.append(field)
    eligible.sort(key=lambda field: order.get(get_obligation(field, sft_type, action_type), 9))
    return eligible


def timestamp_for(day: date, trade_index: int, field_number: int) -> str:
    hour = 8 + ((trade_index + field_number) % 10)
    minute = (field_number * 7 + trade_index * 3) % 60
    second = (field_number * 11 + trade_index * 5) % 60
    return f"{day.isoformat()}T{hour:02d}:{minute:02d}:{second:02d}Z"


def offset_date(day: date, days: int) -> date:
    return day + timedelta(days=days)


def base_pair(field: dict, day: date, trade_index: int) -> tuple[str, str]:
    fmt = field.get("format", "").lower()
    name = field["name"].lower()
    number = field["number"]
    table = field["table"]

    if field.get("is_mirror", False):
        if "margin" in name and "transaction" in name:
            return ("MRGG", "MRGE")
        return ("GIVE", "TAKE")

    if "timestamp" in fmt or "date-time" in fmt:
        value = timestamp_for(day, trade_index, number)
        return value, value

    if "date" in fmt:
        value = day.isoformat()
        return value, value

    if "boolean" in fmt or "true/false" in fmt:
        value = "true" if stable_index(table, number, day.day, trade_index, modulo=2) == 0 else "false"
        return value, value

    if "lei" in fmt or "lei" in name:
        lei = LEI_POOL[stable_index(name, day.day, trade_index, modulo=len(LEI_POOL))]
        return lei, lei

    if "isin" in fmt or "isin" in name:
        isin = ISIN_POOL[stable_index(name, day.day, trade_index, modulo=len(ISIN_POOL))]
        return isin, isin

    if "currency" in fmt or "iso 4217" in fmt or "currency" in name:
        currency = CURRENCY_POOL[stable_index(name, day.day, trade_index, modulo=len(CURRENCY_POOL))]
        return currency, currency

    if "iso 3166" in fmt or "country" in name or "jurisdiction" in name:
        country = COUNTRY_POOL[stable_index(name, day.day, trade_index, modulo=len(COUNTRY_POOL))]
        return country, country

    if any(token in fmt for token in ["decimal", "amount", "numeric", "integer", "percentage", "rate", "number"]):
        base = 1000000 + (day.day * 10000) + (trade_index * 1000) + (table * 100) + number
        if "rate" in fmt or "percentage" in fmt:
            value = f"{(0.0100 + ((trade_index + number) % 17) / 1000):.4f}"
        elif "integer" in fmt:
            value = str(1 + ((trade_index + number) % 20))
        else:
            value = f"{base:.2f}"
        return value, value

    token = TEXT_POOL[stable_index(name, day.day, trade_index, modulo=len(TEXT_POOL))]
    value = f"{token}_{table}_{number}_{day.day:02d}_{trade_index:02d}"
    return value, value


def mismatch_pair(field: dict, day: date, trade_index: int) -> tuple[str, str]:
    fmt = field.get("format", "").lower()
    name = field["name"].lower()
    number = field["number"]
    table = field["table"]

    if field.get("is_mirror", False):
        if "margin" in name and "transaction" in name:
            return ("MRGG", "MRGG_X")
        return ("GIVE", "GIVE_X")

    if "timestamp" in fmt or "date-time" in fmt:
        return timestamp_for(day, trade_index, number), timestamp_for(offset_date(day, 1), trade_index, number)

    if "date" in fmt:
        return day.isoformat(), offset_date(day, 1).isoformat()

    if "boolean" in fmt or "true/false" in fmt:
        return "true", "false"

    if "lei" in fmt or "lei" in name:
        left = LEI_POOL[stable_index(name, day.day, trade_index, modulo=len(LEI_POOL))]
        right = LEI_POOL[(stable_index(name, day.day, trade_index, modulo=len(LEI_POOL)) + 1) % len(LEI_POOL)]
        if left == right:
            right = LEI_POOL[(LEI_POOL.index(left) + 1) % len(LEI_POOL)]
        return left, right

    if "isin" in fmt or "isin" in name:
        left = ISIN_POOL[stable_index(name, day.day, trade_index, modulo=len(ISIN_POOL))]
        right = ISIN_POOL[(stable_index(name, day.day, trade_index, modulo=len(ISIN_POOL)) + 1) % len(ISIN_POOL)]
        if left == right:
            right = ISIN_POOL[(ISIN_POOL.index(left) + 1) % len(ISIN_POOL)]
        return left, right

    if "currency" in fmt or "iso 4217" in fmt or "currency" in name:
        left = CURRENCY_POOL[stable_index(name, day.day, trade_index, modulo=len(CURRENCY_POOL))]
        right = CURRENCY_POOL[(stable_index(name, day.day, trade_index, modulo=len(CURRENCY_POOL)) + 1) % len(CURRENCY_POOL)]
        if left == right:
            right = CURRENCY_POOL[(CURRENCY_POOL.index(left) + 1) % len(CURRENCY_POOL)]
        return left, right

    if "iso 3166" in fmt or "country" in name or "jurisdiction" in name:
        left = COUNTRY_POOL[stable_index(name, day.day, trade_index, modulo=len(COUNTRY_POOL))]
        right = COUNTRY_POOL[(stable_index(name, day.day, trade_index, modulo=len(COUNTRY_POOL)) + 1) % len(COUNTRY_POOL)]
        if left == right:
            right = COUNTRY_POOL[(COUNTRY_POOL.index(left) + 1) % len(COUNTRY_POOL)]
        return left, right

    if any(token in fmt for token in ["decimal", "amount", "numeric", "integer", "percentage", "rate", "number"]):
        if "rate" in fmt or "percentage" in fmt:
            left = 0.0100 + ((trade_index + number) % 17) / 1000
            right = left + 0.2500
            return f"{left:.4f}", f"{right:.4f}"
        if "integer" in fmt:
            left = 1 + ((trade_index + number) % 20)
            return str(left), str(left + 5)
        left = 1000000 + (day.day * 10000) + (trade_index * 1000) + (table * 100) + number
        right = left - 50000
        return f"{left:.2f}", f"{right:.2f}"

    return (
        f"{TEXT_POOL[stable_index(name, day.day, trade_index, modulo=len(TEXT_POOL))]}_L_{table}_{number}_{day.day:02d}_{trade_index:02d}",
        f"{TEXT_POOL[(stable_index(name, day.day, trade_index, modulo=len(TEXT_POOL)) + 1) % len(TEXT_POOL)]}_R_{table}_{number}_{day.day:02d}_{trade_index:02d}",
    )


def build_trade_row(day: date, trade_index: int, op_count: int, sft_type: str = "Repo", action_type: str = "NEWT") -> tuple[dict, dict]:
    target = target_unmatches(day, trade_index)
    candidates = mismatch_candidates(sft_type, action_type)
    if target > len(candidates):
        raise ValueError(f"Target unmatches {target} exceeds eligible fields {len(candidates)} for {sft_type}/{action_type}")

    mismatch_names = {field["name"] for field in candidates[:target]}
    uti = f"SNDR202603{day.day:02d}{trade_index:03d}"

    row = {
        "uti": uti,
        "sft_type": sft_type,
        "action_type": action_type,
    }

    for col_base, field in FIELD_COLS:
        if field["name"] in mismatch_names:
            cp1, cp2 = mismatch_pair(field, day, trade_index)
        else:
            cp1, cp2 = base_pair(field, day, trade_index)
        row[f"{col_base}_cp1"] = cp1
        row[f"{col_base}_cp2"] = cp2

    meta = {
        "uti": uti,
        "date": day.isoformat(),
        "trade_index": trade_index,
        "target_unmatches": target,
        "operations_in_file": op_count,
        "sft_type": sft_type,
        "action_type": action_type,
    }
    return row, meta


def write_daily_csv(day: date) -> tuple[Path, list[dict]]:
    op_count = day_operation_count(day)
    rows = []
    manifest = []
    for trade_index in range(1, op_count + 1):
        row, meta = build_trade_row(day, trade_index, op_count=op_count)
        rows.append(row)
        manifest.append(meta)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"sftr_reconciliation_{day.isoformat()}.csv"

    header = ["uti", "sft_type", "action_type"]
    for col_base, _field in FIELD_COLS:
        header.append(f"{col_base}_cp1")
        header.append(f"{col_base}_cp2")

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return path, manifest


def generate_all() -> dict:
    files = []
    manifest_by_file: dict[str, list[dict]] = {}
    for day_num in range(1, 32):
        current_day = date(2026, 3, day_num)
        path, manifest = write_daily_csv(current_day)
        files.append(path)
        manifest_by_file[path.name] = manifest
    return {"files": files, "manifest": manifest_by_file}


def audit_all(manifest_by_file: dict[str, list[dict]]) -> dict:
    from app.services.file_parser import parse_tabular_csv
    from app.services.comparison import compare_trade

    audit = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "folder": str(OUT_DIR),
        "files": [],
        "summary": {},
    }

    total_files = 0
    total_rows = 0
    total_expected_unmatches = 0
    total_actual_unmatches = 0
    unique_utis = set()
    per_level_counts = defaultdict(int)

    for filename, manifest_rows in sorted(manifest_by_file.items()):
        path = OUT_DIR / filename
        raw = path.read_bytes()
        parsed_rows = parse_tabular_csv(raw)

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            header = next(reader)
            row_count = sum(1 for _ in reader)

        file_expected = sum(row["target_unmatches"] for row in manifest_rows)
        file_actual = 0
        row_audit = []

        for expected, parsed in zip(manifest_rows, parsed_rows, strict=True):
            comparisons = compare_trade(parsed["emisor"], parsed["receptor"], parsed["sft_type"], parsed["action_type"])
            actual_unmatches = sum(1 for c in comparisons if c["result"] == "UNMATCH")
            file_actual += actual_unmatches
            per_level_counts[expected["target_unmatches"]] += 1
            row_audit.append(
                {
                    "uti": expected["uti"],
                    "target_unmatches": expected["target_unmatches"],
                    "actual_unmatches": actual_unmatches,
                    "ok": actual_unmatches == expected["target_unmatches"],
                }
            )
            unique_utis.add(expected["uti"])

        file_report = {
            "file": filename,
            "date": manifest_rows[0]["date"] if manifest_rows else None,
            "columns": len(header),
            "rows": row_count,
            "expected_rows": len(manifest_rows),
            "expected_unmatches": file_expected,
            "actual_unmatches": file_actual,
            "all_rows_match_targets": all(item["ok"] for item in row_audit),
            "row_checks": row_audit,
        }

        audit["files"].append(file_report)
        total_files += 1
        total_rows += row_count
        total_expected_unmatches += file_expected
        total_actual_unmatches += file_actual

    audit["summary"] = {
        "total_files": total_files,
        "total_rows": total_rows,
        "total_unique_utis": len(unique_utis),
        "total_expected_unmatches": total_expected_unmatches,
        "total_actual_unmatches": total_actual_unmatches,
        "all_files_ok": all(file["all_rows_match_targets"] for file in audit["files"]),
        "all_files_have_313_columns": all(file["columns"] == 313 for file in audit["files"]),
        "mismatch_level_distribution": dict(sorted(per_level_counts.items())),
    }

    with AUDIT_PATH.open("w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)

    return audit


def main() -> None:
    generated = generate_all()
    audit = audit_all(generated["manifest"])
    print(f"Generated {audit['summary']['total_files']} CSV files in {OUT_DIR}")
    print(f"Total rows: {audit['summary']['total_rows']}")
    print(f"Total expected unmatches: {audit['summary']['total_expected_unmatches']}")
    print(f"Total actual unmatches: {audit['summary']['total_actual_unmatches']}")
    print(f"All files OK: {audit['summary']['all_files_ok']}")
    print(f"Audit report: {AUDIT_PATH}")


if __name__ == "__main__":
    main()
