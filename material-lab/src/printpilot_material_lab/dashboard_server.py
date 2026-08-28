from __future__ import annotations

import base64
import binascii
import hmac
import json
import mimetypes
import secrets
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

from .dashboard_auth import CredentialStore, LoginLimiter, SessionStore
from .errors import DatabaseError, InputError, MaterialLabError
from .image_recognition import recognize_image as recognize_uploaded_image
from .material_domain import classify_color_family, compact_inventory_payload
from .local_store import (
    LocalStore,
    adjust_inventory,
    create_filament_record,
    add_filament_evidence,
    add_product_inbox_evidence,
    add_preset_evaluation,
    get_source_file,
    get_filament_detail,
    get_product_detail,
    list_dashboard_filaments,
    list_products,
    list_inventory_movements,
    set_inventory,
    set_inventory_details,
    undo_inventory_movement,
    update_filament_record,
)
from .preset_evaluation import evaluate_preset_bytes


# Evidence uploads are sent as base64 JSON. 8 MiB raw evidence needs about
# 10.7 MiB on the wire, plus the surrounding JSON envelope.
MAX_BODY_BYTES = 12 * 1024 * 1024
COOKIE_NAME = "printpilot_dashboard_session"
COOKIE_MAX_AGE = 12 * 60 * 60

LLMS_TEXT = """# PrintPilot 耗材看板

> 私有的3D打印耗材盘点与供应商资料档案。网页数据需要登录，不公开库存或原始资料。

## AI读取入口

- `GET /api/ai/inventory`：登录后返回紧凑的只读库存、色系和确定性评测，适合直接作为AI上下文。
- `GET /openapi.json`：机器可读的接口契约。
- `POST /api/products/evidence`：按产品保存原始资料图片；只进入待人工处理队列，不实时识别。

## 数据语义

- `sealed` 是未开封整卷数。
- `opened_pct` 是至多一卷已开封耗材的估算余量百分比。
- `color` 保留商家原色名，`family` 是用户可修改的标准色系。
- AI输出只用于整理和评测草稿；所有写入仍由用户在网页确认。
- 当前库存接口不提供3MF、耗材选择、喷嘴或切片参数推荐。
"""


def _openapi_document() -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {"title": "PrintPilot Material Dashboard", "version": "0.2.0"},
        "paths": {
            "/api/ai/inventory": {
                "get": {
                    "summary": "读取低Token耗材库存与评测包",
                    "security": [{"sessionCookie": []}],
                    "responses": {"200": {"description": "紧凑库存包"}, "401": {"description": "需要登录"}},
                }
            },
            "/api/evidence/recognize": {
                "post": {
                    "summary": "识别商家参数截图并返回待确认草稿",
                    "security": [{"sessionCookie": []}],
                    "responses": {"200": {"description": "识别草稿"}},
                }
            },
            "/api/products/evidence": {
                "post": {
                    "summary": "上传产品原始资料图片并标记为待人工处理",
                    "security": [{"sessionCookie": []}],
                    "responses": {"201": {"description": "图片已私有归档"}},
                }
            },
            "/api/inventory/set-details": {
                "post": {
                    "summary": "盘点未开封卷和在用卷余量",
                    "security": [{"sessionCookie": []}],
                    "responses": {"200": {"description": "更新后的库存"}},
                }
            },
        },
        "components": {
            "securitySchemes": {
                "sessionCookie": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": COOKIE_NAME,
                }
            }
        },
    }


