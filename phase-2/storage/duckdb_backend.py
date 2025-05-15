# duckdb_backend.py
import duckdb
import os
from models.paper import Paper, Figure, Entity
from utils.logging import get_logger

logger = get_logger("figurex.storage")


class DuckDBStorage:
    def __init__(self, db_path: str = "data/figurex.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._initialize_schema()

    def _initialize_schema(self):
        """Initialize database schema if it doesn't exist"""
        try:
            with open("storage/schema.sql", "r") as f:
                self.conn.execute(f.read())
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            raise

    def save_paper(self, paper: Paper):
        """
        Save paper and its figures/entities to database, avoiding duplicates
        """
        try:
            # Begin transaction
            self.conn.execute("BEGIN TRANSACTION")

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
                logger.info(f"Updated existing paper: {paper.paper_id}")
            else:
                # Insert new paper
                paper_row_id = self.get_next_id("papers")
                self.conn.execute(
                    "INSERT INTO papers (id, paper_id, title, abstract, source) VALUES (?, ?, ?, ?, ?)",
                    (paper_row_id, paper.paper_id, paper.title, paper.abstract, "PMC")
                )
                logger.info(f"Inserted new paper: {paper.paper_id}")

            # Save figures without duplication
            for fig_index, fig in enumerate(paper.figures):
                # Use figure label if available, otherwise create a unique label
                fig_label = fig.label if fig.label and fig.label != "Unknown Figure" else f"Figure {fig_index + 1}"

                # Check if this figure already exists for this paper
                existing_fig = self.conn.execute(
                    "SELECT id FROM figures WHERE paper_id = ? AND label = ?",
                    (paper.paper_id, fig_label)
                ).fetchone()

                if existing_fig:
                    fig_row_id = existing_fig[0]
                    # Update the existing figure
                    self.conn.execute(
                        "UPDATE figures SET caption = ?, figure_url = ? WHERE id = ?",
                        (fig.caption, fig.url, fig_row_id)
                    )
                    logger.info(f"Updated existing figure: {fig_label} for paper {paper.paper_id}")

                    # Clear existing entity links for this figure before adding new ones
                    self.conn.execute(
                        "DELETE FROM figure_entities WHERE figure_id = ?",
                        (fig_row_id,)
                    )
                else:
                    # Create new figure
                    fig_row_id = self.get_next_id("figures")
                    self.conn.execute(
                        "INSERT INTO figures (id, paper_id, label, caption, figure_url) VALUES (?, ?, ?, ?, ?)",
                        (fig_row_id, paper.paper_id, fig_label, fig.caption, fig.url)
                    )
                    logger.info(f"Inserted new figure: {fig_label} for paper {paper.paper_id}")

                # Process entities for this figure
                entity_count = 0
                for entity in fig.entities:
                    # Skip empty entities
                    if not entity.text:
                        continue

                    # Use type if available
                    entity_type = entity.type if entity.type else "UNKNOWN"

                    # Check if entity already exists
                    entity_row = self.conn.execute(
                        "SELECT id FROM entities WHERE name = ?",
                        (entity.text,)
                    ).fetchone()

                    if entity_row is None:
                        entity_row_id = self.get_next_id("entities")
                        self.conn.execute(
                            "INSERT INTO entities (id, name, type) VALUES (?, ?, ?)",
                            (entity_row_id, entity.text, entity_type)
                        )
                    else:
                        entity_row_id = entity_row[0]

                    # Check if this figure-entity link already exists
                    existing_link = self.conn.execute(
                        "SELECT id FROM figure_entities WHERE figure_id = ? AND entity_id = ?",
                        (fig_row_id, entity_row_id)
                    ).fetchone()

                    if existing_link is None:
                        # Link entity to figure
                        fe_id = self.get_next_id("figure_entities")
                        self.conn.execute(
                            "INSERT INTO figure_entities (id, figure_id, entity_id) VALUES (?, ?, ?)",
                            (fe_id, fig_row_id, entity_row_id)
                        )
                        entity_count += 1

                logger.info(f"Added {entity_count} entities to figure {fig_label}")

            # Commit transaction
            self.conn.execute("COMMIT")
            logger.info(f"Successfully saved paper {paper.paper_id} with {len(paper.figures)} figures")

        except Exception as e:
            # Rollback on error
            self.conn.execute("ROLLBACK")
            logger.error(f"Error saving paper {paper.paper_id}: {e}")
            raise

    def get_next_id(self, table_name: str) -> int:
        """Get the next available ID for a table"""
        result = self.conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}").fetchone()
        return result[0]