from __future__ import annotations

import subprocess

import pytest

from printpilot_material_lab.errors import InputError
from printpilot_material_lab.image_recognition import extract_claims, recognize_image


def test_extract_claims_keeps_marketing_values_as_claims() -> None:
    result = extract_claims(
        """遇果 常规 PETG 黑色
        线径 1.75mm
        喷嘴温度 230-260℃
        底板温度 60-70℃
        冷却风扇 100%
        打印速度 50-200mm/s
        客服：按照默认参数打就行
        """
    )
    assert result["suggested"]["material_type"] == "PETG"
    assert result["suggested"]["color"] == "黑色"
    assert result["suggested"]["diameter_mm"] == 1.75
    claims = {claim["key"]: claim["value"] for claim in result["claims"]}
    assert claims["nozzle_temperature"].startswith("230-260")
    assert claims["bed_temperature"].startswith("60-70")
    assert claims["cooling_fan"].startswith("100")
    assert claims["customer_quote"] == "客服：按照默认参数打就行"


def test_recognize_image_calls_tesseract_without_pillow(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "PETG\n喷嘴温度 240℃\n", "")

    monkeypatch.setattr("printpilot_material_lab.image_recognition.subprocess.run", fake_run)
    result = recognize_image(b"\x89PNG\r\n\x1a\nimage", "参数.png", "image/png")
    assert calls and calls[0][2:5] == ["stdout", "-l", "chi_sim+eng"]
    assert result["suggested"]["material_type"] == "PETG"


def test_recognize_image_rejects_non_image() -> None:
    with pytest.raises(InputError, match="PNG、JPG或WebP"):
        recognize_image(b"not-an-image", "参数.txt", "text/plain")


def test_extract_claims_keeps_physical_and_mechanical_properties() -> None:
    result = extract_claims(
        """三绿 PLA+2.0
        线径 1.75mm
        净重 1kg
        密度 1.21 g/cm3
        热变形温度 56±3℃
        熔融指数 8.3±2 g/10min
        维卡软化温度 54℃
        拉伸强度 46±5MPa
        断裂伸长率 10±2.5%
        弯曲强度 83±5MPa
        缺口冲击强度 10±3 kJ/m2
        """
    )
    claims = {claim["key"]: claim for claim in result["claims"]}
    assert claims["density"]["value"] == "1.21"
    assert claims["heat_deflection_temperature"]["value"] == "56±3"
    assert claims["tensile_strength"]["unit"] == "MPa"
    assert claims["notched_impact_strength"]["value"] == "10±3"
    assert claims["spool_weight"] == {"key": "spool_weight", "value": "1", "unit": "kg"}
