# cli.py
import typer
import requests
from ingestion.pmc_ingestor import PMCIngestor
from ingestion.pubtator_client import PubTatorClient
from storage.duckdb_backend import DuckDBStorage
from utils.logging import get_logger

cli = typer.Typer()
logger = get_logger()


def convert_pmc_to_pmid(pmc_numeric_id: str) -> str:
    """
    Convert a PMC ID to PMID using the NCBI ID Converter API.
    Returns empty string if conversion fails.
    """
    try:
        # Use the proper NCBI ID converter API
        response = requests.get(
            f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=PMC{pmc_numeric_id}&format=json"
        )
        response.raise_for_status()
        data = response.json()

        if "records" in data and len(data["records"]) > 0 and "pmid" in data["records"][0]:
            pmid = str(data["records"][0]["pmid"])
            logger.info(f"Successfully converted PMC{pmc_numeric_id} to PMID {pmid}")
            return pmid
        else:
            logger.warning(f"No PMID found for PMC{pmc_numeric_id}")
            return ""
    except Exception as e:
        logger.error(f"Failed to convert PMC to PMID: {e}")
        return ""


@cli.command()
def ingest(paper_id: str):
    """
    Ingest a paper by its PMC ID.
    If paper_id is provided without 'PMC' prefix, it will be added automatically.
    """
    # Ensure full PMC ID
    if not paper_id.startswith("PMC"):
        paper_id = f"PMC{paper_id}"
    logger.info(f"Ingesting paper: {paper_id}")

    pmc = PMCIngestor()
    pubtator = PubTatorClient()
    storage = DuckDBStorage()

    # Fetch paper with figures from PMC
    paper = pmc.fetch(paper_id)
    logger.info(f"Fetched paper: {paper.title}")
    logger.info(f"Found {len(paper.figures)} figures")

    # Get numeric PMC ID for PubTator
    pmc_numeric_id = paper_id.replace("PMC", "")

    # Try converting to PMID first (preferred by PubTator)
    pmid = convert_pmc_to_pmid(pmc_numeric_id)

    # Use PMID if available, otherwise try with PMC ID
    entities = []
    if pmid:
        logger.info(f"Using PMID {pmid} for entity extraction")
        entities = pubtator.fetch_entities(pmid)
    else:
        logger.info(f"Using PMC ID {pmc_numeric_id} for entity extraction")
        entities = pubtator.fetch_entities(pmc_numeric_id)

    logger.info(f"Fetched {len(entities)} entities")

    # Associate entities with all figures
    # This is a simple approach - in a more sophisticated system,
    # we would match entities only to figures where they appear
    if entities:
        for fig in paper.figures:
            logger.info(f"Associating entities with figure: {fig.label}")
            fig.entities = entities

    # Save to database
    storage.save_paper(paper)
    logger.info(f"Ingestion complete for {paper_id}")


if __name__ == "__main__":
    cli()