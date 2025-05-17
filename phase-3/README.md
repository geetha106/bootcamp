## Folder structure

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

## Usage 

```bash
python -m scripts.inspect_db
```

## Sample usage examples for the batch processing functionality
1. Single paper ingestion:

```bash
python -m cli.cli ingest PMC1790863
```

2. Batch ingestion from file:

```bash
python -m cli.cli ingest test.txt
```

3. Batch ingestion of multiple IDs:

```bash
python -m cli.cli batch PMC7696669 17299597
```

4. To see terminal output in csv format:

```bash
python -m cli.cli batch PMC7696669 29355051 --format csv
```

5. To see terminal output in csv format:

```bash
python -m cli.cli batch PMC7696669 17299597 --format json
python -m cli.cli batch PMC7696669 29355051 --output results.json
```

6. Resetting the database:

```bash
python test_batch_ingest.py --reset
```

7. Display items in the database:

```bash
python test_batch_ingest.py --display
```

8. Watching a folder for new files:

```bash
python -m cli.cli watch --folder-path data/watch --interval 30
```

## Notes

1. If we send in the PMCID and PMID for the same paper, as they both represent the same paper, Papers in the DB will be - 1 only.
