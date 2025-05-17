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


def display_papers(storage):
    """Display papers in the database"""
    logger.info("Displaying database contents...")

    try:
        # Execute raw query to avoid model validation issues
        papers_result = storage.conn.execute("""
            SELECT id, paper_id, title, abstract FROM papers
        """).fetchall()

        if not papers_result:
            logger.info("No papers found in database")
            return

        logger.info(f"Found {len(papers_result)} papers:")

        for paper_row in papers_result:
            paper_id = paper_row[1]
            paper_title = paper_row[2]
            paper_abstract = paper_row[3]

            logger.info(f"Paper: {paper_title} (ID: {paper_id})")
            logger.info(f"  Abstract: {paper_abstract[:100]}..." if paper_abstract else "  No abstract")

            # Get figures
            figures_result = storage.conn.execute("""
                SELECT id, label, caption FROM figures WHERE paper_id = ?
            """, (paper_id,)).fetchall()

            logger.info(f"  Figures: {len(figures_result)}")

            for fig_row in figures_result:
                fig_id = fig_row[0]
                fig_label = fig_row[1]
                fig_caption = fig_row[2]

                logger.info(f"    {fig_label}: {fig_caption[:50]}..." if fig_caption else "    No caption")

                # Get entities
                entities_result = storage.conn.execute("""
                    SELECT e.name, e.type 
                    FROM entities e
                    JOIN figure_entities fe ON e.id = fe.entity_id
                    WHERE fe.figure_id = ?
                """, (fig_id,)).fetchall()

                logger.info(f"    Entities: {len(entities_result)}")

                for i, entity_row in enumerate(entities_result[:5]):
                    entity_name = entity_row[0]
                    entity_type = entity_row[1]
                    logger.info(f"      {entity_type}: {entity_name}")

                if len(entities_result) > 5:
                    logger.info(f"      ... and {len(entities_result) - 5} more entities")

    except Exception as e:
        logger.error(f"Error displaying papers: {e}")


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
        display_papers(storage)

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
            display_papers(storage)

if __name__ == "__main__":
    # Parse arguments using argparse to maintain compatibility
    parser = argparse.ArgumentParser(description="Test batch ingestion of papers")
    parser.add_argument("paper_ids", nargs="*", help="List of PMC IDs or PMIDs to process")
    parser.add_argument("--reset", action="store_true", help="Reset the database")
    parser.add_argument("--display", action="store_true", help="Display database contents")

    args = parser.parse_args()

    main(paper_ids=args.paper_ids, reset=args.reset, display=args.display)