class DashboardRequestError(MaterialLabError):
    code = "dashboard_request_error"

    def __init__(self, message: str, status: HTTPStatus) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class DashboardConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    open_browser: bool = True
    static_root: Path = Path(__file__).with_name("dashboard_dist")
    public_origin: str | None = None
    auth_file: Path | None = None

    @property
    def password_auth(self) -> bool:
        return self.auth_file is not None

    def validate(self) -> None:
        if not self.static_root.joinpath("index.html").is_file():
            raise DashboardRequestError(
                "看板前端尚未构建；请先在dashboard目录运行npm install和npm run build。",
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
        if self.public_origin:
            parsed = urllib.parse.urlsplit(self.public_origin)
            if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}:
                raise DashboardRequestError(
                    "公网访问地址必须是没有路径的HTTPS地址。",
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
        if self.password_auth:
            if not self.public_origin:
                raise DashboardRequestError(
                    "密码鉴权模式必须配置HTTPS公网访问地址。",
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
            CredentialStore(self.auth_file).snapshot()


class InventoryDashboardService:
    def __init__(
        self,
        list_records: Callable[[], list[dict[str, Any]]] = list_dashboard_filaments,
        adjust: Callable[[str, int, bool], dict[str, Any]] = adjust_inventory,
        set_values: Callable[
            [str, int, int | None, int | None, bool], dict[str, Any]
        ] = set_inventory,
        update_filament: Callable[
            [str, dict[str, Any], bool], dict[str, Any]
        ] = update_filament_record,
        create_filament: Callable[..., dict[str, Any]] = create_filament_record,
        get_detail: Callable[[str], dict[str, Any]] = get_filament_detail,
        list_product_records: Callable[[], list[dict[str, Any]]] = list_products,
        get_product: Callable[[str], dict[str, Any]] = get_product_detail,
        list_movements: Callable[[str | None, int], list[dict[str, Any]]] = list_inventory_movements,
        apply_movement: Callable[..., dict[str, Any]] = adjust_inventory,
        undo_movement: Callable[[str, bool], dict[str, Any]] = undo_inventory_movement,
        set_details: Callable[..., dict[str, Any]] = set_inventory_details,
        add_evidence: Callable[..., dict[str, Any]] = add_filament_evidence,
        add_product_evidence: Callable[..., dict[str, Any]] = add_product_inbox_evidence,
        get_evidence_file: Callable[[str], tuple[Path, str | None, str]] = get_source_file,
        recognize_image: Callable[[bytes, str, str | None], dict[str, Any]] = recognize_uploaded_image,
        save_preset_evaluation: Callable[..., dict[str, Any]] = add_preset_evaluation,
    ) -> None:
        self._list_records = list_records
        self._adjust = adjust
        self._set_values = set_values
        self._update_filament = update_filament
        self._create_filament = create_filament
        self._get_detail = get_detail
        self._list_product_records = list_product_records
        self._get_product = get_product
        self._list_movements = list_movements
        self._apply_movement = apply_movement
        self._undo_movement = undo_movement
        self._set_details = set_details
        self._add_evidence = add_evidence
        self._add_product_evidence = add_product_evidence
        self._get_evidence_file = get_evidence_file
        self._recognize_image = recognize_image
        self._save_preset_evaluation = save_preset_evaluation

    def list(self) -> dict[str, Any]:
        rows = self._list_records()
        return {
            "rows": rows,
            "summary": {
                "filament_count": len(rows),
                "stock_spools": sum(int(row["stock_spools"]) for row in rows),
                "opened_spool_count": sum(int(row.get("opened_remaining_percent") or 0) > 0 for row in rows),
                "stock_equivalent": round(sum(float(row.get("stock_equivalent", int(row.get("stock_spools") or 0) + int(row.get("opened_remaining_percent") or 0) / 100)) for row in rows), 2),
                "product_series_count": len({(row.get("brand"), row.get("product_line"), row.get("material_type")) for row in rows}),
                "color_variant_count": len({(row.get("color_family") or classify_color_family(row.get("color")), row.get("color")) for row in rows}),
                "unclassified_color_count": sum((row.get("color_family") or classify_color_family(row.get("color"))) == "未分类" for row in rows),
                "stock_total_kg": round(
                    sum(float(row["stock_total_kg"]) for row in rows), 3
                ),
                "low_stock_count": sum(
                    row["stock_status"] in {"低库存", "无库存"} for row in rows
                ),
                "replenishment_spools": round(
                    sum(float(row.get("replenishment_spools") or 0) for row in rows), 2
                ),
                "needs_attention_count": sum(
                    int(row.get("source_count") or 0) == 0
                    or int(row.get("conflict_count") or 0) > 0
                    or (row.get("color_family") or classify_color_family(row.get("color")))
                    == "未分类"
                    for row in rows
                ),
            },
        }

    def ai_inventory(self) -> dict[str, Any]:
        return compact_inventory_payload(self._list_records())

    def products(self) -> dict[str, Any]:
        rows = self._list_product_records()
        return {
            "rows": rows,
            "summary": {
                "product_count": len(rows),
                "color_count": sum(int(row.get("color_count") or 0) for row in rows),
                "stock_equivalent": round(sum(float(row.get("stock_equivalent") or 0) for row in rows), 2),
                "manufacturer_preset_count": sum(
                    int(row.get("manufacturer_preset_count") or 0) for row in rows
                ),
            },
        }

    def product_detail(self, product_id: str) -> dict[str, Any]:
        self._validate_uuid(product_id, "product_id")
        return self._get_product(product_id)

    def detail(self, filament_id: str) -> dict[str, Any]:
        self._validate_uuid(filament_id, "filament_id")
        return self._get_detail(filament_id)

    def movements(self, filament_id: str | None, limit: int) -> list[dict[str, Any]]:
        if filament_id:
            self._validate_uuid(filament_id, "filament_id")
        if not 1 <= limit <= 200:
            raise InputError("limit必须在1到200之间。")
        return self._list_movements(filament_id, limit)

    def adjust(self, payload: dict[str, Any]) -> dict[str, Any]:
        filament_id = self._filament_id(payload)
        delta = self._integer(payload, "delta", minimum=-1000, maximum=1000)
        if delta == 0:
            raise InputError("库存调整量不能为0。")
        return self._adjust(filament_id, delta, True)

    def set(self, payload: dict[str, Any]) -> dict[str, Any]:
        filament_id = self._filament_id(payload)
        spools = self._integer(payload, "stock_spools", minimum=0, maximum=10000)
        weight = self._optional_integer(
            payload, "spool_weight_g", minimum=1, maximum=100000
        )
        threshold = self._optional_integer(
            payload, "low_stock_threshold", minimum=0, maximum=10000
        )
        return self._set_values(filament_id, spools, weight, threshold, True)

    def set_details(self, payload: dict[str, Any]) -> dict[str, Any]:
        filament_id = self._filament_id(payload)
        return self._set_details(
            filament_id,
            self._integer(payload, "stock_spools", minimum=0, maximum=10000),
            self._optional_integer(payload, "spool_weight_g", minimum=1, maximum=100000),
            self._optional_integer(payload, "low_stock_threshold", minimum=0, maximum=10000),
            self._optional_integer(payload, "target_stock_spools", minimum=0, maximum=10000),
            self._optional_text(payload, "storage_location", 200),
            self._optional_text(payload, "inventory_notes", 1000),
            self._optional_text(payload, "movement_note", 500),
            True,
            self._optional_integer(payload, "opened_remaining_percent", minimum=0, maximum=100),
        )

    def create_filament(self, payload: dict[str, Any]) -> dict[str, Any]:
        fields = payload.get("fields")
        if not isinstance(fields, dict):
            raise InputError("fields必须是对象。")
        return self._create_filament(
            fields,
            self._integer(payload, "stock_spools", minimum=0, maximum=10000),
            self._integer(payload, "spool_weight_g", minimum=1, maximum=100000),
            self._integer(payload, "low_stock_threshold", minimum=0, maximum=10000),
            self._integer(payload, "target_stock_spools", minimum=0, maximum=10000),
            self._optional_text(payload, "storage_location", 200),
            self._optional_text(payload, "inventory_notes", 1000),
            True,
            self._optional_integer(payload, "opened_remaining_percent", minimum=0, maximum=100) or 0,
        )

    def movement(self, payload: dict[str, Any]) -> dict[str, Any]:
        filament_id = self._filament_id(payload)
        delta = self._integer(payload, "delta", minimum=-1000, maximum=1000)
        if delta == 0:
            raise InputError("库存调整量不能为0。")
        movement_type = payload.get("movement_type")
        if movement_type not in {"purchase", "usage", "correction"}:
            raise InputError("movement_type必须是purchase、usage或correction。")
        return self._apply_movement(
            filament_id,
            delta,
            True,
            movement_type,
            self._optional_text(payload, "note", 500),
        )

    def undo(self, payload: dict[str, Any]) -> dict[str, Any]:
        movement_id = str(payload.get("movement_id") or "")
        self._validate_uuid(movement_id, "movement_id")
        return self._undo_movement(movement_id, True)

    def update_filament(self, payload: dict[str, Any]) -> dict[str, Any]:
        filament_id = self._filament_id(payload)
        fields = payload.get("fields")
        if not isinstance(fields, dict):
            raise InputError("fields必须是对象。")
        return self._update_filament(filament_id, fields, True)

    def add_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        filament_id = self._filament_id(payload)
        source = payload.get("source")
        if not isinstance(source, dict):
            raise InputError("source必须是对象。")
        claims = payload.get("claims", [])
        if not isinstance(claims, list):
            raise InputError("claims必须是数组。")
        file_bytes: bytes | None = None
        filename: str | None = None
        media_type: str | None = None
        uploaded = payload.get("file")
        if uploaded is not None:
            if not isinstance(uploaded, dict):
                raise InputError("file必须是对象。")
            encoded = uploaded.get("data_base64")
            if not isinstance(encoded, str) or not encoded:
                raise InputError("上传资料缺少data_base64。")
            filename = self._optional_text(uploaded, "filename", 200)
            media_type = self._optional_text(uploaded, "media_type", 100)
            try:
                file_bytes = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise InputError("上传资料不是有效的Base64文件。") from exc
            if len(file_bytes) > 8 * 1024 * 1024:
                raise InputError("单份厂家资料不能超过8MB。")
        return self._add_evidence(
            filament_id,
            source,
            claims,
            file_bytes,
            filename,
            media_type,
            True,
        )

    def add_product_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        product_id = str(payload.get("product_id") or "")
        self._validate_uuid(product_id, "product_id")
        source = payload.get("source")
        if not isinstance(source, dict):
            raise InputError("source必须是对象。")
        uploaded = payload.get("file")
        if not isinstance(uploaded, dict):
            raise InputError("必须上传产品资料图片。")
        filename = self._optional_text(uploaded, "filename", 200)
        media_type = self._optional_text(uploaded, "media_type", 100)
        encoded = uploaded.get("data_base64")
        if not filename or not media_type or not isinstance(encoded, str) or not encoded:
            raise InputError("产品资料图片信息不完整。")
        try:
            file_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise InputError("产品资料图片不是有效Base64文件。") from exc
        if not file_bytes or len(file_bytes) > 8 * 1024 * 1024:
            raise InputError("单张产品资料图片不能为空且不能超过8MB。")
        signatures = {
            "image/png": file_bytes.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/jpeg": file_bytes.startswith(b"\xff\xd8\xff"),
            "image/webp": len(file_bytes) >= 12
            and file_bytes.startswith(b"RIFF")
            and file_bytes[8:12] == b"WEBP",
        }
        if media_type not in signatures or not signatures[media_type]:
            raise InputError("只支持内容真实有效的PNG、JPG或WebP图片。")
        return self._add_product_evidence(
            product_id,
            source,
            file_bytes,
            filename,
            media_type,
            True,
        )

    def add_product_preset(self, payload: dict[str, Any]) -> dict[str, Any]:
        product_id = str(payload.get("product_id") or "")
        self._validate_uuid(product_id, "product_id")
        filament_id = payload.get("filament_id")
        if filament_id is not None:
            filament_id = str(filament_id)
            self._validate_uuid(filament_id, "filament_id")
        authority = str(payload.get("authority") or "manufacturer_profile")
        provenance = self._optional_text(payload, "provenance", 1000)
        if not provenance:
            raise InputError("必须说明预设由谁提供、如何取得。")
        uploaded = payload.get("file")
        if not isinstance(uploaded, dict):
            raise InputError("必须上传JSON或BBSFLMT预设文件。")
        filename = self._optional_text(uploaded, "filename", 200)
        encoded = uploaded.get("data_base64")
        if not filename or not isinstance(encoded, str) or not encoded:
            raise InputError("预设文件信息不完整。")
        if Path(filename).suffix.casefold() not in {".json", ".bbsflmt"}:
            raise InputError("只支持JSON或BBSFLMT耗材预设。")
        try:
            file_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise InputError("上传的预设不是有效Base64文件。") from exc
        if not file_bytes or len(file_bytes) > 8 * 1024 * 1024:
            raise InputError("预设文件不能为空且不能超过8MB。")
        report = evaluate_preset_bytes(
            filename,
            file_bytes,
            authority=authority,
            provenance=provenance,
        )
        profiles = report["profiles"]
        if len(profiles) != 1:
            raise InputError("一个上传文件必须恰好包含一个A1 0.4 mm预设。")
        profile = profiles[0]
        if profile["scope_level"] == "product":
            filament_id = None
        elif filament_id is None:
            color_hint = str(profile.get("color") or "").casefold()
            colors = self._get_product(product_id).get("colors", [])
            matches = [
                row
                for row in colors
                if color_hint and color_hint in str(row.get("color") or "").casefold()
            ]
            if len(matches) != 1:
                raise InputError(
                    f"预设识别为{profile.get('color') or '特定'}颜色专用，但无法唯一匹配库存颜色。"
                )
            filament_id = str(matches[0]["filament_id"])
        result = self._save_preset_evaluation(
            product_id,
            filament_id,
            profile,
            file_bytes,
            filename,
            True,
        )
        return {**result, "evaluation": profile, "filament_id": filament_id}

    def evidence_file(self, source_id: str) -> tuple[Path, str | None, str]:
        self._validate_uuid(source_id, "source_id")
        return self._get_evidence_file(source_id)

    def recognize_image(self, payload: dict[str, Any]) -> dict[str, Any]:
        uploaded = payload.get("file")
        if not isinstance(uploaded, dict):
            raise InputError("file必须是对象。")
        encoded = uploaded.get("data_base64")
        if not isinstance(encoded, str) or not encoded:
            raise InputError("识别图片缺少data_base64。")
        filename = self._optional_text(uploaded, "filename", 200) or "upload.png"
        media_type = self._optional_text(uploaded, "media_type", 100)
        try:
            file_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise InputError("识别图片不是有效的Base64文件。") from exc
        if len(file_bytes) > 8 * 1024 * 1024:
            raise InputError("识别图片不能超过8MB。")
        return self._recognize_image(file_bytes, filename, media_type)

    @staticmethod
    def _filament_id(payload: dict[str, Any]) -> str:
        value = str(payload.get("filament_id") or "")
        InventoryDashboardService._validate_uuid(value, "filament_id")
        return value

    @staticmethod
    def _validate_uuid(value: str, field: str) -> None:
        try:
            UUID(value)
        except ValueError as exc:
            raise InputError(f"{field}必须是有效UUID。") from exc

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str, maximum: int) -> str | None:
        if key not in payload or payload[key] is None:
            return None
        value = payload[key]
        if not isinstance(value, str):
            raise InputError(f"{key}必须是文本。")
        if len(value.strip()) > maximum:
            raise InputError(f"{key}不能超过{maximum}个字符。")
        return value.strip()

    @classmethod
    def _optional_integer(
        cls,
        payload: dict[str, Any],
        key: str,
        *,
        minimum: int,
        maximum: int,
    ) -> int | None:
        if key not in payload or payload[key] is None:
            return None
        return cls._integer(payload, key, minimum=minimum, maximum=maximum)

    @staticmethod
    def _integer(
        payload: dict[str, Any], key: str, *, minimum: int, maximum: int
    ) -> int:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise InputError(f"{key}必须是整数。")
        if not minimum <= value <= maximum:
            raise InputError(f"{key}必须在{minimum}到{maximum}之间。")
        return value


class DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        static_root: Path,
        session_token: str,
        service: InventoryDashboardService,
        config: DashboardConfig,
    ) -> None:
        super().__init__(address, DashboardRequestHandler)
        self.static_root = static_root.resolve()
        self.session_token = session_token
        self.service = service
        self.config = config
        self.credentials = CredentialStore(config.auth_file) if config.auth_file else None
        self.sessions = SessionStore()
        self.login_limiter = LoginLimiter()
        self.write_lock = threading.Lock()

    @property
    def origin(self) -> str:
        host, port = self.server_address
        return f"http://{host}:{port}"

    @property
    def browser_origin(self) -> str:
        return self.config.public_origin or self.origin


