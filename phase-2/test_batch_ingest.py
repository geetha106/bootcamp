#!/usr/bin/env python
# test_batch_ingest.py

import os
import sys
from cli.cli import process_paper
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


def display_papers_data():
    """Display all papers from the database"""
    db = DuckDBStorage()

    # Get all papers
    papers = db.conn.execute(
        "SELECT * FROM papers"
    ).fetchall()

    if not papers:
        logger.error("No papers found in database")
        return

    print(f"\nFound {len(papers)} papers in database:")

    for paper_data in papers:
        print("\n" + "=" * 80)
        print(f"PAPER: {paper_data[2]}")
        print(f"ID: {paper_data[1]}")
        print("-" * 80)
        print(f"Abstract: {paper_data[3][:200]}..." if paper_data[3] else "No abstract available")
        print("=" * 80)

        # Get figures for this paper
        figures = db.conn.execute(
            "SELECT * FROM figures WHERE paper_id = ?",
            (paper_data[1],)
        ).fetchall()

        print(f"\nFound {len(figures)} figures:")

        for fig in figures:
            fig_id, paper_id, label, caption, url = fig
            print(f"\n[Figure {fig_id}]")
            print(f"Label: {label}")
            print(f"Caption: {caption[:100]}..." if caption else "No caption available")

            # Get entities for this figure
            entities = db.conn.execute(
                """
                SELECT e.name, e.type 
                FROM entities e
                JOIN figure_entities fe ON e.id = fe.entity_id
                WHERE fe.figure_id = ?
                """,
                (fig_id,)
            ).fetchall()

            if entities:
                print(f"\nEntities ({len(entities)}):")
                for name, etype in entities:
                    print(f"  - {name} ({etype})")
            else:
                print("\nNo entities found for this figure")

            print("-" * 40)

    # Print overall statistics
    entity_count = db.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    figure_entity_count = db.conn.execute("SELECT COUNT(*) FROM figure_entities").fetchone()[0]

    print("\n" + "=" * 80)
    print(f"Database Statistics:")
    print(f"- Papers: {len(papers)}")
    print(f"- Figures: {db.conn.execute('SELECT COUNT(*) FROM figures').fetchone()[0]}")
    print(f"- Unique Entities: {entity_count}")
    print(f"- Figure-Entity Links: {figure_entity_count}")
    print("=" * 80)


if __name__ == "__main__":
    # Parse command line arguments
    args = sys.argv[1:]
    paper_ids = []
    display_flag = False
    reset_flag = False

    # Extract flags and paper IDs
    for arg in args:
        if arg == '--display':
            display_flag = True
        elif arg == '--reset':
            reset_flag = True
        else:
            paper_ids.append(arg)

    # Reset database if requested
    if reset_flag:
        reset_database()

    # Process papers if any IDs were provided
    success_count = 0
    if paper_ids:
        logger.info(f"Processing {len(paper_ids)} paper(s)...")
        for paper_id in paper_ids:
            if process_paper(paper_id):
                success_count += 1
        logger.info(f"Processed {success_count} out of {len(paper_ids)} papers successfully")

    # Display database contents if requested or if no papers were processed
    if display_flag or (not paper_ids and not reset_flag):
        display_papers_data()

    # If no arguments were provided, show usage
    if not args:
        print("Usage:")
        print("  python test_batch_ingest.py [PMC_ID|PMID...] [--display] [--reset]")
        print("")
        print("Options:")
        print("  PMC_ID|PMID    One or more paper IDs to process")
        print("  --display      Display all papers in the database")
        print("  --reset        Reset the database before processing")