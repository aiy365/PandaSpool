from __future__ import annotations

import json
import logging
import mimetypes
import shutil
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from pypdf import PdfReader

from .errors import InputError
from .util import canonical_json, fingerprint, safe_slug, sha256_file


IDENTITY_FIELDS = (
    "brand",
    "manufacturer",
    "seller",
    "product_line",
    "material_type",
    "variant",
    "color",
    "diameter_mm",
    "sku",
    "barcode",
    "region",
)


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"无法读取JSON：{path}") from exc


def load_identity(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    data = _read_json(source)
    if not isinstance(data, dict):
        raise InputError("耗材身份文件必须是JSON对象。")
    identity = {field: data.get(field) for field in IDENTITY_FIELDS}
    required = ["brand", "product_line", "material_type", "region"]
    missing = [field for field in required if not str(identity.get(field) or "").strip()]
    if missing:
        raise InputError(f"耗材身份缺少字段：{missing}")
    try:
        diameter = float(identity.get("diameter_mm") or 1.75)
    except (TypeError, ValueError) as exc:
        raise InputError("diameter_mm 必须是正数。") from exc
    if diameter <= 0:
        raise InputError("diameter_mm 必须是正数。")
    identity["diameter_mm"] = diameter
    for key, value in list(identity.items()):
        if isinstance(value, str):
            identity[key] = value.strip() or None
    return identity


def load_claims(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    source = Path(path).expanduser().resolve()
    data = _read_json(source)
    if not isinstance(data, list):
        raise InputError("声明文件必须是JSON数组。")
    claims: list[dict[str, Any]] = []
    for index, raw in enumerate(data, start=1):
        if not isinstance(raw, dict) or not raw.get("key") or "value" not in raw:
            raise InputError(f"第{index}条声明必须包含 key 和 value。")
        claim = {
            "key": str(raw["key"]).strip(),
            "value": raw["value"],
            "unit": raw.get("unit"),
            "source": raw.get("source"),
            "location": raw.get("location"),
            "authority": raw.get("authority", "unknown"),
            "scope": raw.get("scope") or {},
            "review_status": raw.get("review_status", "pending"),
            "notes": raw.get("notes"),
        }
        if claim["review_status"] not in {"pending", "approved", "rejected"}:
            raise InputError(f"第{index}条声明的 review_status 无效。")
        claims.append(claim)
    return claims


def load_source_metadata(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    source = Path(path).expanduser().resolve()
    data = _read_json(source)
    if not isinstance(data, dict):
        raise InputError("来源元数据必须是以文件名或URL为键的JSON对象。")
    allowed_authorities = {
        "unknown",
        "manufacturer_page",
        "manufacturer_tds",
        "manufacturer_profile",
        "reseller",
        "bambu_system",
        "user_profile",
    }
    result: dict[str, dict[str, Any]] = {}
    for key, raw in data.items():
        if not isinstance(raw, dict):
            raise InputError(f"来源元数据 {key!r} 必须是JSON对象。")
        authority = str(raw.get("authority") or "unknown")
        if authority not in allowed_authorities:
            raise InputError(f"来源元数据 {key!r} 的 authority 无效。")
        result[str(key)] = {
            "authority": authority,
            "source_organization": raw.get("source_organization"),
            "document_version": raw.get("document_version"),
            "region": raw.get("region"),
            "notes": raw.get("notes"),
        }
    return result


def _download(url: str, destination: Path) -> tuple[str | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PrintPilot-Material-Lab/0.1 (+local evidence archive)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            content_type = response.headers.get_content_type()
            content_disposition = response.headers.get("Content-Disposition")
            destination.write_bytes(response.read())
            return content_type, content_disposition
    except Exception as exc:  # urllib exposes several transport-specific subclasses
        raise InputError(f"无法下载来源：{url}") from exc


def _extract_pdf(path: Path) -> str:
    logger = logging.getLogger("pypdf")
    previous_level = logger.level
    logger.setLevel(logging.ERROR)
    try:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise InputError(f"无法解析PDF：{path}") from exc
    finally:
        logger.setLevel(previous_level)
    return "\n\n".join(f"--- Page {index} ---\n{text}" for index, text in enumerate(pages, 1))


def _extract_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    parser = _VisibleTextParser()
    parser.feed(raw)
    return "\n".join(parser.parts)


def _extract_bbsflmt(path: Path) -> str:
    chunks: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist()):
                if name.lower().endswith(".json"):
                    raw = archive.read(name).decode("utf-8")
                    data = json.loads(raw)
                    chunks.append(f"--- {name} ---\n{json.dumps(data, ensure_ascii=False, indent=2)}")
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"无法解析BBSFLMT：{path}") from exc
    return "\n\n".join(chunks)


def extract_text(path: Path, media_type: str | None = None) -> tuple[str, str | None]:
    suffix = path.suffix.lower()
    if suffix == ".pdf" or media_type == "application/pdf":
        return "pdf", _extract_pdf(path)
    if suffix == ".bbsflmt":
        return "bbsflmt", _extract_bbsflmt(path)
    if suffix == ".json" or media_type == "application/json":
        data = _read_json(path)
        return "json", json.dumps(data, ensure_ascii=False, indent=2)
    if suffix in {".html", ".htm"} or media_type == "text/html":
        return "webpage", _extract_html(path)
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return "image", None
    return "file", None


def _source_filename(source: str, index: int) -> str:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme in {"http", "https"}:
        leaf = Path(parsed.path).name or parsed.netloc
        suffix = Path(leaf).suffix or ".html"
        return f"{index:02d}-{safe_slug(Path(leaf).stem or parsed.netloc)}{suffix}"
    path = Path(source)
    return f"{index:02d}-{safe_slug(path.stem)}{path.suffix.lower()}"


def _resolve_claim_sources(
    claims: list[dict[str, Any]], sources: list[dict[str, Any]], identity: dict[str, Any]
) -> list[dict[str, Any]]:
    aliases: dict[str, str] = {}
    sha_by_id: dict[str, str] = {}
    for source in sources:
        source_id = source["source_ref"]
        sha_by_id[source_id] = source["sha256"]
        aliases[source_id] = source_id
        aliases[source["original"]] = source_id
        aliases[Path(source["original"]).name] = source_id
        aliases[Path(source["staged_path"]).name] = source_id
        for alias in source.get("aliases", []):
            aliases[str(alias)] = source_id
            aliases[Path(str(alias)).name] = source_id

    resolved: list[dict[str, Any]] = []
    for claim in claims:
        requested = claim.get("source")
        if not requested:
            raise InputError(f"声明 {claim['key']!r} 没有指定 source。")
        source_id = aliases.get(str(requested))
        if not source_id:
            raise InputError(f"声明 {claim['key']!r} 引用了未知来源：{requested}")
        scope = {"region": identity["region"], **dict(claim.get("scope") or {})}
        enriched = {
            **claim,
            "source_ref": source_id,
            "scope": scope,
        }
        enriched.pop("source", None)
        enriched["fingerprint"] = fingerprint(
            {
                "identity": identity,
                "source_sha256": sha_by_id[source_id],
                "key": enriched["key"],
                "value": enriched["value"],
                "unit": enriched["unit"],
                "scope": scope,
                "location": enriched["location"],
            }
        )
        resolved.append(enriched)
    return resolved


def detect_conflicts(claims: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        if claim.get("review_status") == "rejected":
            continue
        grouped.setdefault(str(claim["key"]), []).append(claim)

    conflicts: list[dict[str, Any]] = []
    for key, items in sorted(grouped.items()):
        distinct: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            signature = canonical_json({"value": item["value"], "unit": item.get("unit")})
            distinct.setdefault(signature, []).append(item)
        if len(distinct) <= 1:
            continue
        conflicts.append(
            {
                "key": key,
                "values": [
                    {
                        "value": group[0]["value"],
                        "unit": group[0].get("unit"),
                        "sources": sorted({item["source_ref"] for item in group}),
                        "regions": sorted(
                            {
                                str(item.get("scope", {}).get("region"))
                                for item in group
                                if item.get("scope", {}).get("region")
                            }
                        ),
                    }
                    for group in distinct.values()
                ],
            }
        )
    return conflicts


def _write_review(manifest: dict[str, Any], path: Path) -> None:
    identity = manifest["filament"]
    lines = [
        f"# {identity['brand']} {identity['product_line']} 建档审核",
        "",
        f"- 材料：{identity['material_type']}",
        f"- 地区：{identity['region']}",
        f"- SKU：{identity.get('sku') or '未提供'}",
        f"- 条码：{identity.get('barcode') or '未提供'}",
        f"- 来源：{len(manifest['sources'])}",
        f"- 参数声明：{len(manifest['claims'])}",
        f"- 冲突：{len(manifest['conflicts'])}",
        "",
        "## 冲突",
        "",
    ]
    if not manifest["conflicts"]:
        lines.append("未发现冲突。")
    else:
        for conflict in manifest["conflicts"]:
            lines.append(f"### {conflict['key']}")
            lines.append("")
            for value in conflict["values"]:
                lines.append(
                    f"- `{value['value']}` {value.get('unit') or ''}；地区："
                    f"{', '.join(value['regions']) or '未标注'}；来源：{', '.join(value['sources'])}"
                )
            lines.append("")
    lines.extend(["## 来源", ""])
    for source in manifest["sources"]:
        lines.append(
            f"- `{source['source_ref']}` {source['kind']}：{source['original']} "
            f"(`{source['sha256'][:12]}`)"
        )
    lines.extend(["", "## 审核门槛", ""])
    pending = sum(1 for claim in manifest["claims"] if claim["review_status"] == "pending")
    lines.append(f"- 待审核声明：{pending}")
    lines.append("- commit 前必须有 SKU 或条码，且调用者明确传入 `--approved`。")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def stage_material(
    identity_file: str | Path,
    source_values: Iterable[str],
    claims_file: str | Path | None,
    output_root: str | Path,
    source_metadata_file: str | Path | None = None,
) -> Path:
    identity = load_identity(identity_file)
    source_inputs = [str(value) for value in source_values]
    if not source_inputs:
        raise InputError("至少需要一个来源文件或URL。")
    source_metadata = load_source_metadata(source_metadata_file)

    run_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    run_dir = Path(output_root).expanduser().resolve() / run_id
    evidence_dir = run_dir / "evidence"
    text_dir = run_dir / "extracted"
    evidence_dir.mkdir(parents=True, exist_ok=False)
    text_dir.mkdir()

    sources: list[dict[str, Any]] = []
    source_by_hash: dict[str, dict[str, Any]] = {}
    for index, source_value in enumerate(source_inputs, start=1):
        filename = _source_filename(source_value, index)
        metadata = source_metadata.get(source_value) or source_metadata.get(
            Path(source_value).name
        ) or {}
        staged = evidence_dir / filename
        parsed = urllib.parse.urlparse(source_value)
        media_type: str | None = None
        if parsed.scheme in {"http", "https"}:
            media_type, _ = _download(source_value, staged)
            if media_type == "application/pdf" and staged.suffix.lower() != ".pdf":
                renamed = staged.with_suffix(".pdf")
                staged.rename(renamed)
                staged = renamed
        else:
            original = Path(source_value).expanduser().resolve()
            if not original.is_file():
                raise InputError(f"来源文件不存在：{original}")
            shutil.copy2(original, staged)
            media_type = mimetypes.guess_type(original.name)[0]
        checksum = sha256_file(staged)
        if checksum in source_by_hash:
            source_by_hash[checksum].setdefault("aliases", []).append(source_value)
            staged.unlink()
            continue
        kind, extracted = extract_text(staged, media_type)
        extracted_path: str | None = None
        if extracted is not None:
            text_path = text_dir / f"{staged.stem}.txt"
            text_path.write_text(extracted, encoding="utf-8")
            extracted_path = str(text_path.relative_to(run_dir))
        source_ref = f"source-{len(sources) + 1:02d}"
        source_record = {
                "source_ref": source_ref,
                "kind": kind,
                "original": source_value,
                "aliases": [],
                "media_type": media_type,
                "staged_path": str(staged.relative_to(run_dir)),
                "extracted_text_path": extracted_path,
                "sha256": checksum,
                "size_bytes": staged.stat().st_size,
                "region": metadata.get("region") or identity["region"],
                "authority": metadata.get("authority", "unknown"),
                "source_organization": metadata.get("source_organization"),
                "document_version": metadata.get("document_version"),
                "notes": metadata.get("notes"),
                "retrieved_at": datetime.now(UTC).isoformat(),
            }
        sources.append(source_record)
        source_by_hash[checksum] = source_record

    claims = _resolve_claim_sources(load_claims(claims_file), sources, identity)
    manifest = {
        "schema_version": 1,
        "status": "staged",
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "filament": identity,
        "sources": sources,
        "claims": claims,
        "conflicts": detect_conflicts(claims),
    }
    manifest["manifest_fingerprint"] = fingerprint(manifest)
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_review(manifest, run_dir / "review.md")
    return manifest_path


def load_manifest(path: str | Path) -> tuple[Path, dict[str, Any]]:
    manifest_path = Path(path).expanduser().resolve()
    data = _read_json(manifest_path)
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise InputError(f"不是受支持的建档清单：{manifest_path}")
    return manifest_path, data
