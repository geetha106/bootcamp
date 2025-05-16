# test_batch_ingest.py
# !/usr/bin/env python

import os
import sys
import tempfile
from cli.cli import batch_ingest, batch_ingest_from_file
from storage.duckdb_backend import DuckDBStorage
from utils.logging import get_logger

logger = get_logger("test_batch")


def reset_database():
    """Delete the database file to start fresh"""
    db_path = "data/figurex.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"Removed existing database at {db_path}")
    else:
        logger.info(f"No existing database found at {db_path}")


def display_all_papers():
    """Display summary stats for all papers in the database"""
    db = DuckDBStorage()

    # Get all papers
    papers = db.conn.execute("SELECT * FROM papers").fetchall()

    if not papers:
        logger.error("No papers found in database")
        return

    print("\n" + "=" * 80)
    print(f"TOTAL PAPERS IN DATABASE: {len(papers)}")
    print("=" * 80)

    for paper_data in papers:
        _, paper_id, title, abstract, source = paper_data

        # Get figure count for this paper
        fig_count = db.conn.execute(
            "SELECT COUNT(*) FROM figures WHERE paper_id = ?",
            (paper_id,)
        ).fetchone()[0]

        # Get entity count for this paper's figures
        entity_count = db.conn.execute(
            """
            SELECT COUNT(DISTINCT fe.entity_id)
            FROM figures f
            JOIN figure_entities fe ON f.id = fe.figure_id
            WHERE f.paper_id = ?
            """,
            (paper_id,)
        ).fetchone()[0]

        print(f"Paper ID: {paper_id}")
        print(f"Title: {title}")
        print(f"Figures: {fig_count}")
        print(f"Unique Entities: {entity_count}")
        print("-" * 80)

    # Print overall statistics
    fig_count = db.conn.execute("SELECT COUNT(*) FROM figures").fetchone()[0]
    entity_count = db.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    figure_entity_count = db.conn.execute("SELECT COUNT(*) FROM figure_entities").fetchone()[0]

    print("\n" + "=" * 80)
    print(f"DATABASE STATISTICS:")
    print(f"- Total Papers: {len(papers)}")
    print(f"- Total Figures: {fig_count}")
    print(f"- Unique Entities: {entity_count}")
    print(f"- Figure-Entity Links: {figure_entity_count}")
    print("=" * 80)


if __name__ == "__main__":
    # Process command line args
    reset_db = "--reset" in sys.argv
    display_only = "--display" in sys.argv

    if reset_db:
        reset_database()

    if display_only:
        display_all_papers()
        sys.exit(0)

    # Check if a sample IDs file was provided
    file_path = None
    for arg in sys.argv[1:]:
        if arg.endswith(".txt") and os.path.isfile(arg):
            file_path = arg
            break

    # Check if direct paper IDs were provided (not starting with --)
    paper_ids = [arg for arg in sys.argv[1:] if not arg.startswith("--") and not arg.endswith(".txt")]

    if not file_path and not paper_ids:
        # Create a temporary file with sample PMC IDs
        sample_ids = ["PMC1790863", "PMC7696669", "35871145"]  # Last one is a PMID
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("\n".join(sample_ids))
            file_path = tmp.name
        logger.info(f"Created temporary file with sample IDs at {file_path}")

    # Run the batch ingestion
    if file_path:
        print(f"Processing papers from file: {file_path}")
        batch_ingest_from_file(file_path)

        # Clean up temporary file if we created one
        if "tmp" in locals():
            os.unlink(file_path)
    elif paper_ids:
        print(f"Processing papers from command line: {', '.join(paper_ids)}")
        batch_ingest(paper_ids)

    # Display results
    display_all_papers()