# FigureX: Design Document

## Architecture Overview

FigureX is designed as a modular system for extracting and analyzing figure data from scientific papers. The architecture follows a layered approach with clear separation of concerns:

1. **User Interface Layer**
   - CLI interface for command-line operations
   - REST API for web-based access
   - Web dashboard for visual interaction

2. **Application Layer**
   - Paper processing pipeline
   - Entity extraction and analysis
   - Data transformation and export

3. **Data Layer**
   - DuckDB storage backend
   - File-based configuration
   - Watched directory system for batch processing

## Key Components and Interactions

### Ingestion Components
- **Paper Processor**: Coordinates the ingestion workflow for papers
- **PMC Ingestor**: Extracts data from PubMed Central using BioC format
- **PubTator Client**: Retrieves entity annotations from PubTator
- **ID Converter**: Normalizes and converts between PMC IDs and PMIDs
- **Watcher**: Monitors directories for new paper ID files to process

### Processing Components
- **Caption Cleaner**: Normalizes and cleans figure captions
- **Entity Mapper**: Maps entities to captions and deduplicates
- **Data Transformer**: Converts between internal models and API responses

### Storage Components
- **DuckDB Backend**: Provides SQL-based storage for paper data
- **Schema Manager**: Handles database schema creation and updates

### API Components
- **FastAPI Router**: Defines API endpoints and request handling
- **Authentication**: Implements API key-based security
- **Response Models**: Defines structured API responses

### UI Components
- **Dashboard**: Web-based UI for interacting with the system
- **Templates**: Jinja2 templates for rendering HTML pages

## Component Interactions

1. **Ingestion Flow**:
   ```
   User → CLI/API → Paper Processor → PMC Ingestor → PubTator Client → Storage
   ```

2. **Watched Directory Flow**:
   ```
   File Drop → Watcher → Paper Processor → Storage
   ```

3. **Query Flow**:
   ```
   User → API/CLI → Storage → Response Transformation → User
   ```

## Dependencies and Justifications

### Core Dependencies
- **FastAPI**: Modern, high-performance web framework for APIs
  - Justification: Provides automatic OpenAPI documentation, dependency injection, and async support
  
- **DuckDB**: Embedded analytical database
  - Justification: Lightweight, columnar storage optimized for analytical queries, no separate server needed
  
- **Typer**: CLI framework based on Python type hints
  - Justification: Creates intuitive CLI interfaces with minimal code
  
- **Pydantic**: Data validation using Python type annotations
  - Justification: Ensures data integrity throughout the application
  
- **Requests**: HTTP library for API calls
  - Justification: Industry standard for HTTP requests in Python
  
- **Watchdog**: API for monitoring file system events
  - Justification: Provides reliable file system monitoring for the watched directory feature

### NLP and Data Processing
- **spaCy**: NLP toolkit for entity recognition
  - Justification: Production-ready NLP capabilities with pre-trained models
  
- **BeautifulSoup4**: HTML parsing library
  - Justification: Robust HTML parsing for extracting content from PMC

### Web and API
- **Uvicorn**: ASGI server for FastAPI
  - Justification: High-performance server recommended for FastAPI
  
- **Jinja2**: Templating engine
  - Justification: Powerful templating for HTML generation
  
- **Python-multipart**: Multipart form parsing
  - Justification: Handles file uploads in the API

## Deployment Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    User / API   │     │  FigureX Core   │     │  External APIs  │
│    Consumers    │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   HTTP/REST     │     │  Paper          │     │  PubMed Central │
│   Interface     │◄────┤  Processing     │◄────┤  API            │
└────────┬────────┘     └────────┬────────┘     └─────────────────┘
         │                       │                       ▲
         ▼                       ▼                       │
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web           │     │  Storage        │     │  PubTator       │
│   Dashboard     │     │  (DuckDB)       │     │  API            │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Design Decisions

### Use of DuckDB
DuckDB was chosen over traditional SQL databases because:
1. It's embedded (no server setup required)
2. Optimized for analytical queries
3. Supports SQL standard
4. Lightweight deployment footprint

### API Key Authentication
Simple API key authentication was implemented because:
1. Appropriate security level for this type of application
2. Low overhead compared to OAuth or JWT
3. Easy integration with various clients

### Watched Directory System
The watched directory approach provides:
1. Simple integration with external systems
2. Batch processing capabilities
3. Clear workflow visualization (unprocessed → underprocess → processed)
4. Fault tolerance through file state tracking

### Modular Component Design
The system is designed with modularity to allow:
1. Easy replacement of components (e.g., different storage backends)
2. Independent testing of components
3. Clear separation of concerns
4. Future extensibility 