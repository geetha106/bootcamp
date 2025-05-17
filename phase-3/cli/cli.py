# cli/cli.py
import typer
import os
import time
from typing import List, Optional
from ingestion.paper_processor import PaperProcessor
from utils.file_utils import (
    read_ids_from_file,
    process_file,
    move_to_processed,
    setup_watch_directory,
    find_input_files
)
from utils.logging import get_logger
from utils.export import BatchResultExporter
from enum import Enum

class OutputFormat(str, Enum):
    JSON = "json"
    CSV = "csv"

cli = typer.Typer()
logger = get_logger()

# Create a processor instance for reuse
processor = PaperProcessor()


# Keep this function for backward compatibility with test_batch_ingest.py
def process_paper(paper_id: str) -> bool:
    """
    Process a single paper using either a PMC ID or PMID.
    Returns True if successful, False otherwise.

    This function is kept for backward compatibility.
    """
    return processor.process(paper_id)


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
        success_count, failed_count = process_file(paper_id, processor.process)
    else:
        # Process a single paper ID
        result = processor.process(paper_id)
        logger.info(f"Paper processing {'successful' if result else 'failed'}")


@cli.command()
def batch(
    paper_ids: List[str] = typer.Argument(..., help="List of PMC IDs or PMIDs to process"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (optional)"),
    format: OutputFormat = typer.Option(OutputFormat.JSON, "--format", "-f", help="Output format (json or csv)")
):
    """
    Ingest multiple papers at once given their PMC IDs or PMIDs.
    Optionally save the results to a file in JSON or CSV format.
    """
    exporter = BatchResultExporter()
    exporter.start_timing()
    results = []

    logger.info(f"Processing {len(paper_ids)} paper(s)...")

    for paper_id in paper_ids:
        logger.info(f"Processing paper ID: {paper_id}")
        # Process paper and collect results
        result = processor.process_with_details(paper_id)
        results.append(result)
        
        if result["status"] == "success":
            logger.info(f"Successfully processed paper: {paper_id}")
        else:
            logger.error(f"Failed to process paper: {paper_id}")

    # Format the results
    formatted_output = exporter.format_results(results, format.value)

    # Output the results
    if output:
        with open(output, 'w') as f:
            f.write(formatted_output)
        logger.info(f"Results saved to {output}")
    else:
        print(formatted_output)

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
    watch_dir, processed_dir = setup_watch_directory(folder_path)

    logger.info(f"Watching folder {watch_dir} for paper ID files. Press Ctrl+C to stop.")

    try:
        while True:
            # Find all .txt files in the watch directory
            files = find_input_files(watch_dir)

            if files:
                logger.info(f"Found {len(files)} file(s) to process")

                for file_path in files:
                    logger.info(f"Processing file: {file_path}")

                    try:
                        # Process the file
                        success_count, failed_count = process_file(
                            file_path, processor.process
                        )

                        # Move the file to the processed directory
                        move_to_processed(file_path, processed_dir)

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