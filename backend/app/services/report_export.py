import re
import textwrap
from html import escape

EMOJI_REPLACEMENTS = {
    "📈": "[Tendencia]",
    "📉": "[Descenso]",
    "⚠️": "[Riesgo]",
    "⚠": "[Riesgo]",
    "✅": "[OK]",
    "❌": "[Error]",
    "🔎": "[Analisis]",
    "💡": "[Insight]",
    "📌": "[Clave]",
    "🟠": "[Advertencia]",
    "🔴": "[Critico]",
    "🟢": "[Correcto]",
    "📊": "[Analitica]",
    "✨": "[IA]",
}


def _normalize_markdown_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if re.fullmatch(r"[*_\-]{3,}", stripped):
        return ""
    stripped = re.sub(r"^#{1,6}\s*", "", stripped)
    stripped = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
    stripped = re.sub(r"\*(.*?)\*", r"\1", stripped)
    for emoji, replacement in EMOJI_REPLACEMENTS.items():
        stripped = stripped.replace(emoji, replacement)
    return stripped


def _classify_line(raw_line: str) -> tuple[str, str]:
    stripped = raw_line.strip()
    normalized = _normalize_markdown_line(raw_line)
    if not normalized:
        return ("blank", "")
    if stripped.startswith("# "):
        return ("heading_1", normalized)
    if stripped.startswith("## "):
        return ("heading_2", normalized)
    if stripped.startswith("- "):
        return ("bullet", normalized)
    if re.match(r"^\*\*.+:\*\*", stripped):
        return ("label", normalized)
    return ("body", normalized)


def _wrap_styled_lines(text: str, width: int = 92) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line_type, content = _classify_line(raw_line)
        if line_type == "blank":
            lines.append(("blank", ""))
            continue
        wrap_width = 88 if line_type == "bullet" else width
        wrapped = textwrap.wrap(content, width=wrap_width, replace_whitespace=False) or [""]
        if line_type == "bullet":
            first, *rest = wrapped
            lines.append(("bullet", first))
            for extra in rest:
                lines.append(("bullet_cont", extra))
        else:
            lines.extend((line_type, item) for item in wrapped)
    return lines


def generate_pdf_report(title: str, subtitle: str, body: str) -> bytes:
    lines: list[tuple[str, str]] = [
        ("title", _normalize_markdown_line(title)),
        ("blank", ""),
        ("subtitle", _normalize_markdown_line(subtitle)),
        ("blank", ""),
    ] + _wrap_styled_lines(body, width=92)

    page_width = 595
    page_height = 842
    left_margin = 50
    top_margin = 60
    default_line_height = 16
    bottom_margin = 50
    style_map = {
        "title": {"font": "F2", "size": 18, "leading": 24, "indent": 0},
        "subtitle": {"font": "F1", "size": 10, "leading": 16, "indent": 0},
        "heading_1": {"font": "F2", "size": 15, "leading": 22, "indent": 0},
        "heading_2": {"font": "F2", "size": 13, "leading": 20, "indent": 0},
        "label": {"font": "F2", "size": 11, "leading": 16, "indent": 0},
        "body": {"font": "F1", "size": 11, "leading": default_line_height, "indent": 0},
        "bullet": {"font": "F1", "size": 11, "leading": default_line_height, "indent": 14},
        "bullet_cont": {"font": "F1", "size": 11, "leading": default_line_height, "indent": 28},
        "blank": {"font": "F1", "size": 11, "leading": 10, "indent": 0},
    }

    pages: list[list[tuple[str, str]]] = [[]]
    current_height = top_margin
    for entry in lines:
        style = style_map[entry[0]]
        if current_height + style["leading"] > page_height - bottom_margin and pages[-1]:
            pages.append([])
            current_height = top_margin
        pages[-1].append(entry)
        current_height += style["leading"]

    objects: list[bytes] = []

    def add_object(payload: bytes) -> int:
        objects.append(payload)
        return len(objects)

    font_obj = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    bold_font_obj = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    page_obj_ids: list[int] = []
    content_obj_ids: list[int] = []

    for page_lines in pages:
        content_lines = ["BT"]
        current_y = page_height - top_margin
        for line_type, line in page_lines:
            style = style_map[line_type]
            escaped = (
                line.replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            encoded = escaped.encode("cp1252", errors="replace").decode("cp1252")
            draw_text = f"- {encoded}" if line_type == "bullet" else encoded
            content_lines.append(f"/{style['font']} {style['size']} Tf")
            content_lines.append(f"1 0 0 1 {left_margin + style['indent']} {current_y} Tm")
            if line_type == "subtitle":
                content_lines.append("0.42 0.45 0.5 rg")
            elif line_type in {"heading_1", "heading_2"}:
                content_lines.append("0.99 0.49 0.2 rg")
            else:
                content_lines.append("0.14 0.2 0.27 rg")
            if draw_text:
                content_lines.append(f"({draw_text}) Tj")
            current_y -= style["leading"]
        content_lines.append("ET")
        content_stream = "\n".join(content_lines).encode("cp1252", errors="replace")
        content_obj_ids.append(add_object(f"<< /Length {len(content_stream)} >>\nstream\n".encode("cp1252") + content_stream + b"\nendstream"))
        page_obj_ids.append(0)

    pages_placeholder_id = add_object(b"")

    for idx, content_id in enumerate(content_obj_ids):
        page_payload = (
            f"<< /Type /Page /Parent {pages_placeholder_id} 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 {font_obj} 0 R /F2 {bold_font_obj} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("cp1252")
        page_obj_ids[idx] = add_object(page_payload)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_obj_ids)
    objects[pages_placeholder_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_ids)} >>".encode("cp1252")

    catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_placeholder_id} 0 R >>".encode("cp1252"))

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, payload in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("cp1252"))
        pdf.extend(payload)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("cp1252"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("cp1252"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("cp1252")
    )
    return bytes(pdf)


def generate_word_report_html(title: str, subtitle: str, body: str) -> bytes:
    blocks = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            blocks.append("</ul>")
            in_list = False

    for raw_line in body.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            close_list()
            continue
        if stripped.startswith("- "):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{escape(_normalize_markdown_line(stripped[2:]))}</li>")
        elif stripped.startswith("## "):
            close_list()
            blocks.append(f"<h2>{escape(_normalize_markdown_line(stripped[3:]))}</h2>")
        elif stripped.startswith("# "):
            close_list()
            blocks.append(f"<h1>{escape(_normalize_markdown_line(stripped[2:]))}</h1>")
        else:
            close_list()
            blocks.append(f"<p>{escape(_normalize_markdown_line(stripped))}</p>")
    close_list()

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #243444; margin: 32px; line-height: 1.5; }}
    h1 {{ color: #243444; font-size: 24px; margin-bottom: 8px; }}
    h2 {{ color: #fc7c34; font-size: 18px; margin-top: 24px; margin-bottom: 8px; }}
    .subtitle {{ color: #6b7280; font-size: 12px; margin-bottom: 24px; }}
    p, li {{ font-size: 12px; }}
    ul {{ margin-top: 8px; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <div class="subtitle">{escape(subtitle)}</div>
  {''.join(blocks)}
</body>
</html>"""
    return html.encode("utf-8")
