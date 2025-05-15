# cli.py
import typer
import requests
import time
from ingestion.pmc_ingestor import PMCIngestor
from ingestion.pubtator_client import PubTatorClient
from storage.duckdb_backend import DuckDBStorage
from utils.logging import get_logger
import os

cli = typer.Typer()
logger = get_logger()


def convert_pmc_to_pmid(pmc_id: str) -> str:
    """
    Convert a PMC ID to a PMID using the NCBI EUtils API.
    Returns the PMID as a string or empty string if conversion fails.

    This uses EUtils instead of the ID converter API which seems unreliable.
    """
    try:
        # Use EUtils API instead of ID converter
        logger.info(f"Converting {pmc_id} to PMID using EUtils...")

        # Remove PMC prefix if present
        numeric_id = pmc_id.replace("PMC", "")

        # First API call to fetch PubMed record
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={numeric_id}&retmode=xml"
        response = requests.get(url)
        response.raise_for_status()

        # Check if the XML contains a PMID
        if "<article-id pub-id-type=\"pmid\">" in response.text:
            # Extract PMID from XML using simple string operations
            xml_text = response.text
            start_tag = "<article-id pub-id-type=\"pmid\">"
            end_tag = "</article-id>"
            start_pos = xml_text.find(start_tag) + len(start_tag)
            end_pos = xml_text.find(end_tag, start_pos)

            if start_pos > len(start_tag) and end_pos > start_pos:
                pmid = xml_text[start_pos:end_pos].strip()
                logger.info(f"Successfully converted {pmc_id} to PMID {pmid}")
                return pmid

        # Alternative approach: use esearch + efetch
        time.sleep(0.3)  # Avoid rate limiting
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=PMC{numeric_id}[pmcid]&retmode=json"
        search_response = requests.get(search_url)
        search_response.raise_for_status()

        search_data = search_response.json()
        if "esearchresult" in search_data and search_data["esearchresult"].get("idlist"):
            pmid = search_data["esearchresult"]["idlist"][0]
            logger.info(f"Successfully converted {pmc_id} to PMID {pmid} using alternative method")
            return pmid

        logger.warning(f"No PMID found for {pmc_id}")
        return ""

    except Exception as e:
        logger.error(f"Failed to convert PMC to PMID: {e}")
        return ""


@cli.command()
def ingest(paper_id: str):
    """
    Ingest a paper by its PMC ID or PMID.

    Example:
        python -m cli.cli ingest PMC7696669
        python -m cli.cli ingest 7696669  (PMC prefix will be added)
    """
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    # Ensure full PMC ID
    if not paper_id.startswith("PMC"):
        paper_id = f"PMC{paper_id}"
    logger.info(f"Ingesting paper: {paper_id}")

    pmc = PMCIngestor()
    pubtator = PubTatorClient()
    storage = DuckDBStorage()

    # Fetch paper from PMC
    paper = pmc.fetch(paper_id)
    logger.info(f"Fetched paper: {paper.title}")
    logger.info(f"Found {len(paper.figures)} figures")

    # Try converting to PMID for better entity extraction
    pmid = convert_pmc_to_pmid(paper_id)

    # Extract entities once for the paper to avoid redundant API calls
    if pmid:
        logger.info(f"Using PMID {pmid} for entity extraction")
        all_entities = pubtator.fetch_entities(pmid)
    else:
        logger.warning(f"Could not fetch PMID for {paper_id}, trying direct PMC extraction")
        # For direct PMC extraction, we'll use a different approach
        all_entities = pubtator.extract_entities_from_text(paper.title + " " + paper.abstract)

    logger.info(f"Extracted {len(all_entities)} entities from paper")

    # Assign extracted entities to each figure
    # In a more advanced implementation, we would match entities to specific figures
    # based on their captions, but for now we'll add all entities to all figures
    for i, fig in enumerate(paper.figures):
        logger.info(f"Annotating figure: {fig.label}")
        fig.entities = all_entities.copy()  # Copy to avoid reference issues

    # Save to database
    storage.save_paper(paper)
    logger.info(f"Successfully saved paper {paper_id} with {len(paper.figures)} figures")
    logger.info(f"Ingestion complete for {paper_id}")


if __name__ == "__main__":
    cli()