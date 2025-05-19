# processing/base.py

from abc import ABC, abstractmethod
from models.paper import Paper, Figure, Entity


class BaseProcessor(ABC):
    """Abstract base class for all processors"""

    @abstractmethod
    def process(self, data):
        """Process the input data and return processed output"""
        pass


class CaptionProcessor(BaseProcessor):
    """Base class for caption processing"""

    @abstractmethod
    def clean_caption(self, caption: str) -> str:
        """Clean and normalize a caption"""
        pass

    @abstractmethod
    def process_figure(self, figure: Figure) -> Figure:
        """Process a figure's caption"""
        pass

    def process(self, paper: Paper) -> Paper:
        """Process all figures in a paper"""
        for figure in paper.figures:
            self.process_figure(figure)
        return paper


class EntityProcessor(BaseProcessor):
    """Base class for entity processing"""

    @abstractmethod
    def process_entities(self, entities: list[Entity]) -> list[Entity]:
        """Process and deduplicate entities"""
        pass

    @abstractmethod
    def map_entities_to_caption(self, caption: str, entities: list[Entity]) -> list[Entity]:
        """Map entities to specific portions of the caption"""
        pass

    def process(self, paper: Paper) -> Paper:
        """Process all entities in a paper"""
        for figure in paper.figures:
            figure.entities = self.process_entities(figure.entities)
            figure.entities = self.map_entities_to_caption(figure.caption, figure.entities)
        return paper