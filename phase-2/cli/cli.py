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
    try:
        response = requests.get(
            f"https://www.ncbi.nlm.nih.gov/research/id-converter/api/v1/pmc/{pmc_numeric_id}"
        )
        response.raise_for_status()
        data = response.json()
        return str(data["records"][0]["pmid"])
    except Exception as e:
        logger.error(f"Failed to convert PMC to PMID: {e}")
        return ""

@cli.command()
def ingest(paper_id: str):
    # Ensure full PMC ID
    if not paper_id.startswith("PMC"):
        paper_id = f"PMC{paper_id}"
    logger.info(f"Ingesting paper: {paper_id}")

    pmc = PMCIngestor()
    pubtator = PubTatorClient()
    storage = DuckDBStorage()

    paper = pmc.fetch(paper_id)
    logger.info(f"Fetched paper: {paper.title}")

    # Try converting to PMID
    pmc_numeric_id = paper_id.replace("PMC", "")
    pmid = convert_pmc_to_pmid(pmc_numeric_id)

    # Fallback to using numeric PMC if PMID is unavailable
    if not pmid:
        logger.warning(f"Could not fetch PMID for {paper_id}, trying PMC numeric ID for PubTator")
        pubtator_id = pmc_numeric_id
    else:
        pubtator_id = pmid

    # Now fetch entities with either valid PMID or PMC numeric ID
    for fig in paper.figures:
        logger.info(f"Annotating figure: {fig.label}")
        fig.entities = pubtator.fetch_entities(pubtator_id)

    storage.save_paper(paper)
    logger.info(f"Ingestion complete for {paper_id}")

if __name__ == "__main__":
    cli()
