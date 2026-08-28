from __future__ import annotations

import zipfile
from pathlib import Path

from printpilot_material_lab.inventory_import import (
    inventory_rows_from_matrix,
    load_inventory_workbook,
)
from printpilot_material_lab.material_domain import classify_color_family


def test_inventory_matrix_turns_decimals_into_opened_spool() -> None:
    records = inventory_rows_from_matrix(
        [
            ["合计： 2.8", None, "2.8盘-20元"],
            [None, None, "大简 PETG 哑光"],
            [2.8, "红色", 2.8],
        ]
    )
    assert records == [
        {
            "brand": "大简",
            "product_line": "PETG 哑光",
            "material_type": "PETG",
            "color": "红色",
            "color_family": "红粉色系",
            "sku": records[0]["sku"],
            "region": "CN",
            "stock_spools": 2,
            "opened_remaining_percent": 80,
            "spool_weight_g": 1000,
        }
    ]
    assert records[0]["sku"].startswith("PP-XLSX-")


def test_color_family_preserves_supplier_name_semantics() -> None:
    assert classify_color_family("珍珠白") == "白色系"
    assert classify_color_family("电光蓝") == "蓝色系"
    assert classify_color_family("透明绿") == "绿色系"
    assert classify_color_family("牛油果色") == "绿色系"
    assert classify_color_family("拿铁色") == "棕米色系"
    assert classify_color_family("肤色") == "棕米色系"
    assert classify_color_family("银色") == "金属色系"
    assert classify_color_family("透明色") == "透明/自然色系"


def test_workbook_brand_alias_is_normalized_without_changing_product_line() -> None:
    record = inventory_rows_from_matrix(
        [[None], [None, None, "Poly PLA 哑光"], [None, "棉花白", 1]]
    )[0]
    assert record["brand"] == "Polymaker"
    assert record["product_line"] == "PLA 哑光"


def test_standard_library_xlsx_reader(tmp_path: Path) -> None:
    workbook = tmp_path / "inventory.xlsx"
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
      <Default Extension="xml" ContentType="application/xml"/>
    </Types>"""
    workbook_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
    </workbook>"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="worksheet"/>
    </Relationships>"""
    sheet = """<?xml version="1.0" encoding="UTF-8"?>
    <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
      <row r="1"><c r="A1" t="inlineStr"><is><t>合计</t></is></c></row>
      <row r="2"><c r="C2" t="inlineStr"><is><t>拓竹PETG</t></is></c></row>
      <row r="3"><c r="B3" t="inlineStr"><is><t>黄色</t></is></c><c r="C3"><v>1.3</v></c></row>
    </sheetData></worksheet>"""
    with zipfile.ZipFile(workbook, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    records = load_inventory_workbook(workbook)
    assert records[0]["brand"] == "拓竹"
    assert records[0]["stock_spools"] == 1
    assert records[0]["opened_remaining_percent"] == 30
