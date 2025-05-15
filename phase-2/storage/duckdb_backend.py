#duckdb_backend.py
import duckdb
import os
from models.paper import Paper, Figure, Entity


class DuckDBStorage:
    def __init__(self, db_path: str = "data/figurex.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._initialize_schema()

    def _initialize_schema(self):
        with open("storage/schema.sql", "r") as f:
            self.conn.execute(f.read())

    def save_paper(self, paper: Paper):
        # Check if paper_id already exists
        existing = self.conn.execute(
            "SELECT id FROM papers WHERE paper_id = ?", (paper.paper_id,)
        ).fetchone()

        if existing:
            paper_row_id = existing[0]
            # Update paper info if needed
            self.conn.execute(
                "UPDATE papers SET title = ?, abstract = ?, source = ? WHERE id = ?",
                (paper.title, paper.abstract, "PMC", paper_row_id)
            )
        else:
            # Insert new paper
            paper_row_id = self.get_next_id("papers")
            self.conn.execute(
                "INSERT INTO papers (id, paper_id, title, abstract, source) VALUES (?, ?, ?, ?, ?)",
                (paper_row_id, paper.paper_id, paper.title, paper.abstract, "PMC")
            )

        # Now save figures
        for fig in paper.figures:
            fig_row_id = self.get_next_id("figures")
            self.conn.execute(
                "INSERT INTO figures (id, paper_id, caption, figure_url) VALUES (?, ?, ?, ?)",
                (fig_row_id, paper.paper_id, fig.caption, fig.url)
            )

            for entity in fig.entities:
                entity_row = self.conn.execute(
                    "SELECT id FROM entities WHERE name = ?", (entity.text,)
                ).fetchone()

                if entity_row is None:
                    entity_row_id = self.get_next_id("entities")
                    self.conn.execute(
                        "INSERT INTO entities (id, name) VALUES (?, ?)",
                        (entity_row_id, entity.text)
                    )
                else:
                    entity_row_id = entity_row[0]

                fe_id = self.get_next_id("figure_entities")
                self.conn.execute(
                    "INSERT INTO figure_entities (id, figure_id, entity_id) VALUES (?, ?, ?)",
                    (fe_id, fig_row_id, entity_row_id)
                )

    def get_next_id(self, table_name: str) -> int:
        result = self.conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}").fetchone()
        return result[0]
