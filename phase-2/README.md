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
    
```

## Usage 

python -m cli.cli PMC1790863

python -m scripts.inspect_db

python test_ingest.py PMC7696669 –reset

## Sample usage examples for the batch processing functionality
Process multiple papers from command line

# Ingest multiple papers using the batch_ingest command

python -m cli.cli batch_ingest PMC1790863 PMC7696669 35871145

# Ingest multiple papers using a file (one ID per line)
python -m cli.cli ingest paper_ids.txt

# Reset database and process sample papers
python test_batch_ingest.py --reset

# Display database contents without processing
python test_batch_ingest.py --display

# Process specific papers and display results
python test_batch_ingest.py PMC1790863 PMC7696669 --display

# Watch a folder for new paper ID files
python -m cli.cli watch_folder --folder-path data/watch --interval 30
Sample paper_ids.txt format
# This is a comment
PMC1790863
PMC7696669
35871145  # This is a PMID

## Folder watching
The watch_folder command monitors a specified directory for .txt files containing paper IDs (one per line).
When a file is detected, it processes all IDs and moves the file to either:

processed/ - if processing was successful
failed/ - if errors occurred during processing

This enables automated batch processing of papers by simply dropping files into the watched directory.
