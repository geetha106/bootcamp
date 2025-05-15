-- schema.sql
-- Updated schema with entity type and improved relationships

CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY,
    paper_id TEXT UNIQUE NOT NULL,
    title TEXT,
    abstract TEXT,
    source TEXT,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS figures (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL,
    caption TEXT,
    figure_url TEXT,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,  -- Added entity type (GENE, DISEASE, etc.)
    UNIQUE(name, type)  -- Entity names can repeat with different types
);

CREATE TABLE IF NOT EXISTS figure_entities (
    id INTEGER PRIMARY KEY,
    figure_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(figure_id) REFERENCES figures(id),
    FOREIGN KEY(entity_id) REFERENCES entities(id),
    UNIQUE(figure_id, entity_id)  -- Prevent duplicate relationships
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_papers_paper_id ON papers(paper_id);
CREATE INDEX IF NOT EXISTS idx_figures_paper_id ON figures(paper_id);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_figure_entities_figure_id ON figure_entities(figure_id);
CREATE INDEX IF NOT EXISTS idx_figure_entities_entity_id ON figure_entities(entity_id);