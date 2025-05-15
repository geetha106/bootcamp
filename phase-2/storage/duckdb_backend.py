# duckdb_backend.py
import duckdb
import os
from models.paper import Paper, Figure, Entity
from utils.logging import get_logger

logger = get_logger(__name__)


class DuckDBStorage:
    def __init__(self, db_path: str = "data/figurex.db"):
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._initialize_schema()
        logger.info(f"DuckDB initialized at {db_path}")

    def _initialize_schema(self):
        """Initialize database schema from SQL file"""
        try:
            with open("storage/schema.sql", "r") as f:
                schema_sql = f.read()
                self.conn.execute(schema_sql)
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise

    def save_paper(self, paper: Paper):
        """
        Save a paper and its figures, entities to the database.

        Args:
            paper: Paper object with title, abstract, figures, and entities
        """
        # Check if paper already exists
        existing = self.conn.execute(
            "SELECT id FROM papers WHERE paper_id = ?", [paper.paper_id]
        ).fetchone()

        if existing:
            paper_row_id = existing[0]
            # Update paper info
            self.conn.execute(
                "UPDATE papers SET title = ?, abstract = ?, source = ? WHERE id = ?",
                [paper.title, paper.abstract, "PMC", paper_row_id]
            )
            logger.info(f"Updated existing paper {paper.paper_id}")
        else:
            # Insert new paper
            paper_row_id = self.get_next_id("papers")
            self.conn.execute(
                "INSERT INTO papers (id, paper_id, title, abstract, source) VALUES (?, ?, ?, ?, ?)",
                [paper_row_id, paper.paper_id, paper.title, paper.abstract, "PMC"]
            )
            logger.info(f"Inserted new paper {paper.paper_id}")

        # Save all figures for this paper
        for fig in paper.figures:
            fig_row_id = self.get_next_id("figures")
            self.conn.execute(
                "INSERT INTO figures (id, paper_id, caption, figure_url) VALUES (?, ?, ?, ?)",
                [fig_row_id, paper.paper_id, fig.caption, fig.url]
            )

            # Save entities for this figure
            for entity in fig.entities:
                # Check if entity already exists
                entity_row = self.conn.execute(
                    "SELECT id FROM entities WHERE name = ?", [entity.text]
                ).fetchone()

                if entity_row is None:
                    # Insert new entity
                    entity_row_id = self.get_next_id("entities")
                    self.conn.execute(
                        "INSERT INTO entities (id, name, type) VALUES (?, ?, ?)",
                        [entity_row_id, entity.text, entity.type]
                    )
                else:
                    entity_row_id = entity_row[0]

                # Link entity to figure
                fe_id = self.get_next_id("figure_entities")
                self.conn.execute(
                    "INSERT INTO figure_entities (id, figure_id, entity_id) VALUES (?, ?, ?)",
                    [fe_id, fig_row_id, entity_row_id]
                )

    def get_next_id(self, table_name: str) -> int:
        """Get the next available ID for a table"""
        result = self.conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}").fetchone()
        return result[0]

    def get_paper(self, paper_id: str) -> Paper:
        """
        Retrieve a stored Paper by ID.

        Args:
            paper_id: The PMC ID of the paper

        Returns:
            Paper object with title, abstract, figures, and entities
        """
        # Implement paper retrieval logic
        pass

    def list_papers(self):
        """Return a list of all stored paper IDs"""
        results = self.conn.execute("SELECT paper_id FROM papers").fetchall()
        return [row[0] for row in results]