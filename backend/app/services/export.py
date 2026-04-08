from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from io import BytesIO
from datetime import datetime


SEVERITY_FILLS = {
    "CRITICAL": PatternFill(start_color="FCEBEB", end_color="FCEBEB", fill_type="solid"),
    "WARNING": PatternFill(start_color="FAEEDA", end_color="FAEEDA", fill_type="solid"),
    "INFO": PatternFill(start_color="E6F1FB", end_color="E6F1FB", fill_type="solid"),
    "NONE": PatternFill(start_color="EAF3DE", end_color="EAF3DE", fill_type="solid"),
}

SEVERITY_FONTS = {
    "CRITICAL": Font(color="A32D2D", bold=True),
    "WARNING": Font(color="854F0B", bold=True),
    "INFO": Font(color="185FA5"),
    "NONE": Font(color="3B6D11"),
}

HEADER_FILL = PatternFill(start_color="2B3544", end_color="2B3544", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
THIN_BORDER = Border(
    left=Side(style="thin", color="D0D0D0"),
    right=Side(style="thin", color="D0D0D0"),
    top=Side(style="thin", color="D0D0D0"),
    bottom=Side(style="thin", color="D0D0D0"),
)


def generate_xlsx(session_data: dict, field_results: list, only_unmatches: bool = False) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "SFTR Comparison"

    # Title row
    ws.merge_cells("A1:J1")
    title_cell = ws["A1"]
    title_cell.value = f"SFTR Unmatch Report - UTI: {session_data.get('uti', 'N/A')}"
    title_cell.font = Font(bold=True, size=14, color="2B3544")
    title_cell.alignment = Alignment(horizontal="left")

    # Metadata
    ws["A2"] = "Session Date:"
    ws["B2"] = session_data.get("created_at", "")
    ws["A3"] = "SFT Type:"
    ws["B3"] = session_data.get("sft_type", "")
    ws["C3"] = "Action Type:"
    ws["D3"] = session_data.get("action_type", "")
    ws["A4"] = "Emisor:"
    ws["B4"] = f"{session_data.get('emisor_name', '')} ({session_data.get('emisor_lei', '')})"
    ws["A5"] = "Receptor:"
    ws["B5"] = f"{session_data.get('receptor_name', '')} ({session_data.get('receptor_lei', '')})"

    for r in range(2, 6):
        ws.cell(row=r, column=1).font = Font(bold=True, size=10)

    # Headers
    headers = [
        "Table", "Field #", "Field Name", "Obligation",
        "Emisor Value", "Receptor Value", "Result",
        "Severity", "Status", "Assignee", "Notes", "Validated"
    ]
    header_row = 7
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER

    # Data rows
    row = header_row + 1
    for fr in field_results:
        if only_unmatches and fr.get("result") != "UNMATCH":
            continue

        severity = fr.get("severity", "NONE")
        fill = SEVERITY_FILLS.get(severity, SEVERITY_FILLS["NONE"])
        font = SEVERITY_FONTS.get(severity, SEVERITY_FONTS["NONE"])

        values = [
            fr.get("table_number"),
            fr.get("field_number"),
            fr.get("field_name"),
            fr.get("obligation"),
            fr.get("emisor_value", ""),
            fr.get("receptor_value", ""),
            fr.get("result"),
            severity,
            fr.get("status", ""),
            fr.get("assignee", ""),
            fr.get("notes", ""),
            "Yes" if fr.get("validated") else "No",
        ]

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = THIN_BORDER
            if col in (7, 8):  # Result and Severity columns
                cell.fill = fill
                cell.font = font
            cell.alignment = Alignment(horizontal="center" if col <= 4 else "left")

        row += 1

    # Summary row
    row += 1
    ws.cell(row=row, column=1, value="Summary").font = Font(bold=True, size=11)
    ws.cell(row=row + 1, column=1, value="Total Fields:")
    ws.cell(row=row + 1, column=2, value=session_data.get("total_fields", 0))
    ws.cell(row=row + 2, column=1, value="Total Unmatches:")
    ws.cell(row=row + 2, column=2, value=session_data.get("total_unmatches", 0))
    ws.cell(row=row + 3, column=1, value="Critical:")
    ws.cell(row=row + 3, column=2, value=session_data.get("critical_count", 0))

    # Column widths
    widths = [8, 8, 40, 10, 30, 30, 10, 10, 15, 15, 30, 10]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w

    output = BytesIO()
    wb.save(output)
    return output.getvalue()
