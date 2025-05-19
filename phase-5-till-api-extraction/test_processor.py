# test_processor.py
from ingestion.paper_processor import PaperProcessor
from storage.duckdb_backend import DuckDBStorage
from utils.logging import get_logger

logger = get_logger()


def test_processor():
    """
    Test the PaperProcessor directly to verify it's saving data to the database.
    """
    # Create a processor instance
    processor = PaperProcessor()

    # Process a paper - we'll use one of your examples
    paper_id = "PMC7696669"  # or "17299597"

    logger.info(f"Testing PaperProcessor with paper ID: {paper_id}")

    # Process the paper
    result = processor.process(paper_id)
    logger.info(f"Processing result: {'Success' if result else 'Failed'}")

    # Check database directly to verify the paper was saved
    db = DuckDBStorage()
    papers_query = db.conn.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
    papers = papers_query.fetchall()

    logger.info(f"Found {len(papers)} paper entries in database")

    if papers:
        paper_row_id = papers[0][0]
        logger.info(f"Paper title: {papers[0][2]}")

        # Check figures
        figures_query = db.conn.execute("SELECT * FROM figures WHERE paper_id = ?", (paper_id,))
        figures = figures_query.fetchall()
        logger.info(f"Found {len(figures)} figures for this paper")

        # Check entities if there are figures
        if figures:
            for fig in figures:
                fig_id = fig[0]
                fig_label = fig[2]

                # Get entities for this figure
                entities_query = db.conn.execute("""
                    SELECT e.name, e.type
                    FROM entities e
                    JOIN figure_entities fe ON e.id = fe.entity_id
                    WHERE fe.figure_id = ?
                """, (fig_id,))
                entities = entities_query.fetchall()

                logger.info(f"Figure '{fig_label}' has {len(entities)} entities")

    logger.info("Test completed")


if __name__ == "__main__":
    test_processor()