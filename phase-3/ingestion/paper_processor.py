# ingestion/paper_processor.py

from ingestion.pmc_ingestor import PMCIngestor
from ingestion.pubtator_client import PubTatorClient
from ingestion.id_converter import normalize_paper_id
from storage.duckdb_backend import DuckDBStorage
from processing.caption_cleaner import CaptionCleaner
from processing.entity_mapper import EntityMapper
from utils.logging import get_logger

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