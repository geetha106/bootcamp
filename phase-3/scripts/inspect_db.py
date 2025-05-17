import duckdb
from storage.duckdb_backend import DuckDBStorage

conn = duckdb.connect("data/figurex.db")

db = DuckDBStorage()

print("Papers:")
for row in db.conn.execute("SELECT * FROM papers").fetchall():
    print(row)

print("\nFigures:")
for row in db.conn.execute("SELECT * FROM figures").fetchall():
    print(row)

print("\nEntities:")
for row in db.conn.execute("SELECT * FROM entities").fetchall():
    print(row)

print("\nFigure-Entity Links:")
for row in db.conn.execute("SELECT * FROM figure_entities").fetchall():
    print(row)
