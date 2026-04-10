"""
Generate deterministic synthetic predatadas reconciliation CSVs.

Output example:
  backend/sample_data/predatadas_april_2026/
    - predatadas_reconciliation_2026-04-01.csv
    - ...
    - audit_summary.json
"""

from __future__ import annotations

import calendar
import csv
import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

FIELDS_PATH = ROOT.parent / "app" / "data" / "predatadas_fields.json"

with FIELDS_PATH.open(encoding="utf-8") as f:
    FIELDS = json.load(f)

from app.services.column_mapping import normalize_col
from app.services.comparison import compare_trade


OPS_PATTERN = [18, 24, 30]
MISMATCH_LEVELS = [1, 2, 3, 4]
PAIRING_FIELDS = {"UTI", "Other counterparty"}
COUNTERPARTIES = [
    "5493001KJTIIGC8Y1R12",
    "7LTWFZYICNSX8D621K86",
    "VUJNWIVNFNEBFQSQE965",
    "R0MUWSFPU8MPRO8K5P81",
]
COLLATERAL_METHODS = [
    "TRIPARTY",
    "BILATERAL",
    "CSD",
    "THIRD_PARTY_AGENT",
]
SFT_TYPES = ["REPO", "SECLEND", "BUYSELLBACK"]


def stable_index(*parts: object, modulo: int) -> int:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:12], 16) % modulo


def output_dir_for(year: int, month: int) -> Path:
    month_name = calendar.month_name[month].lower()
    return ROOT / f"predatadas_{month_name}_{year}"


def day_profile(day: date) -> str:
    if day.day in {4, 9, 14, 19, 24, 29}:
        return "clean"
    if day.day in {2, 5, 8, 11, 15, 18, 21, 23, 26, 28, 30}:
        return "mixed"
    return "problematic"


def operation_count(day: date) -> int:
    return OPS_PATTERN[(day.day - 1) % len(OPS_PATTERN)]


def target_mismatches(day: date, trade_index: int) -> int:
    profile = day_profile(day)
    if profile == "clean":
        return 0
    if profile == "mixed" and trade_index % 2 == 0:
        return 0
    return MISMATCH_LEVELS[(day.day + trade_index) % len(MISMATCH_LEVELS)]


def issue_mode(day: date, trade_index: int, mismatch_count: int) -> str:
    if mismatch_count == 0:
        return "clean"
    bucket = stable_index("predatadas_mode", day.isoformat(), trade_index, modulo=16)
    if bucket < 7:
        return "unmatch"
    if bucket < 11:
        return "unpair_uti"
    if bucket < 14:
        return "unpair_other"
    return "unpair_both"


