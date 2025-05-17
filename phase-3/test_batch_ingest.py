# test_batch_ingest.py

import argparse
import sys
from pathlib import Path
import typer
from typing import List, Optional

# Import from the new modular structure
from ingestion.paper_processor import PaperProcessor
from storage.duckdb_backend import DuckDBStorage
from utils.logging import get_logger

logger = get_logger()


def main(paper_ids: List[str] = [], reset: bool = False, display: bool = False):
    """
    Test batch ingestion of papers

    Args:
        paper_ids: List of PMC IDs or PMIDs to process
        reset: Whether to reset the database
        display: Whether to display the database contents
    """
    storage = DuckDBStorage()

    if reset:
        logger.info("Resetting database...")
        storage.reset_db()
        logger.info("Database reset complete")

    if display:
        logger.info("Displaying database contents...")
        papers = storage.get_papers()

        if not papers:
            logger.info("No papers found in database")
        else:
            logger.info(f"Found {len(papers)} papers:")
            for paper in papers:
                logger.info(f"Paper: {paper.title} (PMC ID: {paper.pmc_id})")
                logger.info(f"  Abstract: {paper.abstract[:100]}...")
                logger.info(f"  Figures: {len(paper.figures)}")
                for fig in paper.figures:
                    logger.info(f"    {fig.label}: {fig.caption[:50]}...")
                    logger.info(f"    Entities: {len(fig.entities)}")
                    for entity in fig.entities[:5]:  # Show only first 5 entities
                        logger.info(f"      {entity.type}: {entity.text}")
                    if len(fig.entities) > 5:
                        logger.info(f"      ... and {len(fig.entities) - 5} more entities")

    if paper_ids:
        logger.info(f"Processing {len(paper_ids)} paper(s)...")
        processor = PaperProcessor()
        success_count = 0
        failed_count = 0

        for paper_id in paper_ids:
            if processor.process(paper_id):
                success_count += 1
            else:
                failed_count += 1

        logger.info(f"Batch processing complete. Success: {success_count}, Failed: {failed_count}")

        if display:
            logger.info("Displaying updated database contents...")
            papers = storage.get_papers()
            logger.info(f"Found {len(papers)} papers after processing")


if __name__ == "__main__":
    # Parse arguments using argparse to maintain compatibility
    parser = argparse.ArgumentParser(description="Test batch ingestion of papers")
    parser.add_argument("paper_ids", nargs="*", help="List of PMC IDs or PMIDs to process")
    parser.add_argument("--reset", action="store_true", help="Reset the database")
    parser.add_argument("--display", action="store_true", help="Display database contents")

    args = parser.parse_args()

    main(paper_ids=args.paper_ids, reset=args.reset, display=args.display)