from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path


MIGRATIONS = (
    Path(__file__).parents[1]
    / "src"
    / "printpilot_material_lab"
    / "sqlite_migrations"
)


def test_sqlite_migrations_build_complete_constrained_schema(tmp_path: Path) -> None:
    database = tmp_path / "schema.sqlite3"
    with sqlite3.connect(database) as connection:
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            connection.executescript(migration.read_text(encoding="utf-8"))
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "app_metadata",
            "material_products",
            "filaments",
            "sources",
            "claims",
            "preset_evaluations",
            "profile_builds",
            "calibration_runs",
            "inventory_movements",
        }.issubset(tables)
        filament_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(filaments)")
        }
        assert "product_id" in filament_columns
        assert "brand" not in filament_columns
        assert "material_type" not in filament_columns
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='view' AND name='filament_inventory_view'"
        ).fetchone()
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        sql = "\n".join(path.read_text(encoding="utf-8").lower() for path in MIGRATIONS.glob("*.sql"))
        assert "after_spools = before_spools + delta" in sql
        assert "unique(owner_id, fingerprint)" in sql
        assert "unique(owner_id, reverses_movement_id)" in sql


def test_repository_does_not_contain_database_credentials() -> None:
    root = Path(__file__).parents[1]
    candidates = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8").split("\0")
    for relative_path in filter(None, candidates):
        path = root / relative_path
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".bbsflmt", ".sqlite3", ".gz"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "sb_" + "secret_" not in text
        assert "eyJ" + "hbGciOi" not in text