class DashboardRequestHandler(BaseHTTPRequestHandler):
    server: DashboardHTTPServer
    server_version = "PrintPilotDashboard/0.1"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        request_id = uuid4().hex
        started = time.monotonic()
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        parsed_path = urllib.parse.urlsplit(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)
        try:
            self._require_host()
            if path.startswith("/launch/") and not self.server.config.password_auth:
                status = self._launch(path)
            elif path == "/health":
                status = self._json(
                    HTTPStatus.OK,
                    {"data": {"status": "ok"}, "request_id": request_id},
                )
            elif path == "/ready":
                status = self._json(
                    HTTPStatus.OK,
                    {"data": {"status": "ready"}, "request_id": request_id},
                )
            elif path == "/api/session":
                session = self._session()
                status = self._json(
                    HTTPStatus.OK,
                    {
                        "data": {
                            "authenticated": session is not None,
                            "mode": "password" if self.server.config.password_auth else "local",
                            "username": getattr(session, "username", None),
                        },
                        "request_id": request_id,
                    },
                )
            elif path == "/llms.txt":
                status = self._text(HTTPStatus.OK, LLMS_TEXT, "text/plain; charset=utf-8")
            elif path == "/openapi.json":
                status = self._json(
                    HTTPStatus.OK,
                    _openapi_document(),
                    cache_control="public, max-age=3600",
                )
            else:
                if path.startswith("/api/evidence/") and path.endswith("/file"):
                    self._require_session()
                    source_id = path.removeprefix("/api/evidence/").removesuffix("/file").strip("/")
                    file_path, media_type, title = self.server.service.evidence_file(source_id)
                    status = self._private_file(file_path, media_type, title)
                elif path == "/api/filaments":
                    self._require_session()
                    status = self._json(
                        HTTPStatus.OK,
                        {"data": self.server.service.list(), "request_id": request_id},
                    )
                elif path == "/api/products":
                    self._require_session()
                    status = self._json(
                        HTTPStatus.OK,
                        {"data": self.server.service.products(), "request_id": request_id},
                    )
                elif path.startswith("/api/products/"):
                    self._require_session()
                    product_id = path.removeprefix("/api/products/")
                    status = self._json(
                        HTTPStatus.OK,
                        {
                            "data": self.server.service.product_detail(product_id),
                            "request_id": request_id,
                        },
                    )
                elif path == "/api/ai/inventory":
                    self._require_session()
                    status = self._json(
                        HTTPStatus.OK,
                        {"data": self.server.service.ai_inventory(), "request_id": request_id},
                    )
                elif path.startswith("/api/filaments/"):
                    self._require_session()
                    filament_id = path.removeprefix("/api/filaments/")
                    status = self._json(
                        HTTPStatus.OK,
                        {
                            "data": self.server.service.detail(filament_id),
                            "request_id": request_id,
                        },
                    )
                elif path == "/api/inventory/movements":
                    self._require_session()
                    filament_id = (query.get("filament_id") or [None])[0]
                    raw_limit = (query.get("limit") or ["50"])[0]
                    try:
                        limit = int(raw_limit)
                    except ValueError as exc:
                        raise InputError("limit必须是整数。") from exc
                    status = self._json(
                        HTTPStatus.OK,
                        {
                            "data": self.server.service.movements(filament_id, limit),
                            "request_id": request_id,
                        },
                    )
                else:
                    if not self.server.config.password_auth:
                        self._require_session()
                    status = self._static(path)
        except Exception as exc:  # global boundary
            status = self._handle_error(exc, request_id)
        finally:
            self._log_request(request_id, path, status, started)

    def do_POST(self) -> None:  # noqa: N802
        request_id = uuid4().hex
        started = time.monotonic()
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        path = urllib.parse.urlsplit(self.path).path
        try:
            self._require_host()
            self._require_same_origin()
            payload = self._read_json()
            if path == "/api/auth/login" and self.server.config.password_auth:
                status = self._login(payload, request_id)
            elif path == "/api/auth/logout" and self.server.config.password_auth:
                token = self._require_session_token()
                self.server.sessions.revoke(token)
                status = self._json(
                    HTTPStatus.OK,
                    {"data": {"status": "logged_out"}, "request_id": request_id},
                    headers={"Set-Cookie": self._expired_cookie()},
                )
            elif path == "/api/auth/settings" and self.server.config.password_auth:
                self._require_session()
                status = self._update_credentials(payload, request_id)
            elif path == "/api/inventory/adjust":
                self._require_session()
                with self.server.write_lock:
                    result = self.server.service.adjust(payload)
                status = self._json(
                    HTTPStatus.OK, {"data": result, "request_id": request_id}
                )
            elif path == "/api/inventory/set":
                self._require_session()
                with self.server.write_lock:
                    result = self.server.service.set(payload)
                status = self._json(
                    HTTPStatus.OK, {"data": result, "request_id": request_id}
                )
            elif path == "/api/inventory/set-details":
                self._require_session()
                with self.server.write_lock:
                    result = self.server.service.set_details(payload)
                status = self._json(
                    HTTPStatus.OK, {"data": result, "request_id": request_id}
                )
            elif path == "/api/inventory/movement":
                self._require_session()
                with self.server.write_lock:
                    result = self.server.service.movement(payload)
                status = self._json(
                    HTTPStatus.OK, {"data": result, "request_id": request_id}
                )
            elif path == "/api/inventory/undo":
                self._require_session()
                with self.server.write_lock:
                    result = self.server.service.undo(payload)
                status = self._json(
                    HTTPStatus.OK, {"data": result, "request_id": request_id}
                )
            elif path == "/api/filaments/update":
                self._require_session()
                with self.server.write_lock:
                    result = self.server.service.update_filament(payload)
                status = self._json(
                    HTTPStatus.OK, {"data": result, "request_id": request_id}
                )
            elif path == "/api/filaments/evidence":
                self._require_session()
                with self.server.write_lock:
                    result = self.server.service.add_evidence(payload)
                status = self._json(
                    HTTPStatus.CREATED, {"data": result, "request_id": request_id}
                )
            elif path == "/api/products/evidence":
                self._require_session()
                with self.server.write_lock:
                    result = self.server.service.add_product_evidence(payload)
                status = self._json(
                    HTTPStatus.CREATED, {"data": result, "request_id": request_id}
                )
            elif path == "/api/products/presets":
                self._require_session()
                with self.server.write_lock:
                    result = self.server.service.add_product_preset(payload)
                status = self._json(
                    HTTPStatus.CREATED, {"data": result, "request_id": request_id}
                )
            elif path == "/api/evidence/recognize":
                self._require_session()
                result = self.server.service.recognize_image(payload)
                status = self._json(
                    HTTPStatus.OK, {"data": result, "request_id": request_id}
                )
            elif path == "/api/filaments/create":
                self._require_session()
                with self.server.write_lock:
                    result = self.server.service.create_filament(payload)
                status = self._json(
                    HTTPStatus.CREATED, {"data": result, "request_id": request_id}
                )
            elif path == "/api/shutdown":
                if self.server.config.password_auth:
                    raise DashboardRequestError(
                        "服务器看板不能从网页关闭。", HTTPStatus.FORBIDDEN
                    )
                self._require_session()
                status = self._json(
                    HTTPStatus.OK,
                    {"data": {"status": "closing"}, "request_id": request_id},
                )
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                raise DashboardRequestError("接口不存在。", HTTPStatus.NOT_FOUND)
        except Exception as exc:  # global boundary
            status = self._handle_error(exc, request_id)
        finally:
            self._log_request(request_id, path, status, started)

    def _launch(self, path: str) -> HTTPStatus:
        supplied = path.removeprefix("/launch/")
        if not hmac.compare_digest(supplied, self.server.session_token):
            raise DashboardRequestError("启动链接已失效。", HTTPStatus.UNAUTHORIZED)
        self.send_response(HTTPStatus.SEE_OTHER)
        self._security_headers()
        self.send_header(
            "Set-Cookie",
            f"{COOKIE_NAME}={self.server.session_token}; HttpOnly; SameSite=Strict; Path=/",
        )
        self.send_header("Location", "/")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return HTTPStatus.SEE_OTHER

    def _session_token(self) -> str:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        supplied = cookie.get(COOKIE_NAME)
        return supplied.value if supplied else ""

    def _session(self) -> Any | None:
        token = self._session_token()
        if not token:
            return None
        if not self.server.config.password_auth:
            if hmac.compare_digest(token, self.server.session_token):
                return type("LocalSession", (), {"username": None})()
            return None
        assert self.server.credentials is not None
        try:
            revision = self.server.credentials.snapshot().revision
        except InputError:
            return None
        return self.server.sessions.get(token, revision)

    def _require_session_token(self) -> str:
        token = self._session_token()
        if self._session() is None:
            raise DashboardRequestError(
                "登录会话已失效，请重新登录。", HTTPStatus.UNAUTHORIZED
            )
        return token

    def _require_session(self) -> Any:
        session = self._session()
        if session is None:
            message = (
                "登录会话已失效，请重新登录。"
                if self.server.config.password_auth
                else "本地看板会话无效，请重新启动。"
            )
            raise DashboardRequestError(message, HTTPStatus.UNAUTHORIZED)
        return session

    def _login(self, payload: dict[str, Any], request_id: str) -> HTTPStatus:
        if self.server.login_limiter.is_blocked():
            raise DashboardRequestError(
                "登录失败次数过多，请10分钟后再试。", HTTPStatus.TOO_MANY_REQUESTS
            )
        username = payload.get("username")
        password = payload.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            raise InputError("用户名和密码不能为空。")
        assert self.server.credentials is not None
        snapshot = self.server.credentials.verify(username, password)
        if snapshot is None:
            self.server.login_limiter.failure()
            raise DashboardRequestError("用户名或密码错误。", HTTPStatus.UNAUTHORIZED)
        self.server.login_limiter.success()
        token = self.server.sessions.create(snapshot)
        return self._json(
            HTTPStatus.OK,
            {
                "data": {"username": snapshot.username, "mode": "password"},
                "request_id": request_id,
            },
            headers={"Set-Cookie": self._session_cookie(token)},
        )

    def _update_credentials(
        self, payload: dict[str, Any], request_id: str
    ) -> HTTPStatus:
        username = payload.get("username")
        current_password = payload.get("current_password")
        new_password_value = payload.get("new_password")
        if not isinstance(username, str) or not isinstance(current_password, str):
            raise InputError("用户名和当前密码不能为空。")
        if new_password_value is not None and not isinstance(new_password_value, str):
            raise InputError("新密码格式无效。")
        new_password = new_password_value or None
        assert self.server.credentials is not None
        snapshot = self.server.credentials.update(
            current_password=current_password,
            username=username,
            new_password=new_password,
        )
        self.server.sessions.revoke_all()
        return self._json(
            HTTPStatus.OK,
            {
                "data": {"username": snapshot.username, "reauthenticate": True},
                "request_id": request_id,
            },
            headers={"Set-Cookie": self._expired_cookie()},
        )

    def _session_cookie(self, token: str) -> str:
        secure = "; Secure" if self.server.config.password_auth else ""
        return (
            f"{COOKIE_NAME}={token}; HttpOnly; SameSite=Strict; Path=/; "
            f"Max-Age={COOKIE_MAX_AGE}{secure}"
        )

    def _expired_cookie(self) -> str:
        secure = "; Secure" if self.server.config.password_auth else ""
        return (
            f"{COOKIE_NAME}=; HttpOnly; SameSite=Strict; Path=/; "
            f"Max-Age=0{secure}"
        )

    def _require_host(self) -> None:
        expected = {
            urllib.parse.urlsplit(self.server.origin).netloc,
            urllib.parse.urlsplit(self.server.browser_origin).netloc,
        }
        if self.headers.get("Host") not in expected:
            raise DashboardRequestError("已拒绝无效的本地主机请求。", HTTPStatus.FORBIDDEN)

    def _require_same_origin(self) -> None:
        if self.headers.get("Origin") != self.server.browser_origin:
            raise DashboardRequestError("已拒绝跨站写入请求。", HTTPStatus.FORBIDDEN)

    def _read_json(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0]
        if content_type != "application/json":
            raise DashboardRequestError(
                "请求必须使用application/json。", HTTPStatus.UNSUPPORTED_MEDIA_TYPE
            )
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise DashboardRequestError("Content-Length无效。", HTTPStatus.BAD_REQUEST) from exc
        if size <= 0 or size > MAX_BODY_BYTES:
            raise DashboardRequestError("请求正文大小无效。", HTTPStatus.BAD_REQUEST)
        try:
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DashboardRequestError("JSON格式无效。", HTTPStatus.BAD_REQUEST) from exc
        if not isinstance(payload, dict):
            raise DashboardRequestError("JSON正文必须是对象。", HTTPStatus.BAD_REQUEST)
        return payload

    def _static(self, path: str) -> HTTPStatus:
        relative = "index.html" if path == "/" else path.lstrip("/")
        target = self.server.static_root.joinpath(relative).resolve()
        if not target.is_relative_to(self.server.static_root) or not target.is_file():
            raise DashboardRequestError("页面资源不存在。", HTTPStatus.NOT_FOUND)
        content = target.read_bytes()
        media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self._security_headers()
        self.send_header("Content-Type", f"{media_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header(
            "Cache-Control",
            "public, max-age=31536000, immutable"
            if "/assets/" in path
            else "no-cache",
        )
        self.end_headers()
        self.wfile.write(content)
        return HTTPStatus.OK

    def _private_file(
        self, path: Path, media_type: str | None, title: str
    ) -> HTTPStatus:
        content = path.read_bytes()
        detected = media_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        safe_title = title.replace("\r", " ").replace("\n", " ").replace('"', "'")[:180]
        ascii_title = "".join(
            character if 32 <= ord(character) < 127 and character not in "\\/;" else "_"
            for character in safe_title
        ).strip() or "evidence"
        encoded_title = urllib.parse.quote(safe_title or "evidence", safe="")
        self.send_response(HTTPStatus.OK)
        self._security_headers()
        self.send_header("Content-Type", detected)
        self.send_header("Content-Length", str(len(content)))
        self.send_header(
            "Content-Disposition",
            f"inline; filename=\"{ascii_title}\"; filename*=UTF-8''{encoded_title}",
        )
        self.send_header("Cache-Control", "private, no-store")
        self.end_headers()
        self.wfile.write(content)
        return HTTPStatus.OK

    def _json(
        self,
        status: HTTPStatus,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
        cache_control: str = "no-store",
    ) -> HTTPStatus:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", cache_control)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)
        return status

    def _text(self, status: HTTPStatus, text: str, media_type: str) -> HTTPStatus:
        content = text.encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(content)
        return status

    def _handle_error(self, exc: Exception, request_id: str) -> HTTPStatus:
        if isinstance(exc, DashboardRequestError):
            status = exc.status
            detail = str(exc)
            code = exc.code
        elif isinstance(exc, InputError):
            status = HTTPStatus.UNPROCESSABLE_ENTITY
            detail = str(exc)
            code = exc.code
        elif isinstance(exc, DatabaseError):
            status = HTTPStatus.BAD_GATEWAY
            detail = "无法访问本地数据库，请检查数据目录权限和磁盘状态。"
            code = exc.code
        else:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            detail = "本地看板发生未预期错误。"
            code = "internal_error"
        self._structured_log(
            "error",
            "request_failed",
            request_id=request_id,
            error_code=code,
            error_type=type(exc).__name__,
        )
        return self._json(
            status,
            {
                "error": {"code": code, "message": detail},
                "request_id": request_id,
            },
        )

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "font-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )

    def _log_request(
        self, request_id: str, path: str, status: HTTPStatus, started: float
    ) -> None:
        safe_path = "/launch/[redacted]" if path.startswith("/launch/") else path
        self._structured_log(
            "info",
            "request_complete",
            request_id=request_id,
            method=self.command,
            path=safe_path,
            status=int(status),
            duration_ms=round((time.monotonic() - started) * 1000, 1),
        )

    @staticmethod
    def _structured_log(level: str, event: str, **fields: Any) -> None:
        print(
            json.dumps(
                {"level": level, "event": event, **fields}, ensure_ascii=False
            ),
            flush=True,
        )


