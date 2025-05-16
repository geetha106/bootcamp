# cli.py
import typer
import requests
import re
import time
import os
from pathlib import Path
from typing import List, Optional
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


def process_paper(paper_id: str) -> bool:
    """
    Process a single paper using either a PMC ID or PMID.
    Returns True if successful, False otherwise.
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
                return False
            paper_id = pmc_id  # Use PMC ID for fetching from PMC

            try:
                pmc = PMCIngestor()
                paper = pmc.fetch(paper_id)
                logger.info(f"Successfully fetched paper after conversion: {paper.title}")
            except Exception as e:
                logger.error(f"Failed to fetch paper using converted PMC ID {paper_id}: {e}")
                return False
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
            return False

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
        return False


@cli.command()
def ingest(paper_id: str):
    """
    Ingest a paper using either a PMC ID or PMID.

    If PMID is provided, it will be converted to PMC ID for fetching from PMC.
    If a text file with paper IDs is provided, all papers in the file will be ingested.
    """
    # Check if paper_id is a file path
    if paper_id.endswith('.txt') and os.path.exists(paper_id):
        logger.info(f"Processing paper IDs from file: {paper_id}")
        with open(paper_id, 'r') as f:
            paper_ids = [line.strip() for line in f if line.strip()]

        # Process each paper ID
        success_count = 0
        failed_count = 0
        for pid in paper_ids:
            if process_paper(pid):
                success_count += 1
            else:
                failed_count += 1

        logger.info(f"Batch processing complete. Success: {success_count}, Failed: {failed_count}")
    else:
        # Process a single paper ID
        process_paper(paper_id)


@cli.command()
def batch(paper_ids: List[str]):
    """
    Ingest multiple papers at once given their PMC IDs or PMIDs.
    """
    success_count = 0
    failed_count = 0

    logger.info(f"Processing {len(paper_ids)} paper(s)...")

    for paper_id in paper_ids:
        if process_paper(paper_id):
            success_count += 1
        else:
            failed_count += 1

    logger.info(f"Batch processing complete. Success: {success_count}, Failed: {failed_count}")


@cli.command()
def watch(
        folder_path: str = typer.Option("data/watch", "--folder-path", help="Path to watch for paper ID files"),
        interval: int = typer.Option(60, "--interval", help="Check interval in seconds")
):
    """
    Watch a folder for text files containing paper IDs to ingest.

    Files should contain one paper ID per line, and should have .txt extension.
    Processed files will be moved to a 'processed' subfolder.
    """
    watch_dir = Path(folder_path)
    processed_dir = watch_dir / "processed"

    # Create directories if they don't exist
    watch_dir.mkdir(exist_ok=True, parents=True)
    processed_dir.mkdir(exist_ok=True)

    logger.info(f"Watching folder {watch_dir} for paper ID files. Press Ctrl+C to stop.")

    try:
        while True:
            # Find all .txt files in the watch directory
            files = list(watch_dir.glob("*.txt"))

            if files:
                logger.info(f"Found {len(files)} file(s) to process")

                for file_path in files:
                    # Skip files in the processed directory
                    if "processed" in str(file_path):
                        continue

                    logger.info(f"Processing file: {file_path}")

                    try:
                        # Read paper IDs from the file
                        with open(file_path, 'r') as f:
                            paper_ids = [line.strip() for line in f if line.strip()]

                        # Process each paper
                        success_count = 0
                        failed_count = 0
                        for paper_id in paper_ids:
                            if process_paper(paper_id):
                                success_count += 1
                            else:
                                failed_count += 1

                        logger.info(
                            f"File {file_path.name} processed. Success: {success_count}, Failed: {failed_count}")

                        # Move the file to the processed directory
                        timestamp = time.strftime("%Y%m%d-%H%M%S")
                        new_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                        file_path.rename(processed_dir / new_filename)

                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")

            else:
                logger.debug(f"No files found in {watch_dir}. Waiting...")

            # Wait for the next check
            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Folder watching stopped")


if __name__ == "__main__":
    cli()