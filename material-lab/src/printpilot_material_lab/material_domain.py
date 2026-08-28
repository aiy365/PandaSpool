from __future__ import annotations

import json
from typing import Any

from .errors import InputError


FILAMENT_STATUSES = {"staged", "reviewed", "calibrated", "archived"}
FILAMENT_REQUIRED_TEXT_FIELDS = {"brand", "product_line", "material_type", "region"}
FILAMENT_OPTIONAL_TEXT_FIELDS = {
    "manufacturer",
    "seller",
    "variant",
    "color",
    "color_family",
    "sku",
    "barcode",
}
INVENTORY_MOVEMENT_TYPES = {"purchase", "usage", "count", "correction"}

COLOR_FAMILIES = (
    "白色系",
    "黑灰色系",
    "蓝色系",
    "绿色系",
    "红粉色系",
    "黄橙色系",
    "棕米色系",
    "紫色系",
    "金属色系",
    "透明/自然色系",
    "多色/效果色系",
    "未分类",
)


def classify_color_family(color: Any) -> str:
    """Return a conservative, user-overridable family for a supplier color name."""

    value = str(color or "").strip().casefold()
    if not value:
        return "未分类"
    rules = (
        (("蓝", "blue"), "蓝色系"),
        (("绿", "牛油果", "green"), "绿色系"),
        (("紫", "香芋", "purple", "violet"), "紫色系"),
        (("红", "粉", "桃", "rose", "pink", "red"), "红粉色系"),
        (("黄", "橙", "柠檬", "yellow", "orange"), "黄橙色系"),
        (("棕", "拿铁", "橡木", "咖啡", "肤", "米色", "brown", "beige"), "棕米色系"),
        (("金", "银", "铜", "metal", "gold", "silver"), "金属色系"),
        (("黑", "灰", "black", "gray", "grey"), "黑灰色系"),
        (("白", "white"), "白色系"),
        (("彩", "渐变", "虹", "多色", "rainbow", "multicolor"), "多色/效果色系"),
        (("透明", "自然", "clear", "transparent", "natural"), "透明/自然色系"),
    )
    return next((family for aliases, family in rules if any(alias in value for alias in aliases)), "未分类")