def create_dashboard_server(
    config: DashboardConfig,
    service: InventoryDashboardService | None = None,
    session_token: str | None = None,
) -> DashboardHTTPServer:
    config.validate()
    # An injected service is already fully configured (tests and embedded use).
    # The production path still initializes and migrates the local store before
    # accepting requests.
    if service is None:
        LocalStore().initialize()
    token = session_token or secrets.token_urlsafe(32)
    ports = [config.port] if config.port == 0 else list(range(config.port, config.port + 20))
    last_error: OSError | None = None
    for port in ports:
        try:
            return DashboardHTTPServer(
                (config.host, port),
                config.static_root,
                token,
                service or InventoryDashboardService(),
                config,
            )
        except OSError as exc:
            last_error = exc
    raise DashboardRequestError(
        f"无法在本机端口{config.port}到{config.port + 19}启动看板。",
        HTTPStatus.SERVICE_UNAVAILABLE,
    ) from last_error


def initialize_dashboard_auth(
    auth_file: str | Path,
    username: str,
    password_file: str | Path,
) -> None:
    password_path = Path(password_file).expanduser().resolve()
    try:
        password = password_path.read_text(encoding="utf-8").rstrip("\r\n")
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError("无法读取临时密码文件。") from exc
    CredentialStore(auth_file).initialize(username, password)


def run_dashboard(
    port: int = 8765,
    open_browser: bool = True,
    public_origin: str | None = None,
    auth_file: str | Path | None = None,
) -> int:
    config = DashboardConfig(
        port=port,
        open_browser=open_browser,
        public_origin=public_origin,
        auth_file=Path(auth_file) if auth_file else None,
    )
    server = create_dashboard_server(config)
    launch_url = f"{server.origin}/launch/{server.session_token}"
    DashboardRequestHandler._structured_log(
        "info", "dashboard_started", origin=server.origin
    )
    if config.open_browser and not config.password_auth:
        webbrowser.open(launch_url)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        DashboardRequestHandler._structured_log("info", "dashboard_stopped")
    return 0
