from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IDListRequest(BaseModel):
    """Request model for processing a list of paper IDs"""
    ids: List[str] = Field(..., description="List of paper IDs (PMC IDs or PMIDs)")


class ProcessingResponse(BaseModel):
    """Response model for processing results"""
    success_count: int = Field(..., description="Number of successfully processed papers")
    failed_count: int = Field(..., description="Number of failed papers")
    processed_ids: List[Dict[str, Any]] = Field(..., description="Details for each processed ID")


class EntityModel(BaseModel):
    """Entity model for paper figures"""
    text: str = Field(..., description="Entity text")
    type: str = Field(..., description="Entity type (e.g., Gene, Disease)")


class FigureModel(BaseModel):
    """Figure model for paper responses"""
    label: str = Field(..., description="Figure label")
    caption: str = Field(..., description="Figure caption")
    url: Optional[str] = Field(None, description="URL to the figure image")
    entities: List[EntityModel] = Field(default_factory=list, description="Entities extracted from caption")


class PaperResponse(BaseModel):
    """Response model for paper data"""
    paper_id: str = Field(..., description="Paper ID (PMC ID or PMID)")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract")
    figure_count: int = Field(..., description="Number of figures in the paper")
    figures: List[FigureModel] = Field(..., description="Figures in the paper")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field("ok", description="API status")
    version: str = Field("1.0.0", description="API version")


# Query models
class PaperQueryParams(BaseModel):
    """Query parameters for searching papers"""
    paper_ids: Optional[List[str]] = Field(None, description="Filter by paper IDs")
    title_contains: Optional[str] = Field(None, description="Filter by title containing text")
    abstract_contains: Optional[str] = Field(None, description="Filter by abstract containing text")
    caption_contains: Optional[str] = Field(None, description="Filter by caption containing text")
    entity_text: Optional[str] = Field(None, description="Filter by entity text")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    limit: int = Field(10, description="Maximum number of results to return")
    offset: int = Field(0, description="Number of results to skip")


class SearchResponse(BaseModel):
    """Response model for search results"""
    total_results: int = Field(..., description="Total number of matching papers")
    results: List[PaperResponse] = Field(..., description="Search results")
    query: Dict[str, Any] = Field(..., description="Query parameters used")
    page_info: Dict[str, Any] = Field(..., description="Pagination information") 