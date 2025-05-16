# cli.py
import typer
import requests
import re
from ingestion.pmc_ingestor import PMCIngestor
from ingestion.pubtator_client import PubTatorClient
from storage.duckdb_backend import DuckDBStorage
from utils.logging import get_logger
import time  # Added for retry with delay

cli = typer.Typer()
logger = get_logger()


def is_pmid(paper_id: str) -> bool:
    """Check if the provided ID is a PMID (all digits)"""
    return paper_id.isdigit()


def convert_pmid_to_pmc(pmid: str) -> str:
    """Convert a PMID to a PMC ID using NCBI E-utilities"""
    try:
        # Use the E-utilities API to convert PMID to PMC ID
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Check if the article has a PMC ID
        result = data.get('result', {})
        article = result.get(pmid, {})

        # Look for PMC ID in the article data
        article_ids = article.get('articleids', [])
        for id_obj in article_ids:
            if id_obj.get('idtype') == 'pmc':
                pmc_id = id_obj.get('value', '')
                if pmc_id:
                    if not pmc_id.startswith("PMC"):
                        pmc_id = f"PMC{pmc_id}"
                    return pmc_id

        logger.warning(f"No PMC ID found for PMID {pmid}")
        return ""
    except Exception as e:
        logger.error(f"Failed to convert PMID to PMC: {e}")
        return ""


def convert_pmc_to_pmid(pmc_id: str) -> str:
    """Convert a PMC ID to a PMID using NCBI E-utilities"""
    # Remove 'PMC' prefix if present for the API call
    pmc_numeric_id = pmc_id.replace("PMC", "")

    try:
        # Use the E-utilities API to convert PMC ID to PMID
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={pmc_id}[pmcid]&retmode=json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract the PMID
        id_list = data.get('esearchresult', {}).get('idlist', [])
        if id_list:
            return id_list[0]

        logger.warning(f"No PMID found for PMC ID {pmc_id}")
        return ""
    except Exception as e:
        logger.error(f"Failed to convert PMC to PMID: {e}")
        return ""


@cli.command()
def ingest(paper_id: str):
    """
    Ingest a paper using either a PMC ID or PMID.

    If PMID is provided, it will be converted to PMC ID for fetching from PMC.
    """
    # Determine if we're dealing with a PMID or PMC ID
    original_id = paper_id

    if is_pmid(paper_id):
        logger.info(f"Detected PMID: {paper_id}")
        pubtator_id = paper_id  # PubTator uses PMID directly

        # Try direct PMC fetch first (in case PMC ID is all digits)
        pmc_id = f"PMC{paper_id}"
        logger.info(f"Trying direct fetch with PMC ID: {pmc_id}")

        try:
            pmc = PMCIngestor()
            paper = pmc.fetch(pmc_id)
            logger.info(f"Successfully fetched paper: {paper.title}")
        except Exception as e:
            # If direct fetch fails, try to convert PMID to PMC ID
            logger.info(f"Direct fetch failed, trying PMID conversion: {e}")
            pmc_id = convert_pmid_to_pmc(paper_id)
            if not pmc_id:
                logger.error(f"Could not convert PMID {paper_id} to PMC ID. Please check if this paper exists in PMC.")
                return
            paper_id = pmc_id  # Use PMC ID for fetching from PMC

            try:
                pmc = PMCIngestor()
                paper = pmc.fetch(paper_id)
                logger.info(f"Successfully fetched paper after conversion: {paper.title}")
            except Exception as e:
                logger.error(f"Failed to fetch paper using converted PMC ID {paper_id}: {e}")
                return
    else:
        # Ensure PMC ID has the PMC prefix
        if not paper_id.startswith("PMC"):
            paper_id = f"PMC{paper_id}"

        logger.info(f"Using PMC ID: {paper_id}")

        # Fetch the paper first to ensure it exists
        try:
            pmc = PMCIngestor()
            paper = pmc.fetch(paper_id)
            logger.info(f"Successfully fetched paper: {paper.title}")
        except Exception as e:
            logger.error(f"Failed to fetch paper with ID {paper_id}: {e}")
            return

        # Convert PMC to PMID for PubTator
        pubtator_id = convert_pmc_to_pmid(paper_id)
        if not pubtator_id:
            logger.warning(f"Could not convert {paper_id} to PMID. Will use PMC ID for PubTator.")
            # Use PMC numeric ID as fallback
            pubtator_id = paper_id.replace("PMC", "")

    # Now proceed with entity extraction and storage
    try:
        pubtator = PubTatorClient()
        storage = DuckDBStorage()

        # Fetch entities for each figure
        for fig in paper.figures:
            logger.info(f"Annotating figure: {fig.label}")
            fig.entities = pubtator.fetch_entities(pubtator_id)

        storage.save_paper(paper)
        logger.info(f"Ingestion complete for original ID: {original_id}")
    except Exception as e:
        logger.error(f"Error during entity extraction or storage: {e}")
        return


if __name__ == "__main__":
    cli()