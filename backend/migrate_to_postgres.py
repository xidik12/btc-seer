"""One-time migration: copy all data from SQLite to PostgreSQL.

Usage:
    SQLITE_URL="sqlite+aiosqlite:////data/btc_oracle.db" \
    POSTGRES_URL="postgresql+asyncpg://user:pass@host:5432/dbname" \
    python migrate_to_postgres.py
"""

import asyncio
import logging
import os
import sys

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text, inspect

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 500


async def migrate():
    sqlite_url = os.environ.get("SQLITE_URL")
    postgres_url = os.environ.get("POSTGRES_URL")

    if not sqlite_url or not postgres_url:
        print("Usage: SQLITE_URL=... POSTGRES_URL=... python migrate_to_postgres.py")
        sys.exit(1)

    # Normalize postgres URL
    if postgres_url.startswith("postgres://"):
        postgres_url = "postgresql+asyncpg://" + postgres_url[len("postgres://"):]
    elif postgres_url.startswith("postgresql://") and "asyncpg" not in postgres_url:
        postgres_url = "postgresql+asyncpg://" + postgres_url[len("postgresql://"):]

    # Import models to register metadata
    sys.path.insert(0, os.path.dirname(__file__))
    from app.database import Base

    sqlite_engine = create_async_engine(sqlite_url, echo=False)
    pg_engine = create_async_engine(postgres_url, echo=False, pool_size=5)

    # Create tables on PostgreSQL
    logger.info("Creating tables on PostgreSQL...")
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Get table names from SQLite
    async with sqlite_engine.connect() as conn:
        table_names = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )

    logger.info(f"Found {len(table_names)} tables to migrate: {table_names}")

    for table_name in table_names:
        await _migrate_table(sqlite_engine, pg_engine, table_name)

    # Reset PostgreSQL sequences
    logger.info("Resetting PostgreSQL sequences...")
    async with pg_engine.begin() as conn:
        for table_name in table_names:
            try:
                # Check if table has an 'id' column with a sequence
                result = await conn.execute(text(
                    f"SELECT pg_get_serial_sequence('{table_name}', 'id')"
                ))
                seq = result.scalar()
                if seq:
                    await conn.execute(text(
                        f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM \"{table_name}\"), 0) + 1, false)"
                    ))
                    logger.info(f"  Reset sequence for {table_name}")
            except Exception as e:
                logger.debug(f"  No sequence for {table_name}: {e}")

    await sqlite_engine.dispose()
    await pg_engine.dispose()

    logger.info("Migration complete!")


async def _migrate_table(sqlite_engine, pg_engine, table_name: str):
    """Migrate a single table from SQLite to PostgreSQL in batches."""
    async with sqlite_engine.connect() as src:
        # Get row count
        count_result = await src.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
        total = count_result.scalar()
        if total == 0:
            logger.info(f"  {table_name}: empty, skipping")
            return

        # Get column names
        col_result = await src.execute(text(f'SELECT * FROM "{table_name}" LIMIT 1'))
        columns = list(col_result.keys())

        logger.info(f"  {table_name}: migrating {total} rows...")

        offset = 0
        migrated = 0
        while offset < total:
            # Read batch from SQLite
            rows_result = await src.execute(
                text(f'SELECT * FROM "{table_name}" LIMIT {BATCH_SIZE} OFFSET {offset}')
            )
            rows = rows_result.fetchall()
            if not rows:
                break

            # Write batch to PostgreSQL
            col_list = ", ".join(f'"{c}"' for c in columns)
            placeholders = ", ".join(f":{c}" for c in columns)
            insert_sql = f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

            async with pg_engine.begin() as dest:
                await dest.execute(
                    text(insert_sql),
                    [dict(zip(columns, row)) for row in rows],
                )

            migrated += len(rows)
            offset += BATCH_SIZE

            if migrated % 5000 == 0 or migrated == total:
                logger.info(f"    {table_name}: {migrated}/{total}")

        logger.info(f"  {table_name}: done ({migrated} rows)")


if __name__ == "__main__":
    asyncio.run(migrate())
