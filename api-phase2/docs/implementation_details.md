# FigureX: Implementation Details

## Code Organization

The FigureX codebase follows a modular structure with clear separation of concerns:

```
figure-captions-extraction/                         # PyPI package root
├── api/                         # REST API logic (FastAPI)
│   ├── auth.py                  # API key authentication
│   ├── main.py                  # FastAPI app initialization
│   ├── models.py                # API request/response models
│   ├── routes.py                # API endpoints
│   ├── static/                  # Static assets for dashboard
│   └── templates/               # Jinja2 templates for dashboard
├── cli/                         # CLI commands (Typer)
│   └── cli.py                   # Typer CLI entrypoint
├── config/                      # Config loading/parsing
│   └── config.py                # Pydantic-based config handling
├── ingestion/                   # Ingestion logic for PMC, PMID, etc.
│   ├── base.py                  # Base classes for ingestors
│   ├── id_converter.py          # PMC ID ↔ PMID conversion
│   ├── paper_processor.py       # Paper processing orchestration
│   ├── pmc_ingestor.py          # PMC BioC ingestion logic
│   └── pubtator_client.py       # PubTator entity extraction
├── processing/                  # Data cleaning, deduplication
│   ├── caption_cleaner.py       # Clean/normalize captions
│   └── entity_mapper.py         # Map entities to captions
├── storage/                     # DuckDB + future-extensible storage
│   ├── base.py                  # Storage interface
│   ├── duckdb_backend.py        # DuckDB implementation
│   └── schema.sql               # SQL schema for tables
├── models/                      # Pydantic models for core entities
│   ├── paper.py                 # Paper, Figure, Entity models
│   └── responses.py             # API response schemas
├── utils/                       # Utility functions
│   ├── logging.py               # Rich-based logging setup
│   └── export.py                # Export functionality
├── watcher.py                   # Watched directory processor
├── run_api.py                   # API server entry point
├── settings.yaml                # Default config
├── requirements.txt             # Dependencies
├── Makefile                     # Dev and operational tasks
├── Dockerfile                   # Docker container setup
└── README.md                    # Overview and usage guide
```

## Key Components

### 1. Paper Processor

The `PaperProcessor` class orchestrates the entire ingestion workflow:

```python
class PaperProcessor:
    def __init__(self):
        self.pmc_ingestor = PMCIngestor()
        self.pubtator_client = PubTatorClient()
        self.storage = DuckDBStorage()
        self.logger = get_logger("paper_processor")
    
    def process_with_details(self, paper_id):
        # Normalize ID
        original_id, pmc_id, pmid = normalize_paper_id(paper_id)
        
        # Check if paper exists in database
        if self.storage.paper_exists(pmc_id or pmid):
            self.logger.info(f"Found complete paper in database: {pmc_id or pmid}")
            return {
                "paper_id": original_id,
                "status": "success",
                "message": "Paper already exists in database"
            }
        
        # Process paper based on available IDs
        if pmc_id:
            return self._process_pmc(pmc_id, original_id)
        elif pmid:
            return self._process_pmid(pmid, original_id)
        else:
            return {
                "paper_id": original_id,
                "status": "error",
                "message": "Could not resolve paper ID"
            }
```

### 2. Storage Backend

The DuckDB storage backend provides SQL-based storage with an embedded database:

```python
class DuckDBStorage(StorageBackend):
    def __init__(self, db_path="data/figurex.db"):
        self.db_path = db_path
        self.logger = get_logger("storage.duckdb")
        self._ensure_db_dir()
        self._init_schema()
    
    def _ensure_db_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_schema(self):
        with self._get_connection() as conn:
            with open("storage/schema.sql", "r") as f:
                schema_sql = f.read()
                conn.execute(schema_sql)
                self.logger.info("Database schema initialized")
```

### 3. API Implementation

The FastAPI implementation provides a RESTful interface:

```python
# API router setup
router = APIRouter()
logger = get_logger("api.routes")

@router.post("/process", response_model=ProcessingResponse)
async def process_ids(
    request: IDListRequest,
    api_key: str = Security(get_api_key)
):
    """Process a list of paper IDs (PMC IDs or PMIDs)"""
    if not request.ids:
        raise HTTPException(status_code=400, detail="No paper IDs provided")
    
    # Process each paper ID
    results = []
    for paper_id in request.ids:
        result = processor.process_with_details(paper_id)
        results.append(result)
    
    return ProcessingResponse(
        success_count=sum(1 for r in results if r["status"] == "success"),
        failed_count=sum(1 for r in results if r["status"] != "success"),
        processed_ids=results
    )
```

