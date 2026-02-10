"""Periodic database backup — supports PostgreSQL (pg_dump) and SQLite (file copy).

Optionally creates a portable SQLite snapshot from PostgreSQL data for easy download.
"""

import asyncio
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


async def run_database_backup():
    """Main backup entry point — dispatches based on dialect."""
    if not settings.backup_enabled:
        return

    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    try:
        if settings.is_postgres:
            await _backup_postgres(backup_dir)
            if settings.backup_sqlite_snapshot:
                await _create_sqlite_snapshot(backup_dir)
        else:
            await _backup_sqlite(backup_dir)

        _cleanup_old_backups(backup_dir)
        logger.info("Database backup completed successfully")
    except Exception as e:
        logger.error(f"Database backup failed: {e}", exc_info=True)


async def _backup_postgres(backup_dir: Path):
    """Run pg_dump in compressed custom format."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dump_file = backup_dir / f"btc_seer_{timestamp}.dump"

    # Extract connection URL for pg_dump
    db_url = settings.database_url
    # Normalize to postgres:// for pg_dump (it doesn't understand postgresql+asyncpg://)
    for prefix in ("postgresql+asyncpg://", "postgresql://"):
        if db_url.startswith(prefix):
            db_url = "postgres://" + db_url[len(prefix):]
            break

    proc = await asyncio.create_subprocess_exec(
        "pg_dump", "-Fc", "-d", db_url, "-f", str(dump_file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"pg_dump failed (rc={proc.returncode}): {stderr.decode()}")

    size_mb = dump_file.stat().st_size / (1024 * 1024)
    logger.info(f"PostgreSQL backup: {dump_file.name} ({size_mb:.1f} MB)")


async def _create_sqlite_snapshot(backup_dir: Path):
    """Copy key tables from PostgreSQL into a portable SQLite file."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    snapshot_path = backup_dir / f"btc_seer_{timestamp}.sqlite"

    try:
        import asyncpg
    except ImportError:
        logger.warning("asyncpg not installed — skipping SQLite snapshot")
        return

    # Parse connection info from DATABASE_URL
    db_url = settings.database_url
    for prefix in ("postgresql+asyncpg://", "postgresql://"):
        if db_url.startswith(prefix):
            db_url = "postgres://" + db_url[len(prefix):]
            break

    conn = await asyncpg.connect(db_url)
    try:
        # Get list of tables
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        table_names = [t["tablename"] for t in tables]

        # Create SQLite database and copy data
        sqlite_conn = sqlite3.connect(str(snapshot_path))
        try:
            for table_name in table_names:
                # Get column info
                columns = await conn.fetch(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = $1 ORDER BY ordinal_position",
                    table_name,
                )
                if not columns:
                    continue

                col_names = [c["column_name"] for c in columns]
                col_defs = []
                for c in columns:
                    dt = c["data_type"].upper()
                    if "INT" in dt:
                        col_defs.append(f'"{c["column_name"]}" INTEGER')
                    elif dt in ("REAL", "DOUBLE PRECISION", "NUMERIC"):
                        col_defs.append(f'"{c["column_name"]}" REAL')
                    elif "BOOL" in dt:
                        col_defs.append(f'"{c["column_name"]}" INTEGER')
                    else:
                        col_defs.append(f'"{c["column_name"]}" TEXT')

                create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(col_defs)})'
                sqlite_conn.execute(create_sql)

                # Fetch data in batches
                offset = 0
                batch_size = 1000
                placeholders = ", ".join(["?"] * len(col_names))
                insert_sql = f'INSERT INTO "{table_name}" ({", ".join(f\'"{c}"\' for c in col_names)}) VALUES ({placeholders})'

                while True:
                    rows = await conn.fetch(
                        f'SELECT * FROM "{table_name}" LIMIT {batch_size} OFFSET {offset}'
                    )
                    if not rows:
                        break
                    sqlite_conn.executemany(
                        insert_sql,
                        [tuple(str(v) if v is not None else None for v in row.values()) for row in rows],
                    )
                    offset += batch_size

                sqlite_conn.commit()
        finally:
            sqlite_conn.close()

        size_mb = snapshot_path.stat().st_size / (1024 * 1024)
        logger.info(f"SQLite snapshot: {snapshot_path.name} ({size_mb:.1f} MB)")

    finally:
        await conn.close()


async def _backup_sqlite(backup_dir: Path):
    """Simple file copy for local SQLite dev databases."""
    # Extract path from sqlite URL
    url = settings.database_url
    # sqlite+aiosqlite:////data/btc_oracle.db → /data/btc_oracle.db
    if ":///" in url:
        db_path = url.split(":///", 1)[1]
        # Handle four slashes (absolute path): sqlite+aiosqlite:////data/...
        if db_path.startswith("/"):
            pass  # Already absolute
    else:
        db_path = url.split("://", 1)[1]

    source = Path(db_path)
    if not source.exists():
        logger.warning(f"SQLite file not found: {source}")
        return

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"btc_seer_{timestamp}.sqlite"
    shutil.copy2(str(source), str(dest))

    size_mb = dest.stat().st_size / (1024 * 1024)
    logger.info(f"SQLite backup: {dest.name} ({size_mb:.1f} MB)")


def _cleanup_old_backups(backup_dir: Path):
    """Delete backup files older than retention policy."""
    cutoff = datetime.utcnow() - timedelta(days=settings.backup_retention_days)

    for f in backup_dir.iterdir():
        if not f.is_file():
            continue
        if f.suffix not in (".dump", ".sqlite"):
            continue
        # Check file modification time
        mtime = datetime.utcfromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            f.unlink()
            logger.info(f"Deleted old backup: {f.name}")
