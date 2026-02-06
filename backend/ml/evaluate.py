"""
Model Evaluation Script — generates accuracy reports and charts.

Usage:
    python -m ml.evaluate
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def evaluate():
    """Evaluate predictions from the database."""
    import asyncio
    from sqlalchemy import select
    from app.database import async_session, Prediction

    async def _eval():
        async with async_session() as session:
            result = await session.execute(
                select(Prediction).where(Prediction.was_correct.isnot(None))
            )
            predictions = result.scalars().all()

        if not predictions:
            logger.info("No evaluated predictions found in database.")
            return

        total = len(predictions)
        correct = sum(1 for p in predictions if p.was_correct)
        accuracy = correct / total * 100

        logger.info(f"\n{'='*50}")
        logger.info(f"MODEL EVALUATION ({total} predictions)")
        logger.info(f"{'='*50}")
        logger.info(f"Overall Accuracy: {accuracy:.1f}%")

        for tf in ["1h", "4h", "24h"]:
            tf_preds = [p for p in predictions if p.timeframe == tf]
            if tf_preds:
                tf_correct = sum(1 for p in tf_preds if p.was_correct)
                tf_acc = tf_correct / len(tf_preds) * 100
                logger.info(f"  {tf}: {tf_acc:.1f}% ({tf_correct}/{len(tf_preds)})")

        # Accuracy by confidence level
        logger.info("\nBy Confidence:")
        for label, low, high in [("High (>70%)", 70, 100), ("Medium (40-70%)", 40, 70), ("Low (<40%)", 0, 40)]:
            group = [p for p in predictions if low <= p.confidence < high]
            if group:
                g_correct = sum(1 for p in group if p.was_correct)
                g_acc = g_correct / len(group) * 100
                logger.info(f"  {label}: {g_acc:.1f}% ({g_correct}/{len(group)})")

        # Generate chart
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from collections import defaultdict

            daily = defaultdict(lambda: {"correct": 0, "total": 0})
            for p in predictions:
                day = p.timestamp.strftime("%Y-%m-%d")
                daily[day]["total"] += 1
                if p.was_correct:
                    daily[day]["correct"] += 1

            dates = sorted(daily.keys())
            accuracies = [daily[d]["correct"] / daily[d]["total"] * 100 for d in dates]

            plt.figure(figsize=(12, 5))
            plt.plot(dates, accuracies, marker="o", color="#4a9eff")
            plt.axhline(y=50, color="red", linestyle="--", alpha=0.5, label="Random (50%)")
            plt.fill_between(dates, accuracies, 50, alpha=0.1, color="#4a9eff")
            plt.title("BTC Oracle — Daily Prediction Accuracy")
            plt.ylabel("Accuracy %")
            plt.xticks(rotation=45)
            plt.legend()
            plt.tight_layout()

            chart_path = Path(__file__).parent / "data" / "accuracy_chart.png"
            chart_path.parent.mkdir(exist_ok=True)
            plt.savefig(chart_path, dpi=150)
            logger.info(f"\nChart saved to {chart_path}")

        except Exception as e:
            logger.warning(f"Could not generate chart: {e}")

    asyncio.run(_eval())


if __name__ == "__main__":
    evaluate()
