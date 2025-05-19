# ingestion/paper_processor.py

from ingestion.pmc_ingestor import PMCIngestor
from ingestion.pubtator_client import PubTatorClient
from ingestion.id_converter import normalize_paper_id
from storage.duckdb_backend import DuckDBStorage
from processing.caption_cleaner import CaptionCleaner
from processing.entity_mapper import EntityMapper
from utils.logging import get_logger
from typing import Dict, Any, List
from models.paper import Paper

logger = get_logger()


class PaperProcessor:
    """Class to handle paper processing workflow"""

    def __init__(self):
        self.pmc_ingestor = PMCIngestor()
        self.pubtator_client = PubTatorClient()
        self.storage = DuckDBStorage()
        self.caption_cleaner = CaptionCleaner()
        self.entity_mapper = EntityMapper()

    def _process_paper_from_api(self, original_id: str, pmc_id: str, pmid: str) -> Dict[str, Any]:
        """
        Process a paper by fetching data from external APIs.
        This is an internal method used when the paper is not in the database
        or needs to be refreshed.
        """
        # Fetch the paper content from PMC
        logger.info(f"Fetching paper with PMC ID: {pmc_id}")
        paper = self.pmc_ingestor.fetch(pmc_id)

        if not paper:
            return {
                "paper_id": original_id,
                "source": "PMC",
                "status": "error",
                "error": f"Failed to fetch paper with PMC ID: {pmc_id}"
            }

        # Use PMID for PubTator if available, otherwise use PMC ID without prefix
        pubtator_id = pmid if pmid else pmc_id.replace("PMC", "")

        # Process each figure
        processed_figures = []
        for fig in paper.figures:
            # Clean the caption
            self.caption_cleaner.process_figure(fig)

            # Fetch entities
            logger.info(f"Annotating figure: {fig.label}")
            fig.entities = self.pubtator_client.fetch_entities(pubtator_id)

            # Process entities
            fig.entities = self.entity_mapper.process_entities(fig.entities)
            fig.entities = self.entity_mapper.map_entities_to_caption(fig.caption, fig.entities)

            # Convert figure to dict format
            processed_figures.append({
                "figure_id": fig.label,
                "caption": fig.caption,
                "figure_url": fig.url,
                "entities": [
                    {
                        "entity": entity.text,
                        "type": entity.type
                    }
                    for entity in fig.entities
                ]
            })

        # Save to database
        self.storage.save_paper(paper)

        # Return success result with paper details
        return {
            "paper_id": original_id,
            "source": "PMC",
            "status": "success",
            "title": paper.title,
            "abstract": paper.abstract,
            "figures": processed_figures
        }

    def _convert_paper_to_dict(self, paper: Paper) -> Dict[str, Any]:
        """Convert a Paper object to the standard dictionary format."""
        return {
            "paper_id": paper.paper_id,
            "source": "PMC",
            "status": "success",
            "title": paper.title,
            "abstract": paper.abstract,
            "figures": [
                {
                    "figure_id": fig.label,
                    "caption": fig.caption,
                    "figure_url": fig.url,
                    "entities": [
                        {
                            "entity": entity.text,
                            "type": entity.type
                        }
                        for entity in fig.entities
                    ]
                }
                for fig in paper.figures
            ]
        }

    def process_with_details(self, paper_id: str) -> Dict[str, Any]:
        """
        Process a single paper and return detailed results including success/error status
        and paper details. First checks the database for existing data before making API calls.
        
        Returns:
            Dict containing paper processing results with the following structure:
            {
                "paper_id": str,
                "source": str ("PMC" or "PMID"),
                "status": str ("success" or "error"),
                "error": str (optional, only present if status is "error"),
                "title": str (optional),
                "abstract": str (optional),
                "figures": List[Dict] (optional)
            }
        """
        try:
            # Normalize the paper ID to get both PMC ID and PMID
            original_id, pmc_id, pmid = normalize_paper_id(paper_id)

            if not pmc_id:
                return {
                    "paper_id": original_id,
                    "source": "PMID" if pmid else "PMC",
                    "status": "error",
                    "error": f"Could not resolve a PMC ID for {original_id}"
                }

            # Check if paper exists in database and is complete
            is_complete, reason = self.storage.check_paper_completeness(pmc_id)
            
            if is_complete:
                # If paper is complete in database, return it
                logger.info(f"Found complete paper in database: {pmc_id}")
                paper = self.storage.get_paper_with_details(pmc_id)
                if paper:
                    return self._convert_paper_to_dict(paper)
                else:
                    logger.warning(f"Paper marked as complete but retrieval failed: {pmc_id}")
            else:
                logger.info(f"Paper {pmc_id} needs to be processed: {reason}")

            # If we get here, we need to process the paper from APIs
            return self._process_paper_from_api(original_id, pmc_id, pmid)

        except Exception as e:
            logger.error(f"Error processing paper {paper_id}: {e}")
            return {
                "paper_id": paper_id,
                "source": "PMC" if paper_id.startswith("PMC") else "PMID",
                "status": "error",
                "error": str(e)
            }

    def process(self, paper_id: str) -> bool:
        """
        Process a single paper using either a PMC ID or PMID.
        Returns True if successful, False otherwise.
        """
        result = self.process_with_details(paper_id)
        return result.get("status") == "success"