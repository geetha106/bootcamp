# ingestion/paper_processor.py

from ingestion.pmc_ingestor import PMCIngestor
from ingestion.pubtator_client import PubTatorClient
from ingestion.id_converter import normalize_paper_id
from storage.duckdb_backend import DuckDBStorage
from processing.caption_cleaner import CaptionCleaner
from processing.entity_mapper import EntityMapper
from utils.logging import get_logger
from typing import Dict, Any, List

logger = get_logger()


class PaperProcessor:
    """Class to handle paper processing workflow"""

    def __init__(self):
        self.pmc_ingestor = PMCIngestor()
        self.pubtator_client = PubTatorClient()
        self.storage = DuckDBStorage()
        self.caption_cleaner = CaptionCleaner()
        self.entity_mapper = EntityMapper()

    def process(self, paper_id: str) -> bool:
        """
        Process a single paper using either a PMC ID or PMID.
        Returns True if successful, False otherwise.
        """
        try:
            # Normalize the paper ID to get both PMC ID and PMID
            original_id, pmc_id, pmid = normalize_paper_id(paper_id)

            if not pmc_id:
                logger.error(f"Could not resolve a PMC ID for {original_id}")
                return False

            # Fetch the paper content from PMC
            logger.info(f"Fetching paper with PMC ID: {pmc_id}")
            paper = self.pmc_ingestor.fetch(pmc_id)

            if not paper:
                logger.error(f"Failed to fetch paper with PMC ID: {pmc_id}")
                return False

            # Use PMID for PubTator if available, otherwise use PMC ID without prefix
            pubtator_id = pmid if pmid else pmc_id.replace("PMC", "")

            # Process each figure
            for fig in paper.figures:
                # Clean the caption
                self.caption_cleaner.process_figure(fig)

                # Fetch entities
                logger.info(f"Annotating figure: {fig.label}")
                fig.entities = self.pubtator_client.fetch_entities(pubtator_id)

                # Process entities
                fig.entities = self.entity_mapper.process_entities(fig.entities)
                fig.entities = self.entity_mapper.map_entities_to_caption(fig.caption, fig.entities)

            # Save to database
            self.storage.save_paper(paper)
            logger.info(f"Successfully processed paper: {original_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing paper {paper_id}: {e}")
            return False

    def process_with_details(self, paper_id: str) -> Dict[str, Any]:
        """
        Process a single paper and return detailed results including success/error status
        and paper details.
        
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
                            "type": entity.type,
                            "identifier": entity.identifier if hasattr(entity, 'identifier') else None
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

        except Exception as e:
            logger.error(f"Error processing paper {paper_id}: {e}")
            return {
                "paper_id": paper_id,
                "source": "PMC" if paper_id.startswith("PMC") else "PMID",
                "status": "error",
                "error": str(e)
            }