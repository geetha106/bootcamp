CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY,
    paper_id TEXT UNIQUE NOT NULL,
    title TEXT,
    abstract TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS figures (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL,
    caption TEXT,
    figure_url TEXT,
    FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS figure_entities (
    id INTEGER PRIMARY KEY,
    figure_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    FOREIGN KEY(figure_id) REFERENCES figures(id),
    FOREIGN KEY(entity_id) REFERENCES entities(id)
);
