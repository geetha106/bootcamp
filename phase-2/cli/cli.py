# cli.py
import typer
import requests
import time
from ingestion.pmc_ingestor import PMCIngestor
from ingestion.pubtator_client import PubTatorClient
from storage.duckdb_backend import DuckDBStorage
from utils.logging import get_logger

cli = typer.Typer()
logger = get_logger()


def convert_pmc_to_pmid(pmc_numeric_id: str) -> str:
    """
    Convert PMC ID to PMID using NCBI's ID converter API
    """
    try:
        # Try the direct API first
        url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=PMC{pmc_numeric_id}&format=json"
        logger.info(f"Trying to convert PMC to PMID using: {url}")

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if "records" in data and len(data["records"]) > 0 and "pmid" in data["records"][0]:
            pmid = data["records"][0]["pmid"]
            logger.info(f"Successfully converted PMC{pmc_numeric_id} to PMID: {pmid}")
            return pmid

        logger.warning(f"No PMID found for PMC{pmc_numeric_id} in first API")

        # Try the alternative API
        alt_url = f"https://www.ncbi.nlm.nih.gov/research/id-converter/api/v1/pmc/{pmc_numeric_id}"
        logger.info(f"Trying alternative conversion API: {alt_url}")

        alt_response = requests.get(alt_url)
        alt_response.raise_for_status()
        alt_data = alt_response.json()

        if "records" in alt_data and len(alt_data["records"]) > 0 and "pmid" in alt_data["records"][0]:
            pmid = str(alt_data["records"][0]["pmid"])
            logger.info(f"Successfully converted PMC{pmc_numeric_id} to PMID: {pmid}")
            return pmid

        logger.warning(f"No PMID found for PMC{pmc_numeric_id}")
        return ""

    except Exception as e:
        logger.error(f"Failed to convert PMC to PMID: {e}")
        return ""


@cli.command()
def ingest(paper_id: str):
    """
    Ingest a paper by ID (PMC or PMID) and extract figures and entities
    """
    # Normalize paper_id
    if paper_id.startswith("PMC"):
        pmc_id = paper_id
        pmc_numeric_id = paper_id.replace("PMC", "")
    else:
        pmc_id = f"PMC{paper_id}"
        pmc_numeric_id = paper_id

    logger.info(f"Ingesting paper: {pmc_id}")

    pmc = PMCIngestor()
    pubtator = PubTatorClient()
    storage = DuckDBStorage()

    try:
        # Fetch paper from PMC
        paper = pmc.fetch(pmc_id)
        logger.info(f"Fetched paper: {paper.title}")

        # Try converting to PMID
        pmid = convert_pmc_to_pmid(pmc_numeric_id)

        # Default to using PMC numeric ID if PMID is unavailable
        pubtator_id = pmid if pmid else pmc_numeric_id

        # Get entities only once to avoid redundant API calls
        logger.info(f"Fetching entities using ID: {pubtator_id}")
        entities = pubtator.fetch_entities(pubtator_id)
        logger.info(f"Retrieved {len(entities)} entities")

        # Assign entities to each figure
        for fig in paper.figures:
            logger.info(f"Assigning entities to figure: {fig.label}")
            fig.entities = entities.copy()  # Make a copy to avoid reference issues

        # Wait a moment to ensure API rate limits aren't hit
        time.sleep(1)

        # Save paper to database
        storage.save_paper(paper)
        logger.info(f"Ingestion complete for {pmc_id}")

    except Exception as e:
        logger.error(f"Error ingesting paper {pmc_id}: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    cli()