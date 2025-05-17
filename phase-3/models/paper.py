from typing import List, Optional
from pydantic import BaseModel


class Entity(BaseModel):
    """Entity model for named entities in captions"""
    text: str
    type: str
    start: int = -1  # Default to -1 if position is unknown
    end: int = -1    # Default to -1 if position is unknown


class Figure(BaseModel):
    """Figure model"""
    label: str
    caption: str
    url: Optional[str] = None
    entities: List[Entity] = []


class Paper(BaseModel):
    """Paper model"""
    paper_id: str
    title: str
    abstract: str
    figures: List[Figure] = []
    pmc_id: Optional[str] = None  # Add this for compatibility with test_batch_ingest.py