def clean_filament_text(value: Any, field: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise InputError(f"{field}必须是文本。")
    cleaned = value.strip()
    if required and not cleaned:
        raise InputError(f"{field}不能为空。")
    if len(cleaned) > 200:
        raise InputError(f"{field}不能超过200个字符。")
    return cleaned or None


def clean_optional_inventory_text(
    value: Any, field: str, maximum: int
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InputError(f"{field}必须是文本。")
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise InputError(f"{field}不能超过{maximum}个字符。")
    return cleaned or None


def inventory_summary(row: dict[str, Any]) -> dict[str, Any]:
    stock_spools = int(row.get("stock_spools") or 0)
    opened_remaining_percent = int(row.get("opened_remaining_percent") or 0)
    spool_weight_g = int(row.get("spool_weight_g") or 1000)
    low_stock_threshold = int(row.get("low_stock_threshold") or 0)
    target_stock_spools = int(row.get("target_stock_spools") or 0)
    stock_equivalent = round(stock_spools + opened_remaining_percent / 100, 2)
    if stock_equivalent == 0:
        stock_status = "无库存"
    elif stock_equivalent <= low_stock_threshold:
        stock_status = "低库存"
    else:
        stock_status = "正常"
    return {
        "filament_id": row["id"],
        "brand": row.get("brand"),
        "product_line": row.get("product_line"),
        "material_type": row.get("material_type"),
        "color": row.get("color"),
        "color_family": row.get("color_family") or classify_color_family(row.get("color")),
        "stock_spools": stock_spools,
        "sealed_spools": stock_spools,
        "opened_remaining_percent": opened_remaining_percent,
        "has_opened_spool": opened_remaining_percent > 0,
        "stock_equivalent": stock_equivalent,
        "spool_weight_g": spool_weight_g,
        "stock_total_kg": round(stock_equivalent * spool_weight_g / 1000, 3),
        "low_stock_threshold": low_stock_threshold,
        "target_stock_spools": target_stock_spools,
        "replenishment_spools": max(target_stock_spools - stock_equivalent, 0),
        "storage_location": row.get("storage_location"),
        "inventory_notes": row.get("inventory_notes"),
        "stock_status": stock_status,
        "inventory_updated_at": row.get("updated_at"),
    }


def dashboard_filament(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "filament_id": row["id"],
        "product_id": row.get("product_id"),
        "brand": row.get("brand"),
        "manufacturer": row.get("manufacturer"),
        "seller": row.get("seller"),
        "product_line": row.get("product_line"),
        "material_type": row.get("material_type"),
        "variant": row.get("variant"),
        "color": row.get("color"),
        "diameter_mm": float(row.get("diameter_mm") or 1.75),
        "sku": row.get("sku"),
        "barcode": row.get("barcode"),
        "region": row.get("region"),
        "status": row.get("status"),
        "created_at": row.get("created_at"),
        **inventory_summary(row),
    }


def readiness_summary(
    filament: dict[str, Any],
    profiles: list[dict[str, Any]],
    calibrations: list[dict[str, Any]],
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    stock = int(filament.get("stock_spools") or 0) + int(
        filament.get("opened_remaining_percent") or 0
    ) / 100
    profile_statuses = {str(item.get("status") or "") for item in profiles}
    accepted = [item for item in calibrations if item.get("status") == "accepted"]
    if stock == 0:
        state, label = "out_of_stock", "无库存"
    elif accepted or "print_calibrated" in profile_statuses:
        state, label = "print_calibrated", "已实测"
    elif "slice_validated" in profile_statuses:
        state, label = "slice_validated", "已切片验证"
    elif "official_profile_available" in profile_statuses:
        state, label = "official_profile", "官方预设可用"
    elif "draft_needs_calibration" in profile_statuses:
        state, label = "needs_calibration", "待校准"
    else:
        state, label = "missing_profile", "缺少预设"

    values: dict[str, set[str]] = {}
    for claim in claims:
        if claim.get("review_status") == "rejected":
            continue
        key = str(claim.get("claim_key") or "")
        signature = json.dumps(claim.get("value"), ensure_ascii=False, sort_keys=True)
        values.setdefault(key, set()).add(signature)
    return {
        "readiness_state": state,
        "readiness_label": label,
        "profile_count": len(profiles),
        "calibration_count": len(calibrations),
        "conflict_count": sum(len(items) > 1 for items in values.values()),
    }


def compact_inventory_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a low-token, read-only inventory packet for AI and exports."""

    products = {
        (str(row.get("brand") or ""), str(row.get("product_line") or ""), str(row.get("material_type") or ""))
        for row in rows
    }
    opened = [row for row in rows if int(row.get("opened_remaining_percent") or 0) > 0]
    unclassified = [row for row in rows if (row.get("color_family") or "未分类") == "未分类"]
    missing_sources = [row for row in rows if int(row.get("source_count") or 0) == 0]
    by_identity: dict[tuple[str, str, str, str], list[str]] = {}
    for row in rows:
        identity = (
            str(row.get("brand") or "").casefold(),
            str(row.get("product_line") or "").casefold(),
            str(row.get("material_type") or "").casefold(),
            str(row.get("color") or "").casefold(),
        )
        by_identity.setdefault(identity, []).append(str(row.get("filament_id") or ""))
    duplicates = [ids for ids in by_identity.values() if len(ids) > 1]

    actions: list[dict[str, Any]] = []
    if opened:
        actions.append(
            {
                "type": "opened_first",
                "count": len(opened),
                "message": f"有{len(opened)}种耗材存在在用卷，盘点时应优先核对这些余量。",
            }
        )
    if unclassified:
        actions.append(
            {
                "type": "color_review",
                "count": len(unclassified),
                "message": f"有{len(unclassified)}种颜色尚未归入色系。",
            }
        )
    if missing_sources:
        actions.append(
            {
                "type": "source_missing",
                "count": len(missing_sources),
                "message": f"有{len(missing_sources)}种在库耗材尚未附商家资料。",
            }
        )
    if duplicates:
        actions.append(
            {
                "type": "duplicate_review",
                "count": len(duplicates),
                "message": f"发现{len(duplicates)}组同产品同颜色重复档案，建议人工核对。",
            }
        )

    return {
        "v": 1,
        "summary": {
            "series": len(products),
            "variants": len(rows),
            "sealed": sum(int(row.get("stock_spools") or 0) for row in rows),
            "opened": len(opened),
            "equivalent": round(
                sum(
                    float(
                        row.get(
                            "stock_equivalent",
                            int(row.get("stock_spools") or 0)
                            + int(row.get("opened_remaining_percent") or 0) / 100,
                        )
                    )
                    for row in rows
                ),
                2,
            ),
        },
        "actions": actions,
        "items": [
            {
                "id": row.get("filament_id"),
                "product": f"{row.get('brand') or ''} · {row.get('product_line') or ''}",
                "material": row.get("material_type"),
                "color": row.get("color"),
                "family": row.get("color_family") or classify_color_family(row.get("color")),
                "sealed": int(row.get("stock_spools") or 0),
                "opened_pct": int(row.get("opened_remaining_percent") or 0),
                "sources": int(row.get("source_count") or 0),
            }
            for row in sorted(
                rows,
                key=lambda item: (
                    str(item.get("brand") or "").casefold(),
                    str(item.get("product_line") or "").casefold(),
                    str(item.get("color_family") or "").casefold(),
                    str(item.get("color") or "").casefold(),
                ),
            )
        ],
    }
