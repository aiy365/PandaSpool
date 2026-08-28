from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .calibration import record_calibration
from .dashboard_server import initialize_dashboard_auth, run_dashboard
from .errors import MaterialLabError
from .profiles import build_profile, smoke_slice
from .staging import stage_material
from .local_store import (
    backup_local_data,
    adjust_inventory,
    commit_calibration_record,
    commit_manifest,
    commit_profile_report,
    local_health,
    list_inventory,
    import_inventory_rows,
    restore_local_data,
    set_inventory,
)
from .inventory_import import load_inventory_workbook
from .material_domain import compact_inventory_payload
from .preset_evaluation import evaluate_preset_files
from .local_store import add_preset_evaluation


def _emit_error(exc: MaterialLabError) -> None:
    print(
        json.dumps({"event": "error", "code": exc.code, "message": str(exc)}, ensure_ascii=False),
        file=sys.stderr,
    )


def _stage(args: argparse.Namespace) -> int:
    path = stage_material(
        args.identity,
        args.source,
        args.claims,
        args.output_dir,
        source_metadata_file=args.source_metadata,
    )
    print(path)
    return 0


def _commit(args: argparse.Namespace) -> int:
    print(json.dumps(commit_manifest(args.manifest, args.approved), ensure_ascii=False, indent=2))
    return 0


def _profile_build(args: argparse.Namespace) -> int:
    path = build_profile(
        args.manifest,
        args.output_dir,
        nozzle_mm=args.nozzle,
        bambu_home=args.bambu_home,
        studio_version=args.studio_version,
        plate_policy=args.plate,
    )
    print(path)
    return 0


def _profile_evaluate(args: argparse.Namespace) -> int:
    result = evaluate_preset_files(
        args.input,
        authority=args.authority,
        provenance=args.provenance,
    )
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output + "\n", encoding="utf-8")
        print(destination)
    else:
        print(output)
    return 0


