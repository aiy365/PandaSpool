from __future__ import annotations

import hashlib
import math
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from .errors import InputError
from .material_domain import classify_color_family


_SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_KNOWN_BRANDS = (
    "Polymaker",
    "彩多屋",
    "大简",
    "天威",
    "三绿",
    "拓竹",
    "必趣",
    "Poly",
)
_MATERIALS = ("PETG", "PCTG", "PLA", "ABS", "ASA", "TPU", "PA", "PC", "PP", "PVA", "HIPS", "PET")
_BRAND_ALIASES = {"Poly": "Polymaker"}


def _column_index(cell_reference: str) -> int:
    letters = re.match(r"[A-Z]+", cell_reference.upper())
    if not letters:
        raise InputError(f"无法解析工作簿单元格：{cell_reference}。")
    value = 0
    for character in letters.group(0):
        value = value * 26 + ord(character) - 64
    return value - 1


def _first_sheet_path(archive: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    first = workbook.find(f"{{{_SPREADSHEET_NS}}}sheets/{{{_SPREADSHEET_NS}}}sheet")
    if first is None:
        raise InputError("工作簿没有工作表。")
    relationship_id = first.attrib.get(f"{{{_OFFICE_REL_NS}}}id")
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relation in relationships.findall(f"{{{_PACKAGE_REL_NS}}}Relationship"):
        if relation.attrib.get("Id") == relationship_id:
            target = relation.attrib.get("Target", "").lstrip("/")
            return target if target.startswith("xl/") else f"xl/{target}"
    raise InputError("无法定位工作簿的第一张工作表。")


def read_first_sheet(path: str | Path) -> list[list[Any]]:
    workbook_path = Path(path).expanduser().resolve()
    if not workbook_path.is_file() or workbook_path.suffix.lower() != ".xlsx":
        raise InputError("库存导入目前只支持有效的.xlsx工作簿。")
    try:
        with zipfile.ZipFile(workbook_path) as archive:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                for item in root.findall(f"{{{_SPREADSHEET_NS}}}si"):
                    shared.append(
                        "".join(
                            node.text or ""
                            for node in item.iter(f"{{{_SPREADSHEET_NS}}}t")
                        )
                    )
            sheet = ET.fromstring(archive.read(_first_sheet_path(archive)))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise InputError("库存工作簿损坏或不是标准Excel工作簿。") from exc

    rows: list[list[Any]] = []
    for row in sheet.findall(f".//{{{_SPREADSHEET_NS}}}row"):
        values: dict[int, Any] = {}
        for cell in row.findall(f"{{{_SPREADSHEET_NS}}}c"):
            index = _column_index(cell.attrib.get("r", ""))
            cell_type = cell.attrib.get("t")
            value_node = cell.find(f"{{{_SPREADSHEET_NS}}}v")
            if cell_type == "inlineStr":
                inline = cell.find(f"{{{_SPREADSHEET_NS}}}is")
                value = "".join(
                    node.text or ""
                    for node in inline.iter(f"{{{_SPREADSHEET_NS}}}t")
                ) if inline is not None else ""
            elif value_node is None:
                value = None
            elif cell_type == "s":
                value = shared[int(value_node.text or 0)]
            elif cell_type in {"str", "e"}:
                value = value_node.text or ""
            elif cell_type == "b":
                value = value_node.text == "1"
            else:
                raw = value_node.text or ""
                number = float(raw)
                value = int(number) if number.is_integer() else number
            values[index] = value
        if values:
            width = max(values) + 1
            rows.append([values.get(index) for index in range(width)])
    return rows


def _product_identity(label: str) -> tuple[str, str, str]:
    cleaned = re.sub(r"\s+", " ", label).strip()
    matched_brand = next((item for item in _KNOWN_BRANDS if cleaned.casefold().startswith(item.casefold())), None)
    if not matched_brand:
        parts = cleaned.split(" ", 1)
        matched_brand = parts[0]
    product_line = cleaned[len(matched_brand):].strip() or cleaned
    brand = _BRAND_ALIASES.get(matched_brand, matched_brand)
    material = next(
        (item for item in _MATERIALS if re.search(rf"(?<![A-Za-z]){re.escape(item)}(?![A-Za-z+])", cleaned, re.IGNORECASE)),
        None,
    )
    if material is None and "PLA+" in cleaned.upper():
        material = "PLA"
    if material is None:
        raise InputError(f"无法从产品列识别材料类型：{label}。")
    return brand, product_line, material


def _stock_parts(value: Any) -> tuple[int, int]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"库存值必须是数字：{value!r}。")
    numeric = float(value)
    if numeric <= 0 or numeric > 10000:
        raise InputError(f"库存值超出允许范围：{numeric}。")
    sealed = math.floor(numeric + 1e-8)
    opened = round((numeric - sealed) * 100)
    if opened == 100:
        sealed += 1
        opened = 0
    return sealed, opened


def inventory_rows_from_matrix(matrix: list[list[Any]]) -> list[dict[str, Any]]:
    if len(matrix) < 3:
        raise InputError("库存工作簿至少需要产品表头、颜色和一行库存。")
    headers = matrix[1]
    records: list[dict[str, Any]] = []
    for row in matrix[2:]:
        color = str(row[1] or "").strip() if len(row) > 1 else ""
        if not color:
            continue
        for column in range(2, min(len(headers), len(row))):
            value = row[column]
            if value in {None, ""}:
                continue
            label = str(headers[column] or "").strip()
            if not label:
                continue
            brand, product_line, material = _product_identity(label)
            sealed, opened = _stock_parts(value)
            identity = hashlib.sha256(f"{label}\0{color}".encode("utf-8")).hexdigest()[:16].upper()
            records.append(
                {
                    "brand": brand,
                    "product_line": product_line,
                    "material_type": material,
                    "color": color,
                    "color_family": classify_color_family(color),
                    "sku": f"PP-XLSX-{identity}",
                    "region": "CN",
                    "stock_spools": sealed,
                    "opened_remaining_percent": opened,
                    "spool_weight_g": 1000,
                }
            )
    if not records:
        raise InputError("库存工作簿中没有非空库存格。")
    return records


def load_inventory_workbook(path: str | Path) -> list[dict[str, Any]]:
    return inventory_rows_from_matrix(read_first_sheet(path))
