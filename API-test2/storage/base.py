from abc import ABC, abstractmethod
from typing import List
from models.paper import Paper

class BaseStorage(ABC):
    """
    Abstract base class for all storage backends (e.g., DuckDB, PostgreSQL).
    """

    @abstractmethod
    def initialize(self) -> None:
        """
        Set up schema/tables if necessary.
        """
        pass

    @abstractmethod
    def store_paper(self, paper: Paper) -> None:
        """
        Store a single Paper and its related metadata (figures, entities).
        """
        pass

    @abstractmethod
    def get_paper(self, paper_id: str) -> Paper:
        """
        Retrieve a stored Paper by ID.
        """
        pass

    @abstractmethod
    def list_papers(self) -> List[str]:
        """
        Return a list of all stored paper IDs.
        """
        pass
