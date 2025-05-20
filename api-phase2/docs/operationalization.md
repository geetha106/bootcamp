# FigureX: Operationalization Guide

This document provides instructions for deploying, configuring, and using the FigureX system in various scenarios.

## Deployment Options

### Local Deployment

1. **Prerequisites**:
   - Python 3.8 or higher
   - pip package manager
   - Git (for cloning the repository)

2. **Installation**:
   ```bash
   # Clone the repository
   git clone https://github.com/geetharuttala/bootcaamp.git
   cd figure-captions-extraction
   
   # Install dependencies
   make install
   # or manually:
   pip install -r requirements.txt
   ```

3. **Configuration**:
   - Copy `settings.yaml.example` to `settings.yaml`
   - Edit the settings as needed (API key, database path, etc.)
   ```bash
   cp settings.yaml.example settings.yaml
   nano settings.yaml
   ```

4. **Running the API**:
   ```bash
   make api-run
   # or manually:
   python run_api.py
   ```

5. **Running the Watched Directory Processor**:
   ```bash
   make run
   # or manually:
   python watcher.py
   ```

### Docker Deployment

1. **Prerequisites**:
   - Docker installed
   - Docker Compose (optional, for multi-container setup)

2. **Building the Docker Image**:
   ```bash
   make docker-build
   # or manually:
   docker build -t figurex:latest .
   ```

3. **Running the Docker Container**:
   ```bash
   make docker-run
   # or manually:
   docker run -p 8000:8000 -v $(pwd)/data:/app/data figurex:latest
   ```
   
## Configuration

### Settings File (settings.yaml)

```yaml
# API Configuration
api:
  # API key for authentication
  api_key: "figurex2023"
  # Base URL for the API
  url: "http://localhost:8000/api"

# Storage Configuration
storage:
  # Path to the DuckDB database file
  db_path: "data/figurex.db"
  # Maximum number of papers to keep in memory cache
  cache_size: 100

# Ingestion Configuration
ingestion:
  # NCBI API key for PubMed Central and PubTator
  ncbi_api_key: ""
  # Maximum number of concurrent requests
  max_concurrent_requests: 5
  # Request timeout in seconds
  timeout: 30
  # Retry count for failed requests
  retry_count: 3

# Logging Configuration
logging:
  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  level: "INFO"
  # Path to log file
  file: "logs/figurex.log"
  # Maximum log file size in MB
  max_size: 10
  # Number of backup log files to keep
  backup_count: 3
```

### Environment Variables

You can override settings using environment variables:

- `FIGUREX_API_KEY`: API key for authentication
- `FIGUREX_DB_PATH`: Path to the DuckDB database file
- `FIGUREX_NCBI_API_KEY`: NCBI API key for PubMed Central and PubTator
- `FIGUREX_LOG_LEVEL`: Log level

## Usage Scenarios

### Scenario 1: Processing a Batch of Paper IDs via CLI

```bash
# Process multiple paper IDs
python -m cli.cli batch PMC7696669 29355051 17299597

# Export the results to a JSON file
python -m cli.cli batch PMC7696669 29355051 --output results.json

# Export the results to a CSV file
python -m cli.cli batch PMC7696669 29355051 --format csv --output results.csv
```

### Scenario 2: Processing a File of Paper IDs via CLI

```bash
# Create a file with paper IDs
echo -e "PMC7696669\n29355051\n17299597" > paper_ids.txt

# Process the file
python -m cli.cli ingest paper_ids.txt
```

### Scenario 3: Using the Watched Directory System

```bash
# Start the watched directory processor
make run

# Place a file in the watched directory
echo -e "PMC7696669\n29355051" > watched_dir/unprocessed/batch1.txt
echo -e "17299597\nPMC1790863" > watched_dir/unprocessed/batch2.txt

# Files will be automatically processed and moved to the processed directory
```

### Scenario 4: Using the REST API

```bash
# Health check
curl http://localhost:8000/api/health

# Process paper IDs - Note: Use query parameter for API key, not header
# Option 1: Using file upload (more reliable)
echo "PMC1790863
29355051" > tests.txt
curl -s -X POST "http://localhost:8000/api/upload?api_key=figurex2023" -F "file=@tests.txt"

# Option 2: Using JSON payload (may have issues in some terminals)
curl -s -X POST "http://localhost:8000/api/process?api_key=figurex2023" \
  -H "Content-Type: application/json" \
  -d "{\"ids\": [\"PMC1790863\", \"29355051\"]}"

# Get all papers
curl "http://localhost:8000/api/papers?api_key=figurex2023"

# Get a specific paper
curl "http://localhost:8000/api/papers/PMC1790863?api_key=figurex2023"

# Search papers
curl "http://localhost:8000/api/search?title_contains=cancer&entity_type=Disease&api_key=figurex2023"

# Export data
curl "http://localhost:8000/api/export?format=json&paper_ids=PMC1790863&paper_ids=29355051&api_key=figurex2023" \
  -o exported_data.json
```

### Scenario 5: Using the Web Dashboard

1. Start the API server:
   ```bash
   make api-run
   ```

2. Open a web browser and navigate to `http://localhost:8000`

3. Enter your API key when prompted

4. Use the dashboard to:
   - Upload a file with paper IDs
   - View processed papers and their figures
   - Search for papers by various criteria
   - Export data in JSON or CSV format

## Monitoring and Maintenance

### Log Files

The system generates log files that can be used for monitoring and troubleshooting:

- API logs: `logs/api.log`
- Watcher logs: `logs/watcher.log`
- General logs: `logs/figurex.log`

### Database Maintenance

The DuckDB database may need occasional maintenance:

```bash
# Backup the database
cp data/figurex.db data/figurex.db.backup

# Reset the database (if needed)
python -m cli.cli reset --force
```

### Updating the System

To update the system to a new version:

```bash
# Pull the latest changes
git pull

# Install any new dependencies
make install

# Restart the services
make api-run
make run
```

## Troubleshooting

### Common Issues and Solutions

1. **API Key Authentication Failures**:
   - Check that the API key in your request matches the one in `settings.yaml`
   - Ensure the API key is provided as the `api_key` query parameter (e.g., `?api_key=figurex2023`)

2. **Paper Processing Failures**:
   - Check internet connectivity to PubMed Central and PubTator
   - Verify that the paper IDs are valid
   - Check the logs for specific error messages

3. **Watched Directory Issues**:
   - Ensure the directories exist: `watched_dir/{unprocessed,underprocess,processed}`
   - Check file permissions
   - Verify that the watcher process is running

4. **Database Issues**:
   - Check disk space
   - Ensure the database directory is writable
   - Try resetting the database if it becomes corrupted

### Getting Help

If you encounter issues that you cannot resolve, please:

1. Check the logs for error messages
2. Consult the documentation
3. Submit an issue on the project's GitHub repository with:
   - A description of the problem
   - Steps to reproduce
   - Relevant log output
   - Your system information 