"""
Generator for sftr_reconciliation_demo.csv
Produces trades with controlled numbers of UNMATCH fields.
"""

import json
import re
import os
import csv

# Load field registry
FIELDS_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "data", "sftr_fields.json")
with open(FIELDS_PATH) as f:
    FIELDS = json.load(f)


def normalize_col(name: str) -> str:
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


# Pre-compute column base names
FIELD_COLS = [(normalize_col(f["name"]), f) for f in FIELDS]

# ── Mismatch value pairs per field format ─────────────────────────────────────
# These pairs guarantee UNMATCH (result != MATCH, MIRROR, or NA)

def get_mismatch_pair(field: dict) -> tuple[str, str]:
    """Return (cp1_val, cp2_val) that will produce an UNMATCH."""
    fmt = field.get("format", "").lower()
    name_lower = field["name"].lower()
    is_mirror = field.get("is_mirror", False)

    # Date/timestamp fields
    if "date" in fmt or "timestamp" in fmt or "date-time" in fmt:
        return ("2024-07-25T08:00:00Z", "2024-07-26T09:30:00Z")

    # Numeric fields
    if "decimal" in fmt or "number" in fmt or "numeric" in fmt or "amount" in fmt or "percentage" in fmt or "rate" in fmt:
        return ("5000000.00", "4950000.00")  # diff = 50000, > any tolerance

    # Mirror fields (GIVE/TAKE) — use GIVE/GIVE so it's a VALUE_MISMATCH not MIRROR
    if is_mirror:
        return ("GIVE", "GIVE_X")

    # LEI fields
    if "lei" in fmt.lower() or "lei" in name_lower:
        return ("7LTWFZYICNSX8D621K86", "VUJNWIVNFNEBFQSQE965")

    # ISIN fields
    if "isin" in fmt.lower() or "isin" in name_lower:
        return ("DE0001135275", "FR0013451524")

    # Boolean fields
    if "true/false" in fmt or "boolean" in fmt:
        return ("true", "false")

    # Default: two clearly different string values
    return ("VALOR_CP1", "VALOR_CP2")


def get_base_pair(field: dict) -> tuple[str, str]:
    """Return matching (cp1_val, cp2_val) for a field — both the same."""
    fmt = field.get("format", "").lower()
    name_lower = field["name"].lower()
    is_mirror = field.get("is_mirror", False)

    if "date" in fmt or "timestamp" in fmt or "date-time" in fmt:
        return ("2024-07-25T08:00:00Z", "2024-07-25T08:00:00Z")
    if "decimal" in fmt or "number" in fmt or "numeric" in fmt or "amount" in fmt:
        return ("5000000.00", "5000000.00")
    if "rate" in fmt or "percentage" in fmt:
        return ("0.0350", "0.0350")
    if is_mirror:
        return ("GIVE", "TAKE")  # MIRROR_MATCH — result=MIRROR, not UNMATCH
    if "lei" in fmt.lower() or "lei" in name_lower:
        return ("7LTWFZYICNSX8D621K86", "7LTWFZYICNSX8D621K86")
    if "isin" in fmt.lower() or "isin" in name_lower:
        return ("DE0001135275", "DE0001135275")
    if "true/false" in fmt or "boolean" in fmt:
        return ("true", "true")
    return ("", "")  # both empty → NA


# ── Trade configurations ───────────────────────────────────────────────────────
# (uti_suffix, target_unmatches, sft_type, action_type)
TRADE_CONFIGS = [
    ("0001", 0,  "Repo", "NEWT"),   # Clean
    ("0002", 0,  "Repo", "NEWT"),   # Clean
    ("0003", 0,  "Repo", "NEWT"),   # Clean
    ("0004", 1,  "Repo", "NEWT"),
    ("0005", 2,  "Repo", "NEWT"),
    ("0006", 3,  "Repo", "NEWT"),
    ("0007", 5,  "Repo", "NEWT"),
    ("0008", 7,  "Repo", "NEWT"),
    ("0009", 10, "Repo", "NEWT"),
    ("0010", 12, "Repo", "NEWT"),
    ("0011", 15, "Repo", "NEWT"),
    ("0012", 18, "Repo", "NEWT"),
    ("0013", 20, "Repo", "NEWT"),
    ("0014", 25, "Repo", "NEWT"),
    ("0015", 30, "Repo", "NEWT"),
    ("0016", 35, "Repo", "NEWT"),
    ("0017", 40, "Repo", "NEWT"),
    ("0018", 45, "Repo", "NEWT"),
    ("0019", 50, "Repo", "NEWT"),
    ("0020", 55, "Repo", "NEWT"),
    ("0021", 60, "Repo", "NEWT"),
]

# Only use non-mirror fields that have obligation M or C for Repo/NEWT as primary mismatch candidates
# (to ensure they actually count as UNMATCH and not NA)
def get_obligation_repo_newt(field: dict) -> str:
    return field.get("obligation", {}).get("Repo", {}).get("NEWT", "-")

# Build ordered list of fields suitable for controlled mismatches
# Priority: M fields first, then C, then O, skip "-"
def build_mismatch_candidates() -> list[dict]:
    candidates = []
    for field in FIELDS:
        obl = get_obligation_repo_newt(field)
        if obl == "-":
            continue
        candidates.append(field)
    # Sort: M first, then C, then O
    order = {"M": 0, "C": 1, "O": 2}
    candidates.sort(key=lambda f: order.get(get_obligation_repo_newt(f), 3))
    return candidates

MISMATCH_CANDIDATES = build_mismatch_candidates()

print(f"Total mismatch-capable fields: {len(MISMATCH_CANDIDATES)}")


def build_row(uti_suffix: str, target_unmatches: int, sft_type: str, action_type: str) -> dict:
    """Build a CSV row dict."""
    uti = f"SNDR2024{uti_suffix}"
    row = {
        "uti": uti,
        "sft_type": sft_type,
        "action_type": action_type,
    }

    # Which fields to mismatch
    mismatch_set = set()
    if target_unmatches > 0:
        chosen = MISMATCH_CANDIDATES[:target_unmatches]
        mismatch_set = {f["name"] for f in chosen}

    # Populate all SFTR fields
    for col_base, field in FIELD_COLS:
        field_name = field["name"]
        obl = get_obligation_repo_newt(field)

        if field_name in mismatch_set:
            cp1, cp2 = get_mismatch_pair(field)
        else:
            cp1, cp2 = get_base_pair(field)

        row[f"{col_base}_cp1"] = cp1
        row[f"{col_base}_cp2"] = cp2

    return row


# ── Generate all rows ──────────────────────────────────────────────────────────
rows = []
for suffix, target, sft, action in TRADE_CONFIGS:
    rows.append(build_row(suffix, target, sft, action))

# ── Write CSV ──────────────────────────────────────────────────────────────────
OUT_PATH = os.path.join(os.path.dirname(__file__), "sftr_reconciliation_demo.csv")

# Build header: metadata + all field columns
header = ["uti", "sft_type", "action_type"]
for col_base, _ in FIELD_COLS:
    header.append(f"{col_base}_cp1")
    header.append(f"{col_base}_cp2")

with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=header, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

print(f"Written {len(rows)} trades to {OUT_PATH}")
print(f"Header columns: {len(header)}")
