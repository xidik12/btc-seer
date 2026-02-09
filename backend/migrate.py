"""Migration script for BTC Seer upgrade.

Adds new columns to existing tables via ALTER TABLE.
New tables are created automatically by SQLAlchemy's create_all().
Run this before starting the app after upgrading.
"""
import asyncio
import logging

from app.config import settings
from app.database import engine, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ALTER TABLE statements for existing tables
MIGRATIONS = [
    # QuantPrediction: add 1w/1mo prediction columns
    "ALTER TABLE quant_predictions ADD COLUMN pred_1w_price FLOAT",
    "ALTER TABLE quant_predictions ADD COLUMN pred_1w_change_pct FLOAT",
    "ALTER TABLE quant_predictions ADD COLUMN pred_1mo_price FLOAT",
    "ALTER TABLE quant_predictions ADD COLUMN pred_1mo_change_pct FLOAT",
    "ALTER TABLE quant_predictions ADD COLUMN actual_price_1w FLOAT",
    "ALTER TABLE quant_predictions ADD COLUMN actual_price_1mo FLOAT",
    "ALTER TABLE quant_predictions ADD COLUMN was_correct_1w BOOLEAN",
    "ALTER TABLE quant_predictions ADD COLUMN was_correct_1mo BOOLEAN",

    # ModelVersion: add A/B testing fields
    "ALTER TABLE model_versions ADD COLUMN is_candidate BOOLEAN DEFAULT 0",
    "ALTER TABLE model_versions ADD COLUMN ab_test_accuracy FLOAT",
    "ALTER TABLE model_versions ADD COLUMN ensemble_weight FLOAT",
]


async def run_migrations():
    logger.info("Running BTC Seer migrations...")

    # First, create any new tables
    await init_db()
    logger.info("New tables created (if any)")

    # Then, add columns to existing tables
    async with engine.begin() as conn:
        for sql in MIGRATIONS:
            try:
                await conn.execute(__import__('sqlalchemy').text(sql))
                logger.info(f"OK: {sql}")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info(f"SKIP (already exists): {sql}")
                else:
                    logger.warning(f"SKIP: {sql} — {e}")

    logger.info("Migrations complete!")


if __name__ == "__main__":
    asyncio.run(run_migrations())
