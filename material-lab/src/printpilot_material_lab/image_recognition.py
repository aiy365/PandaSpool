from __future__ import annotations

"""Small, dependency-free image recognition boundary for the dashboard.

The dashboard deliberately keeps OCR outside the browser.  The browser only
uploads the private image; this module calls the server's installed
Tesseract binary and turns the returned text into a conservative draft.  It
never invents max-flow, K/PA or a machine profile from a marketing claim.
"""

import mimetypes
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .errors import InputError


MAX_RECOGNITION_BYTES = 8 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
KNOWN_MATERIALS = ("PETG", "PCTG", "PLA", "ABS", "ASA", "TPU", "PA", "PC", "PP", "PVA", "HIPS", "PET")
KNOWN_BRANDS = (
    "R3D", "SUNLU", "Polymaker", "Panchroma", "Bambu", "大简", "遇果",
    "NextShapes", "必趣", "BIQU", "拓竹",
)
COLOR_ALIASES: tuple[tuple[str, str], ...] = (
    ("透明", "透明"), ("transparent", "透明"), ("clear", "透明"),
    ("黑色", "黑色"), ("black", "黑色"), ("白色", "白色"), ("white", "白色"),
    ("灰色", "灰色"), ("gray", "灰色"), ("grey", "灰色"), ("红色", "红色"),
    ("red", "红色"), ("蓝色", "蓝色"), ("blue", "蓝色"), ("绿色", "绿色"),
    ("green", "绿色"), ("黄色", "黄色"), ("yellow", "黄色"), ("橙色", "橙色"),
    ("orange", "橙色"), ("紫色", "紫色"), ("purple", "紫色"), ("银色", "银色"),
    ("silver", "银色"), ("棕色", "棕色"), ("brown", "棕色"), ("自然色", "自然色"),
    ("natural", "自然色"),
)


def _clean_text(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value.replace("\r", "")).strip()


def _normalise_number(value: str) -> str:
    return value.replace("～", "-").replace("~", "-").strip()


def _line_value(lines: list[str], labels: tuple[str, ...], *, number_pattern: str = r"\d+(?:\.\d+)?(?:\s*(?:[-~～]|±)\s*\d+(?:\.\d+)?)?") -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(rf"(?:{label_pattern})[^\d\n:：]{{0,18}}[:：]?\s*({number_pattern})", re.IGNORECASE)
    for line in lines:
        match = pattern.search(line)
        if match:
            return _normalise_number(match.group(1))
    return None


def _claim(key: str, value: str | None, unit: str | None = None) -> dict[str, str]:
    result = {"key": key, "value": value or ""}
    if unit:
        result["unit"] = unit
    return result