### 4. Watched Directory System

The watched directory system monitors for new files and processes them automatically:

```python
class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.txt'):
            logger.info(f"New file detected: {event.src_path}")
            process_file(event.src_path)

def main():
    logger.info(f"Starting to monitor {UNPROCESSED_DIR} for new .txt files")
    
    # Process any existing files
    for file_path in UNPROCESSED_DIR.glob('*.txt'):
        logger.info(f"Found existing file: {file_path}")
        process_file(str(file_path))
    
    # Set up the file watcher
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, str(UNPROCESSED_DIR), recursive=False)
    observer.start()
```

### 5. Authentication System

API key authentication is implemented using FastAPI's security dependencies:

```python
def get_api_key(
    api_key_query: Optional[str] = Query(None, alias="api_key")
) -> str:
    """Get and validate API key from query parameter"""
    if not api_key_query:
        raise HTTPException(
            status_code=401,
            detail="API key is required as query parameter (api_key)",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Get the configured API key
    config = get_config()
    valid_api_key = config.api.api_key
    
    if api_key_query != valid_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key_query
```

## Design Patterns

### 1. Repository Pattern

The storage backend implements the repository pattern, abstracting database operations:

```python
class StorageBackend(ABC):
    @abstractmethod
    def save_paper(self, paper: Paper) -> bool:
        pass
    
    @abstractmethod
    def get_paper(self, paper_id: str) -> Optional[Paper]:
        pass
    
    @abstractmethod
    def get_papers(self) -> List[Paper]:
        pass
    
    @abstractmethod
    def paper_exists(self, paper_id: str) -> bool:
        pass
```

### 2. Strategy Pattern

The ingestion system uses the strategy pattern for different ingestion sources:

```python
class Ingestor(ABC):
    @abstractmethod
    def ingest(self, paper_id: str) -> Optional[Paper]:
        pass

class PMCIngestor(Ingestor):
    def ingest(self, pmc_id: str) -> Optional[Paper]:
        # PMC-specific ingestion logic
        pass

class PMIDIngestor(Ingestor):
    def ingest(self, pmid: str) -> Optional[Paper]:
        # PMID-specific ingestion logic
        pass
```

### 3. Facade Pattern

The `PaperProcessor` class acts as a facade, hiding the complexity of the ingestion process:

```python
def process_paper_ids(paper_ids):
    """
    Process a list of paper IDs (PMC IDs or PMIDs)
    This provides a simple interface to the complex processing logic
    """
    results = []
    
    for paper_id in paper_ids:
        try:
            # Complex processing logic hidden behind this facade
            result = processor.process_with_details(paper_id)
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing paper {paper_id}: {e}")
            results.append({
                "paper_id": paper_id,
                "status": "error",
                "message": str(e)
            })
    
    return results
```

### 4. Dependency Injection

FastAPI's dependency injection is used for authentication and configuration:

```python
@router.get("/papers/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    api_key: str = Security(get_api_key)
):
    """Get a specific paper by ID"""
    try:
        paper = storage.get_paper(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        return paper_to_response(paper)
    except Exception as e:
        logger.error(f"Error retrieving paper {paper_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## Clean Code Practices

### 1. Comprehensive Logging

The system uses structured logging throughout:

```python
def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RichHandler(rich_tracebacks=True)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

### 2. Error Handling

Robust error handling is implemented throughout the codebase:

```python
def process_file(file_path):
    """Process a file containing paper IDs"""
    try:
        # Processing logic
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        # Recovery logic
        try:
            if os.path.exists(underprocess_path):
                shutil.move(underprocess_path, UNPROCESSED_DIR / filename)
                logger.info(f"Moved {filename} back to unprocessed directory due to error")
        except Exception:
            logger.exception("Failed to move file after error")
```

### 3. Type Hints

Python type hints are used throughout the codebase:

```python
def normalize_paper_id(paper_id: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Normalize a paper ID to get both PMC ID and PMID
    Returns (original_id, pmc_id, pmid)
    """
    original_id = paper_id.strip()
    pmc_id = None
    pmid = None
    
    # Normalization logic
    
    return original_id, pmc_id, pmid
```

### 4. Modular Design

The code is organized into small, focused modules with clear responsibilities.

## Performance Optimizations

1. **Database Indexing**: Key fields are indexed for faster queries
2. **Batch Processing**: Papers are processed in batches for efficiency
3. **Caching**: Frequently accessed data is cached to reduce API calls
4. **Asynchronous Processing**: Background tasks for long-running operations 