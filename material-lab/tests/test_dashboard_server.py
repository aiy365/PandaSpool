from __future__ import annotations

import base64
import http.client
import json
import threading
from pathlib import Path
from typing import Any

import pytest

from printpilot_material_lab.dashboard_server import (
    DashboardConfig,
    InventoryDashboardService,
    create_dashboard_server,
)
from printpilot_material_lab.dashboard_auth import CredentialStore


FILAMENT_ID = "11111111-1111-4111-8111-111111111111"
PRODUCT_ID = "33333333-3333-4333-8333-333333333333"


def _configure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRINTPILOT_DATABASE_PATH", raising=False)
    monkeypatch.delenv("PRINTPILOT_FILES_ROOT", raising=False)


def _row() -> dict[str, Any]:
    return {
        "filament_id": FILAMENT_ID,
        "brand": "R3D",
        "manufacturer": "R3D",
        "seller": None,
        "product_line": "PETG Transparent",
        "material_type": "PETG",
        "variant": "Transparent",
        "color": "Clear",
        "diameter_mm": 1.75,
        "sku": "R3D-PETG-TRANSPARENT-CLEAR-CN",
        "barcode": None,
        "region": "CN",
        "status": "reviewed",
        "stock_spools": 6,
        "spool_weight_g": 1000,
        "stock_total_kg": 6.0,
        "low_stock_threshold": 1,
        "stock_status": "正常",
        "source_count": 1,
        "claim_count": 1,
        "created_at": "2026-08-10T00:00:00Z",
        "inventory_updated_at": "2026-08-10T00:00:00Z",
    }