def extract_claims(raw_text: str) -> dict[str, Any]:
    """Extract only values that are visibly associated with a known label."""

    text = _clean_text(raw_text)
    lines = [_clean_text(line) for line in text.splitlines() if _clean_text(line)]
    joined = "\n".join(lines)
    claims: list[dict[str, str]] = []

    labelled_values = (
        ("nozzle_temperature", ("喷嘴温度", "喷头温度", "nozzle temperature", "nozzle temp"), "°C"),
        ("bed_temperature", ("热床温度", "底板温度", "底版温度", "bed temperature", "bed temp"), "°C"),
        ("cooling_fan", ("冷却风扇", "冷却风扇", "cooling fan", "fan"), "%"),
        ("print_speed", ("打印速度", "printing speed", "print speed"), "mm/s"),
        ("drying_temperature", ("烘干温度", "干燥温度", "drying temperature", "drying temp"), "°C"),
        ("drying_time", ("烘干时间", "干燥时间", "drying time", "drying"), ""),
        ("retraction_distance", ("回抽距离", "retraction distance"), "mm"),
        ("retraction_speed", ("回抽速度", "retraction speed"), "mm/s"),
        ("density", ("密度", "density"), "g/cm³"),
        ("heat_deflection_temperature", ("热变形温度", "热变型温度", "heat deflection temperature"), "°C"),
        ("melt_flow_index", ("熔融指数", "熔体流动速率", "melt flow index"), "g/10min"),
        ("vicat_softening_temperature", ("维卡软化温度", "vicat softening temperature"), "°C"),
        ("tensile_strength", ("拉伸强度", "tensile strength"), "MPa"),
        ("tensile_modulus", ("拉伸模量", "杨氏模量", "tensile modulus", "young's modulus"), "MPa"),
        ("elongation_at_break", ("断裂伸长率", "拉伸断裂伸长率", "elongation at break"), "%"),
        ("flexural_strength", ("弯曲强度", "flexural strength"), "MPa"),
        ("flexural_modulus", ("弯曲模量", "flexural modulus"), "MPa"),
        ("notched_impact_strength", ("缺口冲击强度", "notched impact strength"), "kJ/m²"),
        ("unnotched_impact_strength", ("无缺口冲击强度", "unnotched impact strength"), "kJ/m²"),
        ("shore_hardness", ("邵氏硬度", "shore hardness"), "Shore D"),
        ("water_absorption", ("吸水率", "water absorption"), "%"),
    )
    for key, labels, unit in labelled_values:
        candidate_lines = lines
        if key == "notched_impact_strength":
            candidate_lines = [
                line for line in lines
                if "无缺口" not in line and "unnotched" not in line.casefold()
            ]
        value = _line_value(candidate_lines, labels)
        if value:
            claims.append(_claim(key, value, unit or None))

    diameter_match = re.search(r"(?:线径|直径|diameter)[^\n:：]{0,12}[:：]?\s*(1\.75|2\.85)\s*(?:mm|毫米)?", joined, re.IGNORECASE)
    if diameter_match:
        claims.append(_claim("diameter", diameter_match.group(1), "mm"))

    weight_match = re.search(r"(?:净重|重量|net weight)[^\d\n:：]{0,12}[:：]?\s*(\d+(?:\.\d+)?)\s*(kg|g|千克|克)", joined, re.IGNORECASE)
    if weight_match:
        unit = "kg" if weight_match.group(2).casefold() in {"kg", "千克"} else "g"
        claims.append(_claim("spool_weight", weight_match.group(1), unit))

    nozzle_match = re.search(r"(?:喷嘴尺寸|喷嘴兼容性|nozzle compatibility)[^\n:：]{0,18}[:：]?\s*([^\n]+)", joined, re.IGNORECASE)
    if nozzle_match:
        claims.append(_claim("nozzle_compatibility", _clean_text(nozzle_match.group(1))))

    surface_match = re.search(r"(?:底板材质|打印面|build surface)[^\n:：]{0,18}[:：]?\s*([^\n]+)", joined, re.IGNORECASE)
    if surface_match:
        claims.append(_claim("build_surface", _clean_text(surface_match.group(1))))

    material = next((item for item in KNOWN_MATERIALS if re.search(rf"(?<![A-Za-z]){re.escape(item)}(?![A-Za-z])", text, re.IGNORECASE)), None)
    brand = next((item for item in KNOWN_BRANDS if item.casefold() in text.casefold()), None)
    color = next((normalised for alias, normalised in COLOR_ALIASES if alias.casefold() in text.casefold()), None)

    quote_lines = [line for line in lines if re.search(r"客服|商家|默认参数|照默认|按默认|直接用|default", line, re.IGNORECASE)]
    quote = "；".join(dict.fromkeys(quote_lines))[:4000] if quote_lines else None
    if quote:
        claims.append(_claim("customer_quote", quote))

    variant = None
    if material:
        variant_match = re.search(rf"{re.escape(material)}\s*([\u4e00-\u9fffA-Za-z][^\n,，;；|/]{{0,20}})", text, re.IGNORECASE)
        if variant_match:
            candidate = _clean_text(variant_match.group(1)).strip(" -:：")
            if candidate and candidate.casefold() not in {"打印", "建议", "参数"}:
                variant = candidate

    suggested_product = " ".join(item for item in (material, variant) if item) or None
    suggested_title = " ".join(item for item in (brand, suggested_product, color, "参数资料") if item) or "图片参数资料"
    warnings = ["识别结果来自图片文字，保存前请核对高亮字段。"]
    if not claims:
        warnings.append("未识别出带标签的打印参数；原图仍会作为证据保存。")
    if any(claim["key"] == "nozzle_compatibility" for claim in claims) and not any("mm" in claim["value"] for claim in claims if claim["key"] == "nozzle_compatibility"):
        warnings.append("喷嘴兼容性只保留原文，不会据此推算最大体积流量。")

    return {
        "raw_text": text[:20000],
        "claims": claims,
        "suggested": {
            "brand": brand,
            "product_line": suggested_product,
            "material_type": material,
            "variant": variant,
            "color": color,
            "diameter_mm": float(diameter_match.group(1)) if diameter_match else None,
            "quote": quote,
            "title": suggested_title,
        },
        "warnings": warnings,
        "engine": "tesseract/chi_sim+eng",
    }


def _validate_image(file_bytes: bytes, filename: str, media_type: str | None) -> str:
    if not file_bytes:
        raise InputError("图片不能为空。")
    if len(file_bytes) > MAX_RECOGNITION_BYTES:
        raise InputError("图片不能超过8MB。")
    detected = ""
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = "image/png"
    elif file_bytes.startswith(b"\xff\xd8\xff"):
        detected = "image/jpeg"
    elif file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        detected = "image/webp"
    supplied = (media_type or mimetypes.guess_type(filename)[0] or "").split(";", 1)[0].lower()
    if detected not in SUPPORTED_IMAGE_TYPES or (supplied and supplied not in SUPPORTED_IMAGE_TYPES):
        raise InputError("目前只支持PNG、JPG或WebP图片识别。")
    return detected


def recognize_image(file_bytes: bytes, filename: str, media_type: str | None = None) -> dict[str, Any]:
    _validate_image(file_bytes, filename, media_type)
    executable = os.environ.get("PRINTPILOT_TESSERACT", "tesseract")
    suffix = Path(filename).suffix.lower() or ".png"
    try:
        with tempfile.NamedTemporaryFile(prefix="printpilot-ocr-", suffix=suffix, delete=False) as handle:
            handle.write(file_bytes)
            temporary_path = handle.name
        try:
            result = subprocess.run(
                [executable, temporary_path, "stdout", "-l", "chi_sim+eng", "--psm", "6"],
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
            )
        finally:
            try:
                Path(temporary_path).unlink(missing_ok=True)
            except OSError:
                pass
    except FileNotFoundError as exc:
        raise InputError("服务器未安装图像识别组件，请安装Tesseract后重试。") from exc
    except subprocess.TimeoutExpired as exc:
        raise InputError("图片识别超时，请裁剪图片后重试。") from exc
    if result.returncode != 0 and not result.stdout.strip():
        raise InputError("图片识别失败，请确认图片清晰且包含文字。")
    parsed = extract_claims(result.stdout)
    if result.stderr.strip() and "warning" not in result.stderr.lower():
        parsed["warnings"] = [*parsed["warnings"], "识别引擎返回了提示，建议人工核对原图。"]
    return parsed
