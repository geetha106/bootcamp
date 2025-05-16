# cli.py
import typer
import requests
import re
from typing import List, Optional
from ingestion.pmc_ingestor import PMCIngestor
from ingestion.pubtator_client import PubTatorClient
from storage.duckdb_backend import DuckDBStorage
from utils.logging import get_logger
import time
import os

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


def process_single_paper(paper_id: str, max_retries: int = 3) -> bool:
    """
    Process a single paper by ID, with retry logic.
    Returns True if successful, False otherwise.
    """
    original_id = paper_id
    retry_count = 0

    while retry_count < max_retries:
        try:
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
                        logger.error(
                            f"Could not convert PMID {paper_id} to PMC ID. Please check if this paper exists in PMC.")
                        return False
                    paper_id = pmc_id  # Use PMC ID for fetching from PMC

                    try:
                        pmc = PMCIngestor()
                        paper = pmc.fetch(paper_id)
                        logger.info(f"Successfully fetched paper after conversion: {paper.title}")
                    except Exception as e:
                        logger.error(f"Failed to fetch paper using converted PMC ID {paper_id}: {e}")
                        retry_count += 1
                        time.sleep(1)  # Wait before retrying
                        continue
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
                    retry_count += 1
                    time.sleep(1)  # Wait before retrying
                    continue

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
                return True
            except Exception as e:
                logger.error(f"Error during entity extraction or storage: {e}")
                retry_count += 1
                time.sleep(1)  # Wait before retrying
                continue

        except Exception as e:
            logger.error(f"Unexpected error processing paper {original_id}: {e}")
            retry_count += 1
            time.sleep(1)  # Wait before retrying

    logger.error(f"Failed to process paper {original_id} after {max_retries} attempts")
    return False


@cli.command()
def ingest(
        paper_id: str = typer.Argument(..., help="Single paper ID or path to file with multiple IDs")
):
    """
    Ingest a paper using either a PMC ID or PMID.

    If PMID is provided, it will be converted to PMC ID for fetching from PMC.

    Can also provide a path to a file containing a list of IDs (one per line).
    """
    # Check if paper_id is a file path
    if os.path.isfile(paper_id):
        batch_ingest_from_file(paper_id)
    else:
        # Process single paper ID
        process_single_paper(paper_id)


@cli.command()
def batch_ingest(
        paper_ids: List[str] = typer.Argument(..., help="List of paper IDs (PMC or PMID)")
):
    """
    Ingest multiple papers using a list of PMC IDs or PMIDs.
    """
    total = len(paper_ids)
    successful = 0
    failed = 0

    logger.info(f"Starting batch ingestion of {total} papers")

    for i, paper_id in enumerate(paper_ids):
        logger.info(f"Processing paper {i + 1}/{total}: {paper_id}")
        if process_single_paper(paper_id):
            successful += 1
        else:
            failed += 1

    logger.info(f"Batch ingestion complete: {successful} successful, {failed} failed out of {total}")


def batch_ingest_from_file(file_path: str):
    """
    Ingest multiple papers from a file containing one ID per line.
    Lines starting with # are treated as comments.
    """
    try:
        with open(file_path, 'r') as f:
            paper_ids = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

        if not paper_ids:
            logger.warning(f"No valid paper IDs found in {file_path}")
            return

        total = len(paper_ids)
        successful = 0
        failed = 0

        logger.info(f"Starting batch ingestion of {total} papers from file {file_path}")

        for i, paper_id in enumerate(paper_ids):
            logger.info(f"Processing paper {i + 1}/{total}: {paper_id}")
            if process_single_paper(paper_id):
                successful += 1
            else:
                failed += 1

        logger.info(f"Batch ingestion complete: {successful} successful, {failed} failed out of {total}")
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")


@cli.command()
def watch_folder(
        folder_path: str = typer.Option("data/watch", help="Path to folder to watch for ID files"),
        interval: int = typer.Option(60, help="Check interval in seconds")
):
    """
    Watch a folder for files containing paper IDs to ingest.
    Processed files will be moved to a 'processed' subfolder.
    """
    from pathlib import Path
    import time

    watch_dir = Path(folder_path)
    processed_dir = watch_dir / "processed"
    failed_dir = watch_dir / "failed"

    # Create directories if they don't exist
    watch_dir.mkdir(exist_ok=True)
    processed_dir.mkdir(exist_ok=True)
    failed_dir.mkdir(exist_ok=True)

    logger.info(f"Watching folder {watch_dir} for paper ID files (checking every {interval} seconds)")

    try:
        while True:
            for file_path in watch_dir.glob("*.txt"):
                if file_path.is_file() and file_path.name != ".gitkeep":
                    logger.info(f"Found file: {file_path}")

                    try:
                        batch_ingest_from_file(str(file_path))
                        # Move to processed directory
                        file_path.rename(processed_dir / file_path.name)
                        logger.info(f"Moved {file_path.name} to processed directory")
                    except Exception as e:
                        logger.error(f"Error processing {file_path.name}: {e}")
                        # Move to failed directory
                        file_path.rename(failed_dir / file_path.name)
                        logger.info(f"Moved {file_path.name} to failed directory")

            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Stopping folder watch")


if __name__ == "__main__":
    cli()