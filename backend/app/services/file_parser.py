import pandas as pd
from io import BytesIO


def parse_csv(content: bytes) -> dict[str, str]:
    df = pd.read_csv(BytesIO(content), sep=";", header=None, names=["field_name", "value"], dtype=str)
    df = df.dropna(subset=["field_name"])
    df["field_name"] = df["field_name"].str.strip()
    df["value"] = df["value"].fillna("").astype(str).str.strip()
    return dict(zip(df["field_name"], df["value"]))


def parse_xml(content: bytes) -> dict[str, str]:
    from lxml import etree
    root = etree.fromstring(content)
    data: dict[str, str] = {}
    for elem in root.iter():
        if elem.text and elem.text.strip():
            tag = etree.QName(elem.tag).localname if "}" in elem.tag else elem.tag
            data[tag] = elem.text.strip()
    return data


def parse_file(filename: str, content: bytes) -> dict[str, str]:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return parse_csv(content)
    elif lower.endswith(".xml"):
        return parse_xml(content)
    else:
        raise ValueError(f"Unsupported file format: {filename}. Use CSV or XML.")
