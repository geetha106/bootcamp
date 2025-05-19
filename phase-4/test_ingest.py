#!/usr/bin/env python
# test_ingest.py

import os
import sys
from cli.cli import ingest
from storage.duckdb_backend import DuckDBStorage
from utils.logging import get_logger

logger = get_logger("test")


def reset_database():
    """Delete the database file to start fresh"""
    db_path = "data/figurex.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"Removed existing database at {db_path}")
    else:
        logger.info(f"No existing database found at {db_path}")


def display_paper_data(paper_id):
    """Display all data for a specific paper from the database"""
    db = DuckDBStorage()

    # Get paper
    paper_data = db.conn.execute(
        "SELECT * FROM papers WHERE paper_id = ?",
        (paper_id,)
    ).fetchone()

    if not paper_data:
        logger.error(f"Paper {paper_id} not found in database")
        return

    print("\n" + "=" * 80)
    print(f"PAPER: {paper_data[2]}")
    print(f"ID: {paper_data[1]}")
    print("-" * 80)
    print(f"Abstract: {paper_data[3][:200]}...")
    print("=" * 80)

    # Get figures
    figures = db.conn.execute(
        "SELECT * FROM figures WHERE paper_id = ?",
        (paper_id,)
    ).fetchall()

    print(f"\nFound {len(figures)} figures:")

    for fig in figures:
        fig_id, paper_id, label, caption, url = fig
        print(f"\n[Figure {fig_id}]")
        print(f"Label: {label}")
        print(f"Caption: {caption[:100]}...")

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
    print(f"- Figures: {len(figures)}")
    print(f"- Unique Entities: {entity_count}")
    print(f"- Figure-Entity Links: {figure_entity_count}")
    print("=" * 80)


if __name__ == "__main__":
    # Check if a paper ID was provided
    if len(sys.argv) > 1:
        paper_id = sys.argv[1]
    else:
        paper_id = "PMC1790863"  # Default test case

    # Reset database to start fresh
    if "--reset" in sys.argv:
        reset_database()

    # First ingest the paper
    print(f"Ingesting paper {paper_id}...")
    ingest(paper_id)

    # Then display the results
    display_paper_data(paper_id if paper_id.startswith("PMC") else f"PMC{paper_id}")