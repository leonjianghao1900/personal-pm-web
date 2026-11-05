from pathlib import Path

from app.schema import SCHEMA_SQL


def test_migration_file_matches_embedded_schema():
    disk = Path("migrations/0001_init.sql").read_text(encoding="utf-8")
    assert disk.strip() == SCHEMA_SQL.strip()