def base_timestamp(day: date, trade_index: int, offset_seconds: int = 0) -> str:
    hour = 8 + (trade_index % 9)
    minute = (trade_index * 7) % 60
    second = (trade_index * 11 + offset_seconds) % 60
    dt = datetime(day.year, day.month, day.day, hour, minute, second) + timedelta(seconds=offset_seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def trade_base_values(day: date, trade_index: int) -> dict[str, str]:
    uti = f"PRED-{day.strftime('%Y%m%d')}-{trade_index + 1:04d}"
    counterparty = COUNTERPARTIES[stable_index("cp", day.isoformat(), trade_index, modulo=len(COUNTERPARTIES))]
    sft_type = SFT_TYPES[stable_index("sft", day.isoformat(), trade_index, modulo=len(SFT_TYPES))]
    reporting_ts = base_timestamp(day, trade_index)
    execution_ts = base_timestamp(day, trade_index, offset_seconds=45)
    return {
        "Reporting timestamp": reporting_ts,
        "Other counterparty": counterparty,
        "UTI": uti,
        "Event date": day.isoformat(),
        "Type of SFT": sft_type,
        "Execution timestamp": execution_ts,
        "Method used to provide collateral": COLLATERAL_METHODS[
            stable_index("collateral", day.isoformat(), trade_index, modulo=len(COLLATERAL_METHODS))
        ],
    }


def apply_unmatch_mutation(field_name: str, values: dict[str, str], day: date, trade_index: int) -> str:
    left = values[field_name]
    if field_name == "Reporting timestamp":
        return base_timestamp(day, trade_index, offset_seconds=300)
    if field_name == "Event date":
        return (day + timedelta(days=1)).isoformat()
    if field_name == "Execution timestamp":
        return base_timestamp(day, trade_index, offset_seconds=7200)
    if field_name == "Type of SFT":
        current_idx = SFT_TYPES.index(left)
        return SFT_TYPES[(current_idx + 1) % len(SFT_TYPES)]
    if field_name == "Method used to provide collateral":
        current_idx = COLLATERAL_METHODS.index(left)
        return COLLATERAL_METHODS[(current_idx + 1) % len(COLLATERAL_METHODS)]
    if field_name == "Other counterparty":
        current_idx = COUNTERPARTIES.index(left)
        return COUNTERPARTIES[(current_idx + 1) % len(COUNTERPARTIES)]
    if field_name == "UTI":
        return f"{left}-X"
    return left


def build_trade(day: date, trade_index: int) -> tuple[dict[str, str], dict[str, str], dict]:
    left = trade_base_values(day, trade_index)
    right = dict(left)

    mismatch_count = target_mismatches(day, trade_index)
    mode = issue_mode(day, trade_index, mismatch_count)

    if mode in {"unpair_uti", "unpair_both"}:
        right["UTI"] = apply_unmatch_mutation("UTI", left, day, trade_index)
    if mode in {"unpair_other", "unpair_both"}:
        right["Other counterparty"] = apply_unmatch_mutation("Other counterparty", left, day, trade_index)

    if mode == "unmatch":
        non_pair_fields = [field["name"] for field in FIELDS if field["name"] not in PAIRING_FIELDS]
        offset = stable_index("predatadas_offset", day.isoformat(), trade_index, modulo=len(non_pair_fields))
        rotated = non_pair_fields[offset:] + non_pair_fields[:offset]
        for field_name in rotated[:mismatch_count]:
            right[field_name] = apply_unmatch_mutation(field_name, left, day, trade_index)

    actual = compare_trade(left, right, sft_type="Predatadas", action_type="NEWT", product_type="predatadas")
    actual_unmatches = sum(1 for item in actual if item["result"] == "UNMATCH")

    manifest = {
        "day": day.isoformat(),
        "trade_index": trade_index,
        "uti": left["UTI"],
        "issue_mode": mode,
        "expected_unmatches": actual_unmatches,
    }
    return left, right, manifest


def write_daily_csv(day: date, out_dir: Path) -> list[dict]:
    field_bases = [normalize_col(field["name"]) for field in FIELDS]
    headers = ["uti", "sft_type", "action_type"]
    for base in field_bases:
        headers.append(f"{base}_cp1")
        headers.append(f"{base}_cp2")

    manifest_rows: list[dict] = []
    path = out_dir / f"predatadas_reconciliation_{day.isoformat()}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter=";")
        writer.writeheader()
        for trade_index in range(operation_count(day)):
            left, right, manifest = build_trade(day, trade_index)
            row = {
                "uti": left["UTI"],
                "sft_type": "Predatadas",
                "action_type": "NEWT",
            }
            for field in FIELDS:
                base = normalize_col(field["name"])
                row[f"{base}_cp1"] = left[field["name"]]
                row[f"{base}_cp2"] = right[field["name"]]
            writer.writerow(row)
            manifest_rows.append(manifest)
    return manifest_rows


def audit_all(manifest_by_file: dict[str, list[dict]], out_dir: Path) -> dict:
    total_rows = 0
    total_expected = 0
    total_actual = 0
    all_ok = True
    issue_mode_distribution: dict[str, int] = {}

    for filename, rows in sorted(manifest_by_file.items()):
        path = out_dir / filename
        content = path.read_bytes()
        import pandas as pd

        df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
        total_rows += len(df)

        for manifest_row, (_idx, row) in zip(rows, df.iterrows()):
            left = {field["name"]: row[f"{normalize_col(field['name'])}_cp1"] for field in FIELDS}
            right = {field["name"]: row[f"{normalize_col(field['name'])}_cp2"] for field in FIELDS}
            actual = compare_trade(left, right, sft_type="Predatadas", action_type="NEWT", product_type="predatadas")
            actual_unmatches = sum(1 for item in actual if item["result"] == "UNMATCH")
            total_expected += manifest_row["expected_unmatches"]
            total_actual += actual_unmatches
            issue_mode_distribution[manifest_row["issue_mode"]] = issue_mode_distribution.get(manifest_row["issue_mode"], 0) + 1
            if actual_unmatches != manifest_row["expected_unmatches"]:
                all_ok = False

    summary = {
        "files": len(manifest_by_file),
        "total_rows": total_rows,
        "total_expected_unmatches": total_expected,
        "total_actual_unmatches": total_actual,
        "all_files_ok": all_ok,
        "issue_mode_distribution": issue_mode_distribution,
    }
    (out_dir / "audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def generate_all(year: int = 2026, month: int = 4, day_start: int = 1, day_end: int | None = None) -> dict:
    last_day = calendar.monthrange(year, month)[1]
    day_end = day_end or last_day
    out_dir = output_dir_for(year, month)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_by_file: dict[str, list[dict]] = {}
    for day_num in range(day_start, day_end + 1):
        current_day = date(year, month, day_num)
        manifest_by_file[f"predatadas_reconciliation_{current_day.isoformat()}.csv"] = write_daily_csv(current_day, out_dir)

    summary = audit_all(manifest_by_file, out_dir)
    print(f"Generated {len(manifest_by_file)} CSV files in {out_dir}")
    print(f"Total rows: {summary['total_rows']}")
    print(f"Total expected unmatches: {summary['total_expected_unmatches']}")
    print(f"Total actual unmatches: {summary['total_actual_unmatches']}")
    print(f"All files OK: {summary['all_files_ok']}")
    print(f"Audit report: {out_dir / 'audit_summary.json'}")
    return summary


if __name__ == "__main__":
    if len(sys.argv) == 1:
        generate_all()
    elif len(sys.argv) == 3:
        generate_all(year=int(sys.argv[1]), month=int(sys.argv[2]))
    elif len(sys.argv) == 5:
        generate_all(year=int(sys.argv[1]), month=int(sys.argv[2]), day_start=int(sys.argv[3]), day_end=int(sys.argv[4]))
    else:
        raise SystemExit("Usage: python sample_data/generate_predatadas_csvs.py [year month [day_start day_end]]")