def _profile_evaluation_commit(args: argparse.Namespace) -> int:
    report = evaluate_preset_files(
        [args.input],
        authority=args.authority,
        provenance=args.provenance,
    )
    profiles = report["files"][0]["profiles"]
    if len(profiles) != 1:
        raise MaterialLabError("目标预设必须恰好包含一个A1 0.4 mm配置。")
    path = Path(args.input).expanduser().resolve()
    result = add_preset_evaluation(
        args.product_id,
        args.filament_id,
        profiles[0],
        path.read_bytes(),
        path.name,
        args.approved,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _profile_commit(args: argparse.Namespace) -> int:
    result = commit_profile_report(args.report, args.filament_id, args.approved)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _slice_smoke(args: argparse.Namespace) -> int:
    result = smoke_slice(
        args.profile,
        args.input,
        args.output_dir,
        bambu_home=args.bambu_home,
        plate=args.plate,
        timeout_seconds=args.timeout,
        report_file=args.report,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _calibration_record(args: argparse.Namespace) -> int:
    path = record_calibration(args.manifest, args.input, args.output_dir)
    print(path)
    return 0


def _calibration_commit(args: argparse.Namespace) -> int:
    result = commit_calibration_record(
        args.record, args.filament_id, args.profile_build_id, args.approved
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _inventory_list(args: argparse.Namespace) -> int:
    print(json.dumps(list_inventory(), ensure_ascii=False, indent=2))
    return 0


def _inventory_set(args: argparse.Namespace) -> int:
    result = set_inventory(
        args.filament_id,
        args.spools,
        args.spool_weight_g,
        args.low_stock_threshold,
        args.approved,
        args.opened_percent,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _inventory_adjust(args: argparse.Namespace) -> int:
    result = adjust_inventory(args.filament_id, args.delta, args.approved)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _inventory_import_xlsx(args: argparse.Namespace) -> int:
    rows = load_inventory_workbook(args.workbook)
    preview = {
        "rows": len(rows),
        "product_series": len({(row["brand"], row["product_line"], row["material_type"]) for row in rows}),
        "colors": len({row["color"] for row in rows}),
        "stock_equivalent": round(
            sum(row["stock_spools"] + row["opened_remaining_percent"] / 100 for row in rows),
            2,
        ),
    }
    if not args.approved:
        print(json.dumps({"preview": preview, "sample": rows[:5]}, ensure_ascii=False, indent=2))
        return 0
    result = import_inventory_rows(rows, True)
    print(json.dumps({"preview": preview, "result": result}, ensure_ascii=False, indent=2))
    return 0


def _inventory_ai_export(args: argparse.Namespace) -> int:
    from .local_store import list_dashboard_filaments

    print(
        json.dumps(
            compact_inventory_payload(list_dashboard_filaments()),
            ensure_ascii=False,
            separators=(",", ":") if args.compact else None,
            indent=None if args.compact else 2,
        )
    )
    return 0


def _database_init(args: argparse.Namespace) -> int:
    print(json.dumps(local_health(), ensure_ascii=False, indent=2))
    return 0


def _backup(args: argparse.Namespace) -> int:
    print(json.dumps(backup_local_data(args.output_dir, args.keep), ensure_ascii=False, indent=2))
    return 0


def _restore(args: argparse.Namespace) -> int:
    print(json.dumps(restore_local_data(args.archive, args.approved), ensure_ascii=False, indent=2))
    return 0


def _dashboard(args: argparse.Namespace) -> int:
    return run_dashboard(
        port=args.port,
        open_browser=not args.no_browser,
        public_origin=args.public_origin,
        auth_file=args.auth_file,
    )


def _dashboard_auth_init(args: argparse.Namespace) -> int:
    initialize_dashboard_auth(args.auth_file, args.username, args.password_file)
    print(json.dumps({"status": "initialized", "auth_file": args.auth_file}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="printpilot-material",
        description="把供应商资料建成可追溯耗材档案，生成A1 0.4预设并维护库存盘点。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage = subparsers.add_parser("stage", help="本地提取证据并生成待审核清单")
    stage.add_argument("--identity", required=True, help="耗材身份JSON")
    stage.add_argument("--claims", help="逐字段参数声明JSON")
    stage.add_argument("--source", action="append", required=True, help="本地文件或URL，可重复")
    stage.add_argument("--source-metadata", help="逐来源身份、地区和版本JSON")
    stage.add_argument("--output-dir", default="staging", help="本地建档目录")
    stage.set_defaults(func=_stage)

    commit = subparsers.add_parser("commit", help="确认后写入SQLite私有档案")
    commit.add_argument("manifest", help="stage产生的manifest.json")
    commit.add_argument("--approved", action="store_true", help="确认资料允许上传并正式建档")
    commit.set_defaults(func=_commit)

    profile = subparsers.add_parser("profile-build", help="生成或推荐A1耗材预设")
    profile.add_argument("manifest", help="stage产生的manifest.json")
    profile.add_argument("--nozzle", type=float, default=0.4, help="v0.1只支持0.4")
    profile.add_argument("--output-dir", default="runs/profiles")
    profile.add_argument("--bambu-home")
    profile.add_argument("--studio-version", default="02.08.01.55")
    profile.add_argument(
        "--plate",
        choices=("glacier", "baseline"),
        default="glacier",
        help="低温板策略；默认使用BIQU Glacier，baseline保持拓竹基线",
    )
    profile.set_defaults(func=_profile_build)

    evaluate = subparsers.add_parser(
        "profile-evaluate",
        help="解析JSON/BBSFLMT中的厂家预设字段与作用域，不写数据库",
    )
    evaluate.add_argument("--input", action="append", required=True, help="预设文件，可重复")
    evaluate.add_argument(
        "--authority",
        choices=("bambu_system", "manufacturer_profile", "user_profile"),
        default="user_profile",
    )
    evaluate.add_argument("--provenance", help="外部来源链说明")
    evaluate.add_argument("--output", help="将评测JSON写入指定文件")
    evaluate.set_defaults(func=_profile_evaluate)

    evaluation_commit = subparsers.add_parser(
        "profile-evaluation-commit",
        help="将一份已解析的厂家预设绑定到产品或指定颜色",
    )
    evaluation_commit.add_argument("--input", required=True, help="JSON或BBSFLMT预设")
    evaluation_commit.add_argument("--product-id", required=True)
    evaluation_commit.add_argument("--filament-id", help="颜色专用预设必须提供")
    evaluation_commit.add_argument(
        "--authority",
        choices=("bambu_system", "manufacturer_profile", "user_profile"),
        default="manufacturer_profile",
    )
    evaluation_commit.add_argument("--provenance", required=True, help="预设来源链说明")
    evaluation_commit.add_argument("--approved", action="store_true")
    evaluation_commit.set_defaults(func=_profile_evaluation_commit)

    profile_commit = subparsers.add_parser("profile-commit", help="把预设报告和产物写入本地私有档案")
    profile_commit.add_argument("report")
    profile_commit.add_argument("--filament-id", required=True)
    profile_commit.add_argument("--approved", action="store_true")
    profile_commit.set_defaults(func=_profile_commit)

    smoke = subparsers.add_parser("slice-smoke", help="用Bambu Studio真实切片验证预设")
    smoke.add_argument("--profile", required=True, help="完整耗材JSON")
    smoke.add_argument("--input", required=True, help="单材料A1 0.4三维制造格式项目")
    smoke.add_argument("--output-dir", default="runs/smoke")
    smoke.add_argument("--bambu-home")
    smoke.add_argument("--plate", type=int, default=1)
    smoke.add_argument("--timeout", type=int, default=180)
    smoke.add_argument("--report", help="切片成功后回写profile-report.json")
    smoke.set_defaults(func=_slice_smoke)

    calibration = subparsers.add_parser("calibration-record", help="本地记录独立校准结果")
    calibration.add_argument("manifest")
    calibration.add_argument("--input", required=True, help="校准JSON")
    calibration.add_argument("--output-dir", default="runs/calibrations")
    calibration.set_defaults(func=_calibration_record)

    calibration_commit = subparsers.add_parser("calibration-commit", help="把校准记录写入本地私有档案")
    calibration_commit.add_argument("record")
    calibration_commit.add_argument("--filament-id", required=True)
    calibration_commit.add_argument("--profile-build-id")
    calibration_commit.add_argument("--approved", action="store_true")
    calibration_commit.set_defaults(func=_calibration_commit)

    inventory_list = subparsers.add_parser("inventory-list", help="查看当前耗材库存盘点表")
    inventory_list.set_defaults(func=_inventory_list)

    inventory_set = subparsers.add_parser("inventory-set", help="把耗材库存设置为盘点后的准确卷数")
    inventory_set.add_argument("--filament-id", required=True)
    inventory_set.add_argument("--spools", required=True, type=int)
    inventory_set.add_argument("--opened-percent", type=int, choices=range(0, 101), metavar="0..100")
    inventory_set.add_argument("--spool-weight-g", type=int)
    inventory_set.add_argument("--low-stock-threshold", type=int)
    inventory_set.add_argument("--approved", action="store_true")
    inventory_set.set_defaults(func=_inventory_set)

    inventory_adjust = subparsers.add_parser("inventory-adjust", help="按正负卷数增减当前库存")
    inventory_adjust.add_argument("--filament-id", required=True)
    inventory_adjust.add_argument("--delta", required=True, type=int)
    inventory_adjust.add_argument("--approved", action="store_true")
    inventory_adjust.set_defaults(func=_inventory_adjust)

    inventory_import = subparsers.add_parser(
        "inventory-import-xlsx",
        help="把颜色×产品库存盘点表导入为未开封卷和一卷在用余量",
    )
    inventory_import.add_argument("workbook", help=".xlsx库存盘点工作簿")
    inventory_import.add_argument(
        "--approved", action="store_true", help="确认预览后写入SQLite"
    )
    inventory_import.set_defaults(func=_inventory_import_xlsx)

    inventory_ai = subparsers.add_parser(
        "inventory-ai-export", help="输出适合AI读取的紧凑只读库存与评测包"
    )
    inventory_ai.add_argument(
        "--pretty", action="store_false", dest="compact", help="使用缩进格式便于人工查看"
    )
    inventory_ai.set_defaults(func=_inventory_ai_export, compact=True)

    database_init = subparsers.add_parser("database-init", help="初始化并检查SQLite数据库")
    database_init.set_defaults(func=_database_init)

    backup = subparsers.add_parser("backup", help="生成SQLite与私有文件的完整本地备份")
    backup.add_argument("--output-dir", default="backups")
    backup.add_argument("--keep", type=int, help="仅保留最近N份同类备份")
    backup.set_defaults(func=_backup)

    restore = subparsers.add_parser("restore", help="从完整备份恢复SQLite与私有文件")
    restore.add_argument("archive")
    restore.add_argument("--approved", action="store_true", help="确认覆盖当前本地数据")
    restore.set_defaults(func=_restore)

    dashboard = subparsers.add_parser("dashboard", help="启动本地耗材看板")
    dashboard.add_argument("--port", type=int, default=8765)
    dashboard.add_argument("--no-browser", action="store_true")
    dashboard.add_argument("--public-origin", help="生产模式的HTTPS访问地址")
    dashboard.add_argument("--auth-file", help="启用密码鉴权时的凭据文件")
    dashboard.set_defaults(func=_dashboard)

    auth_init = subparsers.add_parser("dashboard-auth-init", help="初始化生产看板管理员")
    auth_init.add_argument("--auth-file", required=True)
    auth_init.add_argument("--username", required=True)
    auth_init.add_argument("--password-file", required=True)
    auth_init.set_defaults(func=_dashboard_auth_init)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except MaterialLabError as exc:
        _emit_error(exc)
        return 1
    except KeyboardInterrupt:
        print('{"event":"cancelled"}', file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
