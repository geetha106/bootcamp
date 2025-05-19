from abc import ABC, abstractmethod
from typing import Union
from models.paper import Paper

class BaseIngestor(ABC):
    """
    Abstract base class for ingestion implementations (e.g., PMC, arXiv).
    """

    @abstractmethod
    def ingest(self, paper_id: str) -> Union[Paper, None]:
        """
        Ingest data from a paper given its ID and return a Paper object.
        Returns None if ingestion fails or the paper is not found.
        """
        pass
