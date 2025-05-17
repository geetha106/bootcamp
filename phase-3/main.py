# main.py
from typing import List, Optional
from models.paper import Paper
from ingestion.pmc_ingestor import PMCIngestor
from ingestion.pubtator_client import PubTatorClient
from storage.duckdb_backend import DuckDBStorage
from ingestion.watcher import FolderWatcher
from utils.logging import get_logger

logger = get_logger("figurex.main")


class FigureX:
    """
    Main class for the FigureX system. Provides a programmatic interface for the system.
    """

    def __init__(self, db_path: str = "data/figurex.db"):
        """
        Initialize the FigureX system.

        Args:
            db_path: Path to the database file
        """
        self.storage = DuckDBStorage(db_path)
        self.pmc_ingestor = PMCIngestor()
        self.pubtator_client = PubTatorClient()

    def ingest_paper(self, paper_id: str) -> bool:
        """
        Ingest a single paper by its ID (PMC or PMID).

        Args:
            paper_id: PMC ID or PMID of the paper to ingest

        Returns:
            bool: True if ingestion was successful, False otherwise
        """
        from cli.cli import process_paper
        return process_paper(paper_id)

    def batch_ingest(self, paper_ids: List[str]) -> tuple:
        """
        Ingest multiple papers by their IDs.

        Args:
            paper_ids: List of PMC IDs or PMIDs to ingest

        Returns:
            tuple: (success_count, failed_count)
        """
        success_count = 0
        failed_count = 0

        for paper_id in paper_ids:
            if self.ingest_paper(paper_id):
                success_count += 1
            else:
                failed_count += 1

        return success_count, failed_count

    def ingest_from_file(self, file_path: str) -> tuple:
        """
        Ingest papers from a file containing one ID per line.

        Args:
            file_path: Path to the file containing paper IDs

        Returns:
            tuple: (success_count, failed_count)
        """
        try:
            with open(file_path, 'r') as f:
                paper_ids = [line.strip() for line in f if line.strip()]

            return self.batch_ingest(paper_ids)
        except Exception as e:
            logger.error(f"Error ingesting from file {file_path}: {e}")
            return 0, 0

    def start_watcher(self, folder_path: str = "data/watch", interval: int = 60):
        """
        Start watching a folder for paper ID files.

        Args:
            folder_path: Path to the folder to watch
            interval: Check interval in seconds
        """
        watcher = FolderWatcher(folder_path, interval)
        watcher.start()

    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """
        Get a paper from the database.

        Args:
            paper_id: PMC ID of the paper

        Returns:
            Paper object or None if not found
        """
        # Ensure PMC ID has the prefix
        if not paper_id.startswith("PMC"):
            paper_id = f"PMC{paper_id}"

        try:
            paper_data = self.storage.conn.execute(
                "SELECT * FROM papers WHERE paper_id = ?",
                (paper_id,)
            ).fetchone()

            if not paper_data:
                return None

            # Get figures for this paper
            figures = self.storage.conn.execute(
                "SELECT * FROM figures WHERE paper_id = ?",
                (paper_id,)
            ).fetchall()

            # Convert to Paper object (simplified for now)
            # In a full implementation, you would build the complete Paper object with Figures and Entities
            from models.paper import Paper, Figure, Entity

            processed_figures = []
            for fig in figures:
                fig_id, _, label, caption, url = fig

                # Get entities for this figure
                entities = self.storage.conn.execute(
                    """
                    SELECT e.name, e.type 
                    FROM entities e
                    JOIN figure_entities fe ON e.id = fe.entity_id
                    WHERE fe.figure_id = ?
                    """,
                    (fig_id,)
                ).fetchall()

                # Create Entity objects
                entity_objects = [Entity(text=name, type=etype) for name, etype in entities]

                # Create Figure object
                processed_figures.append(Figure(
                    label=label,
                    caption=caption,
                    url=url,
                    entities=entity_objects
                ))

            # Create and return Paper object
            return Paper(
                paper_id=paper_data[1],
                title=paper_data[2],
                abstract=paper_data[3],
                figures=processed_figures
            )

        except Exception as e:
            logger.error(f"Error getting paper {paper_id}: {e}")
            return None

    def list_papers(self) -> List[str]:
        """
        List all paper IDs in the database.

        Returns:
            List of paper IDs
        """
        try:
            result = self.storage.conn.execute("SELECT paper_id FROM papers").fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error listing papers: {e}")
            return []


# Example usage
if __name__ == "__main__":
    figurex = FigureX()

    # Ingest a single paper
    # figurex.ingest_paper("PMC1790863")

    # Batch ingest
    # success, failed = figurex.batch_ingest(["PMC1790863", "PMC7696669", "35871145"])
    # print(f"Batch ingest: {success} succeeded, {failed} failed")

    # List papers
    papers = figurex.list_papers()
    print(f"Papers in database: {papers}")

    # Get a paper
    if papers:
        paper = figurex.get_paper(papers[0])
        if paper:
            print(f"Paper: {paper.title}")
            print(f"Figures: {len(paper.figures)}")