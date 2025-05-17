# storage/duckdb_backend.py
import duckdb
import os
from models.paper import Paper, Figure, Entity
from typing import List, Optional, Tuple
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

    def reset_db(self):
        """Reset the database by dropping all tables and recreating them"""
        try:
            # Drop tables in the correct order to respect foreign key constraints
            self.conn.execute("DROP TABLE IF EXISTS figure_entities")
            self.conn.execute("DROP TABLE IF EXISTS entities")
            self.conn.execute("DROP TABLE IF EXISTS figures")
            self.conn.execute("DROP TABLE IF EXISTS papers")

            # Reinitialize schema
            self._initialize_schema()
            logger.info("Database has been reset")
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            raise

    def get_papers(self) -> List[Paper]:
        """
        Get all papers from the database with their figures and entities
        """
        try:
            # Get all papers
            papers_result = self.conn.execute("""
                SELECT id, paper_id, title, abstract, source 
                FROM papers
            """).fetchall()

            papers = []
            for paper_row in papers_result:
                paper_id = paper_row[1]

                # Get figures for this paper
                figures_result = self.conn.execute("""
                    SELECT id, label, caption, figure_url 
                    FROM figures 
                    WHERE paper_id = ?
                """, (paper_id,)).fetchall()

                figures = []
                for fig_row in figures_result:
                    fig_id = fig_row[0]

                    # Get entities for this figure
                    entities_result = self.conn.execute("""
                        SELECT e.id, e.name, e.type
                        FROM entities e
                        JOIN figure_entities fe ON e.id = fe.entity_id
                        WHERE fe.figure_id = ?
                    """, (fig_id,)).fetchall()

                    entities = [
                        Entity(
                            text=entity_row[1],
                            type=entity_row[2],
                            start=-1,  # Default to -1 as these may not be stored
                            end=-1  # Default to -1 as these may not be stored
                        )
                        for entity_row in entities_result
                    ]

                    figures.append(Figure(
                        label=fig_row[1],
                        caption=fig_row[2],
                        url=fig_row[3],
                        entities=entities
                    ))

                papers.append(Paper(
                    paper_id=paper_id,
                    pmc_id=paper_id,  # Add pmc_id for compatibility with test_batch_ingest.py
                    title=paper_row[2],
                    abstract=paper_row[3],
                    figures=figures
                ))

            return papers
        except Exception as e:
            logger.error(f"Error getting papers: {e}")
            return []

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

    def get_paper_with_details(self, paper_id: str) -> Optional[Paper]:
        """
        Get a paper with all its figures and entities from the database.
        Returns None if the paper doesn't exist.
        """
        try:
            # Get paper details
            paper_result = self.conn.execute("""
                SELECT id, paper_id, title, abstract, source 
                FROM papers 
                WHERE paper_id = ?
            """, (paper_id,)).fetchone()

            if not paper_result:
                return None

            # Get figures for this paper
            figures_result = self.conn.execute("""
                SELECT id, label, caption, figure_url 
                FROM figures 
                WHERE paper_id = ?
                ORDER BY label  -- Ensure figures are in order
            """, (paper_id,)).fetchall()

            figures = []
            for fig_row in figures_result:
                fig_id = fig_row[0]

                # Get entities for this figure
                entities_result = self.conn.execute("""
                    SELECT e.id, e.name, e.type
                    FROM entities e
                    JOIN figure_entities fe ON e.id = fe.entity_id
                    WHERE fe.figure_id = ?
                """, (fig_id,)).fetchall()

                entities = [
                    Entity(
                        text=entity_row[1],
                        type=entity_row[2],
                        start=-1,  # Default to -1 as these may not be stored
                        end=-1  # Default to -1 as these may not be stored
                    )
                    for entity_row in entities_result
                ]

                figures.append(Figure(
                    label=fig_row[1],
                    caption=fig_row[2],
                    url=fig_row[3],
                    entities=entities
                ))

            return Paper(
                paper_id=paper_id,
                title=paper_result[2],
                abstract=paper_result[3],
                figures=figures
            )

        except Exception as e:
            logger.error(f"Error retrieving paper {paper_id}: {e}")
            return None

    def check_paper_completeness(self, paper_id: str) -> Tuple[bool, str]:
        """
        Check if a paper exists in the database and has complete data.
        
        Returns:
            Tuple[bool, str]: (is_complete, reason)
            - is_complete: True if paper exists and has all required data
            - reason: Description of why the paper is incomplete or "complete"
        """
        try:
            # Check if paper exists
            paper_result = self.conn.execute("""
                SELECT p.id, p.title, p.abstract,
                       COUNT(DISTINCT f.id) as figure_count,
                       COUNT(DISTINCT fe.id) as entity_count
                FROM papers p
                LEFT JOIN figures f ON p.paper_id = f.paper_id
                LEFT JOIN figure_entities fe ON f.id = fe.figure_id
                WHERE p.paper_id = ?
                GROUP BY p.id, p.title, p.abstract
            """, (paper_id,)).fetchone()

            if not paper_result:
                return False, "Paper not found in database"

            paper_id, title, abstract, figure_count, entity_count = paper_result

            if not title or not abstract:
                return False, "Missing title or abstract"

            if figure_count == 0:
                return False, "No figures found"

            if entity_count == 0:
                return False, "No entities found"

            return True, "complete"

        except Exception as e:
            logger.error(f"Error checking paper completeness for {paper_id}: {e}")
            return False, f"Database error: {str(e)}"