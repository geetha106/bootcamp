from typing import List, Optional
from pydantic import BaseModel, Field


class IDListRequest(BaseModel):
    """Request model for paper ID list processing"""
    ids: List[str] = Field(..., description="List of PMC IDs or PMIDs to process")


class ProcessingResponse(BaseModel):
    """Response model for batch processing results"""
    success_count: int = Field(..., description="Number of successfully processed papers")
    failed_count: int = Field(..., description="Number of failed paper processing attempts")
    processed_ids: List[dict] = Field(..., description="Details of processed paper IDs")


class PaperResponse(BaseModel):
    """Response model for a single paper"""
    paper_id: str
    title: str
    abstract: str
    figure_count: int
    figures: List[dict]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "ok"
    version: str = "1.0.0" 