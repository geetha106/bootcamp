# FigureX API Dashboard

This module provides a FastAPI dashboard for the FigureX system, allowing users to upload paper IDs (PMC IDs or PMIDs) and extract figure captions and related metadata.

## Features

- Upload a file containing paper IDs (PMC IDs or PMIDs)
- Enter paper IDs manually
- View processed papers and their figures
- Export results in JSON or CSV format
- RESTful API endpoints for programmatic access

## Installation

1. Make sure you have all dependencies installed:

```bash
pip install -r requirements.txt
```

2. Run the API server:

```bash
python run_api.py
```

3. Open your browser and navigate to `http://localhost:8000`

## API Endpoints

The following API endpoints are available:

- `GET /api/health` - Health check endpoint
- `POST /api/process` - Process a list of paper IDs
- `POST /api/upload` - Upload a file containing paper IDs
- `GET /api/papers` - Get all papers from the database
- `GET /api/papers/{paper_id}` - Get a specific paper by ID
- `GET /api/export` - Export papers data in JSON or CSV format

## Usage Examples

### Process paper IDs using the API

```python
import requests
import json

# Process paper IDs
response = requests.post(
    "http://localhost:8000/api/process",
    json={"ids": ["PMC1790863", "PMC7696669", "35871145"]}
)

# Print results
print(json.dumps(response.json(), indent=2))
```

### Upload a file using the API

```python
import requests

# Upload a file containing paper IDs
with open("paper_ids.txt", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/upload",
        files={"file": f}
    )

# Print results
print(response.json())
```

## Dashboard Usage

1. **Upload Paper IDs**:
   - Upload a file containing paper IDs (one per line)
   - Or enter paper IDs manually (one per line)
   - Click "Process Paper IDs" to start processing

2. **View Papers**:
   - Click on the "Papers" tab to view all processed papers
   - Click on a paper to view its details and figures

3. **Export Results**:
   - Click the "Export Results" button to download the results in JSON or CSV format

## File Formats

- **Text file (.txt)**: One paper ID per line
- **CSV file (.csv)**: Paper IDs in the first column 