def _request(
    server: Any,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    # 修改凭据会依次校验旧密码并计算新scrypt哈希；较慢的Windows机器可能超过3秒。
    connection = http.client.HTTPConnection(*server.server_address, timeout=10)
    encoded = json.dumps(body).encode() if body is not None else None
    request_headers = dict(headers or {})
    if encoded is not None:
        request_headers["Content-Type"] = "application/json"
        request_headers["Content-Length"] = str(len(encoded))
    connection.request(method, path, body=encoded, headers=request_headers)
    response = connection.getresponse()
    data = response.read()
    result = response.status, {key: value for key, value in response.getheaders()}, data
    connection.close()
    return result


def test_dashboard_requires_launch_session_and_same_origin_for_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure(monkeypatch)
    static_root = tmp_path / "dist"
    static_root.mkdir()
    (static_root / "index.html").write_text("<main>dashboard</main>", encoding="utf-8")

    adjustments: list[tuple[str, int, bool]] = []
    edits: list[tuple[str, dict[str, Any], bool]] = []
    evidence: list[tuple[str, dict[str, Any], list[dict[str, Any]], bytes | None]] = []
    product_evidence: list[tuple[str, dict[str, Any], bytes, str, str]] = []
    evidence_path = tmp_path / "客服截图.png"
    evidence_path.write_bytes(b"stored screenshot")

    def adjust(filament_id: str, delta: int, approved: bool) -> dict[str, Any]:
        adjustments.append((filament_id, delta, approved))
        return {"after": {**_row(), "stock_spools": 7}}

    def update_filament(
        filament_id: str, fields: dict[str, Any], approved: bool
    ) -> dict[str, Any]:
        edits.append((filament_id, fields, approved))
        return {"after": {**_row(), **fields}}

    def add_evidence(
        filament_id: str,
        source: dict[str, Any],
        claims: list[dict[str, Any]],
        file_bytes: bytes | None,
        _filename: str | None,
        _media_type: str | None,
        _approved: bool,
    ) -> dict[str, Any]:
        evidence.append((filament_id, source, claims, file_bytes))
        return {"source_id": "22222222-2222-4222-8222-222222222222", "inserted_claims": len(claims)}

    def add_product_evidence(
        product_id: str,
        source: dict[str, Any],
        file_bytes: bytes,
        filename: str,
        media_type: str,
        _approved: bool,
    ) -> dict[str, Any]:
        product_evidence.append((product_id, source, file_bytes, filename, media_type))
        return {
            "source_id": "44444444-4444-4444-8444-444444444444",
            "inserted_claims": 0,
            "deduplicated_source": False,
            "processing_status": "pending_manual_review",
        }

    service = InventoryDashboardService(
        list_records=lambda: [_row()],
        adjust=adjust,
        set_values=lambda *_args: {},
        update_filament=update_filament,
        add_evidence=add_evidence,
        add_product_evidence=add_product_evidence,
        get_evidence_file=lambda _source_id: (evidence_path, "image/png", "客服截图.png"),
    )
    token = "test-session-token"
    server = create_dashboard_server(
        DashboardConfig(port=0, open_browser=False, static_root=static_root),
        service=service,
        session_token=token,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _, _ = _request(server, "GET", "/health", headers={"Host": "malicious.example"})
        assert status == 403

        status, _, _ = _request(server, "GET", "/api/filaments")
        assert status == 401

        status, headers, _ = _request(server, "GET", f"/launch/{token}")
        assert status == 303
        cookie = headers["Set-Cookie"].split(";", 1)[0]

        status, headers, body = _request(
            server, "GET", "/api/filaments", headers={"Cookie": cookie}
        )
        assert status == 200
        assert headers["X-Frame-Options"] == "DENY"
        payload = json.loads(body)
        assert payload["data"]["summary"] == {
            "filament_count": 1,
            "stock_spools": 6,
            "opened_spool_count": 0,
            "stock_equivalent": 6.0,
            "product_series_count": 1,
            "color_variant_count": 1,
            "unclassified_color_count": 0,
            "stock_total_kg": 6.0,
            "low_stock_count": 0,
            "replenishment_spools": 0,
            "needs_attention_count": 0,
        }

        status, _, _ = _request(
            server,
            "POST",
            "/api/inventory/adjust",
            body={"filament_id": FILAMENT_ID, "delta": 1},
            headers={"Cookie": cookie, "Origin": "https://malicious.example"},
        )
        assert status == 403

        status, _, body = _request(
            server,
            "POST",
            "/api/inventory/adjust",
            body={"filament_id": FILAMENT_ID, "delta": 1},
            headers={"Cookie": cookie, "Origin": server.origin},
        )
        assert status == 200
        assert json.loads(body)["data"]["after"]["stock_spools"] == 7
        assert adjustments == [(FILAMENT_ID, 1, True)]

        status, _, body = _request(
            server,
            "POST",
            "/api/filaments/update",
            body={"filament_id": FILAMENT_ID, "fields": {"color": "透明"}},
            headers={"Cookie": cookie, "Origin": server.origin},
        )
        assert status == 200
        assert json.loads(body)["data"]["after"]["color"] == "透明"
        assert edits == [(FILAMENT_ID, {"color": "透明"}, True)]

        encoded = base64.b64encode(b"screenshot").decode()
        status, _, body = _request(
            server,
            "POST",
            "/api/filaments/evidence",
            body={
                "filament_id": FILAMENT_ID,
                "source": {
                    "kind": "customer_service",
                    "title": "客服回复",
                    "user_decision": "use_default_profile",
                    "quote": "按照默认参数打就行",
                },
                "claims": [{"key": "nozzle_temperature", "value": "230-260", "unit": "°C"}],
                "file": {"filename": "reply.png", "media_type": "image/png", "data_base64": encoded},
            },
            headers={"Cookie": cookie, "Origin": server.origin},
        )
        assert status == 201
        assert evidence[0][0] == FILAMENT_ID
        assert evidence[0][3] == b"screenshot"

        image = b"\x89PNG\r\n\x1a\nraw screenshot"
        status, _, body = _request(
            server,
            "POST",
            "/api/products/evidence",
            body={
                "product_id": PRODUCT_ID,
                "source": {"kind": "seller", "title": "商品页截图"},
                "file": {
                    "filename": "product.png",
                    "media_type": "image/png",
                    "data_base64": base64.b64encode(image).decode(),
                },
            },
            headers={"Cookie": cookie, "Origin": server.origin},
        )
        assert status == 201
        assert json.loads(body)["data"]["processing_status"] == "pending_manual_review"
        assert product_evidence == [
            (PRODUCT_ID, {"kind": "seller", "title": "商品页截图"}, image, "product.png", "image/png")
        ]

        status, _, body = _request(
            server,
            "POST",
            "/api/products/evidence",
            body={
                "product_id": PRODUCT_ID,
                "source": {"kind": "seller"},
                "file": {
                    "filename": "fake.png",
                    "media_type": "image/png",
                    "data_base64": base64.b64encode(b"not-an-image").decode(),
                },
            },
            headers={"Cookie": cookie, "Origin": server.origin},
        )
        assert status == 422
        assert json.loads(body)["error"]["code"] == "invalid_input"

        status, _, body = _request(
            server,
            "GET",
            "/api/ai/inventory",
            headers={"Cookie": cookie},
        )
        assert status == 200
        ai_payload = json.loads(body)["data"]
        assert ai_payload["v"] == 1
        assert ai_payload["summary"]["series"] == 1

        status, _, body = _request(server, "GET", "/llms.txt")
        assert status == 200
        assert b"/api/ai/inventory" in body

        status, _, body = _request(server, "GET", "/openapi.json")
        assert status == 200
        assert json.loads(body)["openapi"] == "3.1.0"

        status, headers, body = _request(
            server,
            "GET",
            "/api/evidence/22222222-2222-4222-8222-222222222222/file",
            headers={"Cookie": cookie},
        )
        assert status == 200
        assert body == b"stored screenshot"
        assert "filename*=" in headers["Content-Disposition"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    assert token not in capsys.readouterr().out


def test_dashboard_validates_inventory_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch)
    static_root = tmp_path / "dist"
    static_root.mkdir()
    (static_root / "index.html").write_text("ok", encoding="utf-8")
    server = create_dashboard_server(
        DashboardConfig(port=0, open_browser=False, static_root=static_root),
        service=InventoryDashboardService(list_records=lambda: []),
        session_token="test-token",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        _, headers, _ = _request(server, "GET", "/launch/test-token")
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        status, _, body = _request(
            server,
            "POST",
            "/api/inventory/adjust",
            body={"filament_id": FILAMENT_ID, "delta": 0},
            headers={"Cookie": cookie, "Origin": server.origin},
        )
        assert status == 422
        assert json.loads(body)["error"]["code"] == "invalid_input"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_dashboard_recognize_image_requires_session_and_returns_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch)
    static_root = tmp_path / "dist"
    static_root.mkdir()
    (static_root / "index.html").write_text("ok", encoding="utf-8")
    recognized = {"raw_text": "PETG", "claims": [], "suggested": {"material_type": "PETG"}, "warnings": [], "engine": "test"}
    server = create_dashboard_server(
        DashboardConfig(port=0, open_browser=False, static_root=static_root),
        service=InventoryDashboardService(
            list_records=lambda: [],
            recognize_image=lambda _bytes, _filename, _media_type: recognized,
        ),
        session_token="test-token",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _, _ = _request(server, "POST", "/api/evidence/recognize", body={"file": {"data_base64": "aW1hZ2U=", "filename": "a.png", "media_type": "image/png"}}, headers={"Origin": server.origin})
        assert status == 401
        _, headers, _ = _request(server, "GET", "/launch/test-token")
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        status, _, body = _request(
            server,
            "POST",
            "/api/evidence/recognize",
            body={"file": {"data_base64": "aW1hZ2U=", "filename": "a.png", "media_type": "image/png"}},
            headers={"Cookie": cookie, "Origin": server.origin},
        )
        assert status == 200
        assert json.loads(body)["data"] == recognized
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_password_dashboard_login_settings_and_session_revocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch)
    static_root = tmp_path / "dist"
    static_root.mkdir()
    (static_root / "index.html").write_text("dashboard", encoding="utf-8")
    auth_file = tmp_path / "auth.json"
    CredentialStore(auth_file).initialize("admin", "initial-password")
    origin = "https://3d.example.com"
    server = create_dashboard_server(
        DashboardConfig(
            port=0,
            open_browser=False,
            static_root=static_root,
            public_origin=origin,
            auth_file=auth_file,
        ),
        service=InventoryDashboardService(list_records=lambda: [_row()]),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _, _ = _request(server, "GET", "/")
        assert status == 200
        status, _, _ = _request(server, "GET", "/api/filaments")
        assert status == 401

        status, _, _ = _request(
            server,
            "POST",
            "/api/auth/login",
            body={"username": "admin", "password": "wrong-password"},
            headers={"Origin": origin},
        )
        assert status == 401

        status, headers, body = _request(
            server,
            "POST",
            "/api/auth/login",
            body={"username": "admin", "password": "initial-password"},
            headers={"Origin": origin},
        )
        assert status == 200
        assert json.loads(body)["data"]["username"] == "admin"
        assert "Secure" in headers["Set-Cookie"]
        cookie = headers["Set-Cookie"].split(";", 1)[0]

        status, _, _ = _request(
            server, "GET", "/api/filaments", headers={"Cookie": cookie}
        )
        assert status == 200

        status, headers, _ = _request(
            server,
            "POST",
            "/api/auth/settings",
            body={
                "username": "operator",
                "current_password": "initial-password",
                "new_password": "replacement-password",
            },
            headers={"Cookie": cookie, "Origin": origin},
        )
        assert status == 200
        assert "Max-Age=0" in headers["Set-Cookie"]

        status, _, _ = _request(
            server, "GET", "/api/filaments", headers={"Cookie": cookie}
        )
        assert status == 401
        assert CredentialStore(auth_file).verify("operator", "replacement-password")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_password_dashboard_rejects_non_https_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch)
    static_root = tmp_path / "dist"
    static_root.mkdir()
    (static_root / "index.html").write_text("dashboard", encoding="utf-8")
    auth_file = tmp_path / "auth.json"
    CredentialStore(auth_file).initialize("admin", "initial-password")
    with pytest.raises(Exception, match="HTTPS"):
        create_dashboard_server(
            DashboardConfig(
                port=0,
                open_browser=False,
                static_root=static_root,
                public_origin="http://3d.example.com",
                auth_file=auth_file,
            )
        )
