# FigureX: Scientific Paper Figure Extraction API

FigureX is a tool for extracting figure captions, entities, titles, abstracts, and figure URLs from scientific papers using PMC IDs or PMIDs.

## Features

- Extract figure captions and metadata from scientific papers
- Identify entities (genes, diseases, chemicals, etc.) in figure captions
- Search papers based on various criteria (titles, captions, entities)
- Export results in JSON or CSV format
- API key authentication for secure access
- Docker deployment support
- Watched directory for automatic processing of paper ID files

## Setup

1. Clone the repository
2. Install dependencies: `make install`
3. Configure settings in `settings.yaml`
4. Run the API server: `make api-run`

## Watched Directory Feature

FigureX includes a watched directory system that automatically processes files containing paper IDs:

1. Place `.txt` files with paper IDs (one per line) in the `watched_dir/unprocessed` folder
2. Files are automatically moved to `watched_dir/underprocess` during processing
3. After processing, files are moved to `watched_dir/processed`
4. Run the watched directory processor: `make run` (uses watcher.py)

The directory structure:
```
watched_dir/
├── unprocessed/    # Place new files here
├── underprocess/   # Files currently being processed
└── processed/      # Completed files
```

## API Authentication

The API uses API key authentication. The default API key is configured in `settings.yaml`:

```yaml
api:
  api_key: figurex2023
  url: http://localhost:8000/api
```

You can modify this key by editing the `settings.yaml` file directly.

### Authentication Method

You can use a query parameter:

```
curl "http://0.0.0.0:8000/api/entity-types?api_key=figurex2023"
```

The UI dashboard will prompt for the API key when needed.

## Using the Makefile

The project includes a Makefile with commands for common operations:

```bash
# Install dependencies
make install

# Run the watched directory processor
make run

# Run the API server
make api-run

# Run tests
make test

# Build Docker image
make docker-build

# Run Docker container
make docker-run
```

## CLI Commands

The system provides CLI commands for various operations:

```bash
# Ingest papers from a file
python -m cli.cli ingest test.txt

# Batch process multiple IDs
python -m cli.cli batch PMC7696669 29355051

# Output in CSV format
python -m cli.cli batch PMC7696669 29355051 --format csv

# Output in JSON format
python -m cli.cli batch PMC7696669 17299597 --format json

# Save output to a file
python -m cli.cli batch PMC7696669 29355051 --output results.json
python -m cli.cli batch PMC7696669 29355051 --output results.csv

# Reset the database
python -m cli.cli reset

# Force reset without confirmation
python -m cli.cli reset --force
```

## API Endpoints

### Health Check

```
GET /api/health
```

Check if the API is running. This endpoint doesn't require authentication.

**Example:**
```
curl http://0.0.0.0:8000/api/health
```

### Process Paper IDs

```
POST /api/process
```

Process a list of paper IDs (PMC IDs or PMIDs).

**Request Body:**
```json
{
  "ids": ["PMC1234567", "12345678"]
}
```

**Example:**
```bash
curl -X POST "http://0.0.0.0:8000/api/process" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: figurex2023" \
  -d '{"ids": ["PMC1790863", "29355051"]}'
```

### Upload Paper IDs

```
POST /api/upload
```

Upload a file containing paper IDs (one per line) and process them.

**Example:**
```bash
curl -X POST "http://0.0.0.0:8000/api/upload" \
  -H "X-API-Key: figurex2023" \
  -F "file=@test.txt"
```

### Get All Papers

```
GET /api/papers
```

Get all papers from the database.

**Example:**
```
curl "http://0.0.0.0:8000/api/papers?api_key=figurex2023"
```

### Get Paper Details

```
GET /api/papers/{paper_id}
```

Get a specific paper by ID.

**Example for a PMID:**
```
curl "http://0.0.0.0:8000/api/papers/17299597?api_key=figurex2023"
```
**For a PMC ID:**
```
curl "http://0.0.0.0:8000/api/papers/PMC7696669?api_key=figurex2023"
```

### Export Data

```
GET /api/export
```

Export paper data in JSON or CSV format.

**Query Parameters:**
- `format`: Export format (`json` or `csv`), default: `json`
- `use_recent`: Use recently processed papers instead of all papers, default: `true`
- `paper_ids`: Optional list of paper IDs to export

**Examples:**
```
# Export single paper
curl "http://0.0.0.0:8000/api/export?format=csv&paper_ids=17299597&api_key=figurex2023"

# Export multiple papers
curl "http://0.0.0.0:8000/api/export?format=json&paper_ids=PMC1790863&paper_ids=29355051&paper_ids=17299597&api_key=figurex2023"
```

### Get Metadata

```
GET /api/metadata
```

Get metadata for papers without downloading a file.

**Query Parameters:**
- `format`: Output format (`json` or `csv`), default: `json`
- `use_recent`: Use recently processed papers instead of all papers, default: `true`
- `paper_ids`: Optional list of paper IDs to get metadata for

