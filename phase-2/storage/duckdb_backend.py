# duckdb_backend.py
import duckdb
import os
from typing import List
from models.paper import Paper, Figure, Entity
from utils.logging import get_logger

logger = get_logger(__name__)


class DuckDBStorage:
    def __init__(self, db_path: str = "data/figurex.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._initialize_schema()
        logger.info(f"DuckDB initialized at {db_path}")

    def _initialize_schema(self):
        """Load and execute the schema SQL file"""
        with open("storage/schema.sql", "r") as f:
            schema_sql = f.read()
            self.conn.execute(schema_sql)
            logger.debug("Schema initialized")

    def save_paper(self, paper: Paper):
        """Save a Paper model and all its related entities to the database"""
        # Start transaction
        self.conn.execute("BEGIN TRANSACTION")

        try:
            # Check if paper_id already exists
            existing = self.conn.execute(
                "SELECT id FROM papers WHERE paper_id = ?", (paper.paper_id,)
            ).fetchone()

            if existing:
                paper_row_id = existing[0]
                # Update paper info
                self.conn.execute(
                    "UPDATE papers SET title = ?, abstract = ?, source = ? WHERE id = ?",
                    (paper.title, paper.abstract, "PMC", paper_row_id)
                )
                logger.info(f"Updated existing paper {paper.paper_id}")

                # Delete existing figures and their entity relationships
                existing_figures = self.conn.execute(
                    "SELECT id FROM figures WHERE paper_id = ?", (paper.paper_id,)
                ).fetchall()

                for fig_id in [fig[0] for fig in existing_figures]:
                    self.conn.execute(
                        "DELETE FROM figure_entities WHERE figure_id = ?", (fig_id,)
                    )

                self.conn.execute(
                    "DELETE FROM figures WHERE paper_id = ?", (paper.paper_id,)
                )
                logger.info(f"Deleted existing figures for {paper.paper_id}")
            else:
                # Insert new paper
                paper_row_id = self.get_next_id("papers")
                self.conn.execute(
                    "INSERT INTO papers (id, paper_id, title, abstract, source) VALUES (?, ?, ?, ?, ?)",
                    (paper_row_id, paper.paper_id, paper.title, paper.abstract, "PMC")
                )
                logger.info(f"Inserted new paper {paper.paper_id}")

            # Save all figures
            for fig in paper.figures:
                fig_row_id = self.get_next_id("figures")
                self.conn.execute(
                    "INSERT INTO figures (id, paper_id, caption, figure_url) VALUES (?, ?, ?, ?)",
                    (fig_row_id, paper.paper_id, fig.caption, fig.url)
                )
                logger.debug(f"Inserted figure {fig.label} for paper {paper.paper_id}")

                # Save all entities for this figure
                for entity in fig.entities:
                    # Check if entity already exists
                    entity_row = self.conn.execute(
                        "SELECT id FROM entities WHERE name = ? AND type = ?",
                        (entity.text, entity.type)
                    ).fetchone()

                    if entity_row is None:
                        # Insert new entity
                        entity_row_id = self.get_next_id("entities")
                        self.conn.execute(
                            "INSERT INTO entities (id, name, type) VALUES (?, ?, ?)",
                            (entity_row_id, entity.text, entity.type)
                        )
                    else:
                        entity_row_id = entity_row[0]

                    # Create relationship between figure and entity
                    fe_id = self.get_next_id("figure_entities")
                    self.conn.execute(
                        "INSERT INTO figure_entities (id, figure_id, entity_id) VALUES (?, ?, ?)",
                        (fe_id, fig_row_id, entity_row_id)
                    )

                logger.debug(f"Added {len(fig.entities)} entities to figure {fig.label}")

            # Commit transaction
            self.conn.execute("COMMIT")
            logger.info(f"Successfully saved paper {paper.paper_id} with {len(paper.figures)} figures")

        except Exception as e:
            # Roll back on error
            self.conn.execute("ROLLBACK")
            logger.error(f"Error saving paper {paper.paper_id}: {e}")
            raise

    def get_next_id(self, table_name: str) -> int:
        """Get the next ID value for a table"""
        result = self.conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}").fetchone()
        return result[0]

    def get_paper(self, paper_id: str) -> Paper:
        """Retrieve a paper and all its related data by paper_id"""
        pass  # Implementation needed

    def list_papers(self) -> List[str]:
        """List all paper IDs in the database"""
        pass  # Implementation needed