from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks, Query, Security
from fastapi.responses import JSONResponse, FileResponse
import os
import tempfile
from typing import List, Optional, Dict, Any
import io
import csv
import json
from datetime import datetime

from api.models import IDListRequest, ProcessingResponse, PaperResponse, HealthResponse, PaperQueryParams, SearchResponse
from api.auth import get_api_key, get_api_key_optional
from ingestion.paper_processor import PaperProcessor
from storage.duckdb_backend import DuckDBStorage
from utils.export import BatchResultExporter
from utils.logging import get_logger
from config.config import get_config
from ingestion.id_converter import normalize_paper_id

# Create router
router = APIRouter()
logger = get_logger("api.routes")

# Initialize processor and storage
processor = PaperProcessor()
config = get_config()
storage = DuckDBStorage(config.storage.db_path)

# Store the most recently processed paper IDs for export
recently_processed_ids = []


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse()


@router.post("/process", response_model=ProcessingResponse)
async def process_ids(
    request: IDListRequest,
    api_key: str = Security(get_api_key)
):
    """
    Process a list of paper IDs (PMC IDs or PMIDs)
    """
    global recently_processed_ids
    
    if not request.ids:
        raise HTTPException(status_code=400, detail="No paper IDs provided")

    results = []
    success_count = 0
    failed_count = 0
    successful_ids = []

    for paper_id in request.ids:
        try:
            # Normalize the paper ID to get both PMC ID and PMID
            original_id, pmc_id, pmid = normalize_paper_id(paper_id)
            
            # Log the ID conversion for debugging
            if pmid and pmc_id:
                logger.info(f"Converted ID: Original={original_id}, PMC={pmc_id}, PMID={pmid}")
            elif pmid:
                logger.info(f"Using PMID: {pmid} (no PMC ID found)")
            elif pmc_id:
                logger.info(f"Using PMC ID: {pmc_id} (no PMID found)")
            else:
                logger.warning(f"Could not resolve ID: {original_id}")
            
            # Use the process_with_details method which handles both PMC IDs and PMIDs
            result = processor.process_with_details(paper_id)
            results.append(result)
            
            if result["status"] == "success":
                success_count += 1
                successful_ids.append(paper_id)
                logger.info(f"Successfully processed paper: {paper_id}")
            else:
                failed_count += 1
                logger.error(f"Failed to process paper: {paper_id}, Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            failed_count += 1
            logger.error(f"Error processing paper {paper_id}: {e}")
            results.append({
                "paper_id": paper_id,
                "status": "error",
                "message": str(e)
            })

    # Store the successfully processed IDs for later export
    recently_processed_ids = successful_ids

    return ProcessingResponse(
        success_count=success_count,
        failed_count=failed_count,
        processed_ids=results
    )


@router.post("/upload", response_model=ProcessingResponse)
async def upload_id_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    api_key: str = Security(get_api_key)
):
    """
    Upload a file containing paper IDs (one per line) and process them
    """
    global recently_processed_ids
    
    if not file.filename.endswith(('.txt', '.csv')):
        raise HTTPException(status_code=400, detail="Only .txt or .csv files are supported")

    # Read file content
    content = await file.read()
    paper_ids = []
    
    # Parse file content based on file type
    if file.filename.endswith('.txt'):
        # For text files, split by lines
        paper_ids = [line.strip() for line in content.decode('utf-8').splitlines() if line.strip()]
    elif file.filename.endswith('.csv'):
        # For CSV files, read the first column
        csv_reader = csv.reader(io.StringIO(content.decode('utf-8')))
        for row in csv_reader:
            if row and row[0].strip():
                paper_ids.append(row[0].strip())

    if not paper_ids:
        raise HTTPException(status_code=400, detail="No paper IDs found in the uploaded file")

    # Process the paper IDs
    results = []
    success_count = 0
    failed_count = 0
    successful_ids = []

    for paper_id in paper_ids:
        try:
            # Normalize the paper ID to get both PMC ID and PMID
            original_id, pmc_id, pmid = normalize_paper_id(paper_id)
            
            # Log the ID conversion for debugging
            if pmid and pmc_id:
                logger.info(f"Converted ID: Original={original_id}, PMC={pmc_id}, PMID={pmid}")
            elif pmid:
                logger.info(f"Using PMID: {pmid} (no PMC ID found)")
            elif pmc_id:
                logger.info(f"Using PMC ID: {pmc_id} (no PMID found)")
            else:
                logger.warning(f"Could not resolve ID: {original_id}")
            
            # Use the process_with_details method which handles both PMC IDs and PMIDs
            result = processor.process_with_details(paper_id)
            results.append(result)
            
            if result["status"] == "success":
                success_count += 1
                successful_ids.append(paper_id)
                logger.info(f"Successfully processed paper: {paper_id}")
            else:
                failed_count += 1
                logger.error(f"Failed to process paper: {paper_id}, Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            failed_count += 1
            logger.error(f"Error processing paper {paper_id}: {e}")
            results.append({
                "paper_id": paper_id,
                "status": "error",
                "message": str(e)
            })

    # Store the successfully processed IDs for later export
    recently_processed_ids = successful_ids

    return ProcessingResponse(
        success_count=success_count,
        failed_count=failed_count,
        processed_ids=results
    )


@router.get("/papers", response_model=List[PaperResponse])
async def get_papers(
    api_key: str = Security(get_api_key)
):
    """
    Get all papers from the database
    """
    try:
        papers = storage.get_papers()
        response = []
        
        for paper in papers:
            figures_data = []
            for fig in paper.figures:
                figures_data.append({
                    "label": fig.label,
                    "caption": fig.caption,
                    "url": fig.url,
                    "entities": [{"text": e.text, "type": e.type} for e in fig.entities]
                })
                
            response.append({
                "paper_id": paper.paper_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "figure_count": len(paper.figures),
                "figures": figures_data
            })
            
        return response
    except Exception as e:
        logger.error(f"Error getting papers: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting papers: {str(e)}")


@router.get("/papers/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    api_key: str = Security(get_api_key)
):
    """
    Get a specific paper by ID
    """
    try:
        # Normalize the paper ID to get PMC ID
        original_id, pmc_id, pmid = normalize_paper_id(paper_id)
        
        if not pmc_id and pmid:
            # If we have a PMID but no PMC ID, try to convert it
            logger.info(f"Converting PMID {pmid} to PMC ID for retrieval")
            paper = storage.get_paper_with_details(pmid)
        else:
            # Use PMC ID for retrieval
            paper = storage.get_paper_with_details(pmc_id or paper_id)
        
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper with ID {paper_id} not found")
        
        figures_data = []
        for fig in paper.figures:
            figures_data.append({
                "label": fig.label,
                "caption": fig.caption,
                "url": fig.url,
                "entities": [{"text": e.text, "type": e.type} for e in fig.entities]
            })
            
        return {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "abstract": paper.abstract,
            "figure_count": len(paper.figures),
            "figures": figures_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paper {paper_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting paper: {str(e)}")


@router.get("/export")
async def export_data(
    format: str = Query("json", description="Export format (json or csv)"),
    use_recent: bool = Query(True, description="Use recently processed papers instead of all papers"),
    paper_ids: Optional[List[str]] = Query(None, description="Optional list of paper IDs to export"),
    api_key: str = Security(get_api_key)
):
    """
    Export papers data in JSON or CSV format
    """
    global recently_processed_ids
    
    try:
        # Determine which papers to export
        if paper_ids:
            # If specific IDs are provided, use those
            papers = []
            for pid in paper_ids:
                # Normalize the paper ID to get PMC ID
                original_id, pmc_id, pmid = normalize_paper_id(pid)
                paper = storage.get_paper_with_details(pmc_id or pid)
                if paper:
                    papers.append(paper)
        elif use_recent and recently_processed_ids:
            # If use_recent is True and we have recently processed IDs, use those
            papers = []
            for pid in recently_processed_ids:
                # Normalize the paper ID to get PMC ID
                original_id, pmc_id, pmid = normalize_paper_id(pid)
                paper = storage.get_paper_with_details(pmc_id or pid)
                if paper:
                    papers.append(paper)
        else:
            # Otherwise, get all papers
            papers = storage.get_papers()
        
        if not papers:
            raise HTTPException(status_code=404, detail="No papers found to export")
        
        # Create exporter
        exporter = BatchResultExporter()
        exporter.start_timing()  # Start timing to avoid the error
        
        # Prepare results in the format expected by the exporter
        results = []
        for paper in papers:
            figures_data = []
            for fig in paper.figures:
                figures_data.append({
                    "label": fig.label,
                    "caption": fig.caption,
                    "url": fig.url,
                    "entities": [{"text": e.text, "type": e.type} for e in fig.entities]
                })
                
            results.append({
                "paper_id": paper.paper_id,
                "status": "success",
                "title": paper.title,
                "abstract": paper.abstract,
                "figures": figures_data
            })
        
        # Format results
        formatted_output = exporter.format_results(results, format)
        
        # Create a temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = "json" if format == "json" else "csv"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}")
        
        # Write data to the file
        with open(temp_file.name, "w") as f:
            f.write(formatted_output)
        
        # Return the file as a download
        return FileResponse(
            path=temp_file.name,
            filename=f"figurex_export_{timestamp}.{file_extension}",
            media_type=f"application/{file_extension}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=f"Error exporting data: {str(e)}")


@router.get("/metadata")
async def get_metadata(
    format: str = Query("json", description="Format (json or csv)"),
    use_recent: bool = Query(True, description="Use recently processed papers instead of all papers"),
    paper_ids: Optional[List[str]] = Query(None, description="Optional list of paper IDs to get metadata for"),
    api_key: str = Security(get_api_key)
):
    """
    Get metadata for papers without downloading a file
    """
    global recently_processed_ids
    
    try:
        # Determine which papers to get metadata for
        if paper_ids:
            # If specific IDs are provided, use those
            papers = []
            for pid in paper_ids:
                # Normalize the paper ID to get PMC ID
                original_id, pmc_id, pmid = normalize_paper_id(pid)
                paper = storage.get_paper_with_details(pmc_id or pid)
                if paper:
                    papers.append(paper)
        elif use_recent and recently_processed_ids:
            # If use_recent is True and we have recently processed IDs, use those
            papers = []
            for pid in recently_processed_ids:
                # Normalize the paper ID to get PMC ID
                original_id, pmc_id, pmid = normalize_paper_id(pid)
                paper = storage.get_paper_with_details(pmc_id or pid)
                if paper:
                    papers.append(paper)
        else:
            # Otherwise, get all papers
            papers = storage.get_papers()
        
        if not papers:
            raise HTTPException(status_code=404, detail="No papers found")
        
        # Prepare results
        results = []
        for paper in papers:
            figures_data = []
            for fig in paper.figures:
                figures_data.append({
                    "label": fig.label,
                    "caption": fig.caption,
                    "url": fig.url,
                    "entities": [{"text": e.text, "type": e.type} for e in fig.entities]
                })
                
            results.append({
                "paper_id": paper.paper_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "figures": figures_data
            })
        
        # Return the results in the requested format
        if format.lower() == "csv":
            # For CSV, we need to flatten the data
            flattened_data = []
            for paper in results:
                for figure in paper["figures"]:
                    entities_text = ", ".join([f"{e['text']} ({e['type']})" for e in figure["entities"]])
                    flattened_data.append({
                        "paper_id": paper["paper_id"],
                        "title": paper["title"],
                        "figure_label": figure["label"],
                        "caption": figure["caption"],
                        "figure_url": figure["url"] or "",
                        "entities": entities_text
                    })
            
            # Convert to CSV string
            output = io.StringIO()
            if flattened_data:
                writer = csv.DictWriter(output, fieldnames=flattened_data[0].keys())
                writer.writeheader()
                writer.writerows(flattened_data)
                csv_string = output.getvalue()
                return JSONResponse(content={"format": "csv", "data": csv_string})
            else:
                return JSONResponse(content={"format": "csv", "data": ""})
        else:
            # Default to JSON
            return JSONResponse(content={"format": "json", "data": results})
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting metadata: {str(e)}")


# New search endpoints
@router.get("/search", response_model=SearchResponse)
async def search_papers(
    paper_ids: Optional[List[str]] = Query(None, description="Filter by paper IDs"),
    title_contains: Optional[str] = Query(None, description="Filter by title containing text"),
    abstract_contains: Optional[str] = Query(None, description="Filter by abstract containing text"),
    caption_contains: Optional[str] = Query(None, description="Filter by caption containing text"),
    entity_text: Optional[str] = Query(None, description="Filter by entity text"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(10, description="Maximum number of results to return"),
    offset: int = Query(0, description="Number of results to skip"),
    api_key: str = Security(get_api_key)
):
    """
    Search papers based on query parameters
    """
    try:
        # Build query params dictionary
        query_params = {
            "paper_ids": paper_ids,
            "title_contains": title_contains,
            "abstract_contains": abstract_contains,
            "caption_contains": caption_contains,
            "entity_text": entity_text,
            "entity_type": entity_type,
            "limit": limit,
            "offset": offset
        }
        
        # Remove None values
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        # Execute search
        total_count, papers = storage.search_papers(query_params)
        
        # Format results
        results = []
        for paper in papers:
            figures_data = []
            for fig in paper.figures:
                figures_data.append({
                    "label": fig.label,
                    "caption": fig.caption,
                    "url": fig.url,
                    "entities": [{"text": e.text, "type": e.type} for e in fig.entities]
                })
                
            results.append({
                "paper_id": paper.paper_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "figure_count": len(paper.figures),
                "figures": figures_data
            })
        
        # Create page info
        page_info = {
            "total_results": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(results) < total_count
        }
        
        return SearchResponse(
            total_results=total_count,
            results=results,
            query=query_params,
            page_info=page_info
        )
    except Exception as e:
        logger.error(f"Error searching papers: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching papers: {str(e)}")


@router.get("/entity-types")
async def get_entity_types(
    api_key: str = Security(get_api_key)
):
    """
    Get all unique entity types in the database
    """
    try:
        entity_types = storage.get_entity_types()
        return {"entity_types": entity_types}
    except Exception as e:
        logger.error(f"Error getting entity types: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting entity types: {str(e)}")


@router.get("/entity-stats")
async def get_entity_stats(
    api_key: str = Security(get_api_key)
):
    """
    Get statistics about entities in the database
    """
    try:
        entity_counts = storage.get_entity_counts()
        return {"entity_counts": entity_counts}
    except Exception as e:
        logger.error(f"Error getting entity statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting entity statistics: {str(e)}")