**Example:**
```
curl "http://0.0.0.0:8000/api/metadata?paper_ids=PMC1790863&api_key=figurex2023"
```

### Search Papers

```
GET /api/search
```

Search papers based on query parameters.

**Query Parameters:**
- `paper_ids`: Filter by paper IDs
- `title_contains`: Filter by title containing text
- `abstract_contains`: Filter by abstract containing text
- `caption_contains`: Filter by caption containing text
- `entity_text`: Filter by entity text
- `entity_type`: Filter by entity type
- `limit`: Maximum number of results to return (default: 10)
- `offset`: Number of results to skip (default: 0)

**Examples:**
```
# Search by title
curl "http://0.0.0.0:8000/api/search?title_contains=cancer&limit=5&api_key=figurex2023"

# Search by entity
curl "http://0.0.0.0:8000/api/search?entity_text=virus&entity_type=Species&api_key=figurex2023"

# Combined search
curl "http://0.0.0.0:8000/api/search?title_contains=Quantifying&entity_type=Species&api_key=figurex2023"
```

### Get Entity Types

```
GET /api/entity-types
```

Get all unique entity types in the database.

**Example:**
```
curl "http://0.0.0.0:8000/api/entity-types?api_key=figurex2023"
```

### Get Entity Statistics

```
GET /api/entity-stats
```

Get statistics about entities in the database.

**Example:**
```
curl "http://0.0.0.0:8000/api/entity-stats?api_key=figurex2023"
```

## Configuration

The system can be configured using the `settings.yaml` file or environment variables:

- `FIGUREX_API_KEY`: API key for authentication
- `FIGUREX_API_URL`: Base URL for the API

## Dashboard

A web dashboard is available at the root URL (`/`) for interactive use.

## License

MIT

## Project Structure

```bash
figurex/                         # PyPI package root
├── api/                         # REST API logic (FastAPI)
│   └── routes.py                # Endpoints for querying and triggering ingestion
├── cli/                         # CLI commands (Typer)
│   └── cli.py                   # Typer CLI entrypoint
├── config/                      # Config loading/parsing
│   └── config.py                # Pydantic-based config handling
├── ingestion/                   # Ingestion logic for PMC, PMID, etc.
│   ├── base.py 
│   ├── id_converter.py
│   ├── paper_processor.py
│   ├── pmc_ingestor.py          # PMC BioC ingestion logic
│   ├── pubtator_client.py       # PubTator entity extraction logic
│   └── watcher.py               # Watched folder ingestion logic
├── processing/                  # Data cleaning, deduplication
│   ├── base.py
│   ├── caption_cleaner.py       # Clean/normalize captions
│   └── entity_mapper.py         # Deduplicate + map entities to captions
├── storage/                     # DuckDB + future-extensible storage logic
│   ├── base.py
│   ├── duckdb_backend.py        # DuckDB implementation
│   └── schema.sql               # SQL schema for tables
├── models/                      # Pydantic models for core entities
│   ├── paper.py                 # Paper, Figure, Entity models
│   └── responses.py             # API response schemas
├── utils/                       # Utility functions
│   ├── logging.py               # Rich-based logging setup
│   └── file_utils.py            # I/O helpers
├── main.py                      # Programmatic entrypoint (optional)
├── settings.toml                # Default config (storage, logging, etc.)
├── requirements.txt             # Dependencies
├── Makefile                     # Dev and operational tasks
├── Dockerfile                   # Docker container setup
├── README.md                    # Overview and usage guide
├── pyproject.toml               # Build system + PyPI metadata
├── docs/                        # MkDocs documentation site
│   ├── index.md                 # Home page
│   ├── architecture.md          # Design + architecture overview
│   ├── usage.md                 # CLI/API usage examples
│   └── deployment.md            # Deployment instructions
└── tests/                       # Unit + integration tests
    ├── test_ingestion.py
    ├── test_api.py
    ├── test_storage.py
    ├── test_batch_ingestion.py
    
```

## Batch Processing Examples

1. Batch ingestion from file:

```bash
python -m cli.cli ingest test.txt
```

2. Batch ingestion of multiple IDs:

```bash
python -m cli.cli batch 17299597 PMC7696669
```

3. To see terminal output in csv format:

```bash
python -m cli.cli batch PMC7696669 29355051 --format csv
```

4. To see terminal output in json format:

```bash
python -m cli.cli batch PMC7696669 17299597 --format json
```

5. To save the output to a file

```bash
python -m cli.cli batch PMC7696669 29355051 --output results.json
```

```bash
python -m cli.cli batch PMC7696669 29355051 --output results.csv
```

6. Resetting the database:

```bash
python -m cli.cli reset
```
Force rest without confirmation

```bash
python -m cli.cli reset --force
```

