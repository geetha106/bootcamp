from pydantic import BaseModel
from typing import List, Optional


class Entity(BaseModel):
    """
    Represents a named entity (e.g., gene, protein) extracted from a figure caption.
    """
    text: str               # the actual entity text
    type: Optional[str]     # type/category (e.g., GENE, DISEASE)
    start: Optional[int]    # start position in caption (optional)
    end: Optional[int]      # end position in caption (optional)


class Figure(BaseModel):
    """
    Represents a single figure in the paper with caption and associated entities.
    """
    label: str                        # e.g., Figure 1, Fig. 2
    caption: str
    url: Optional[str]
    entities: List[Entity] = []      # Entities found in this caption


class Paper(BaseModel):
    """
    Represents the entire paper with title, abstract, and all figures.
    """
    paper_id: str
    title: str
    abstract: Optional[str]
    figures: List[Figure] = []
