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
from storage.duckdb_backend import DuckDBStorage
from config.config import get_config

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
def reset(
    force: bool = typer.Option(False, "--force", "-f", help="Force reset without confirmation")
):
    """
    Reset the database by dropping all tables and recreating them.
    This will delete all stored papers, figures, and entities.
    """
    if not force:
        confirm = typer.confirm("This will delete all data in the database. Are you sure?")
        if not confirm:
            logger.info("Database reset cancelled")
            raise typer.Exit()

    try:
        config = get_config()
        storage = DuckDBStorage(config.storage.db_path)
        storage.reset_db()
        logger.info("Database has been reset successfully")
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise typer.Exit(1)


@cli.command()
def batch(
    paper_ids: List[str] = typer.Argument(..., help="One or more PMC IDs or PMIDs to process"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (optional)"),
    format: OutputFormat = typer.Option(OutputFormat.JSON, "--format", "-f", help="Output format (json or csv)")
):
    """
    Process one or more papers by their PMC IDs or PMIDs.
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
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
        with open(output, 'w') as f:
            f.write(formatted_output)
        logger.info(f"Results saved to {output}")
    else:
        print(formatted_output)


@cli.command()
def ingest(
    input_file: str = typer.Argument(..., help="Path to text file containing PMC IDs or PMIDs (one per line)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (optional)"),
    format: OutputFormat = typer.Option(OutputFormat.JSON, "--format", "-f", help="Output format (json or csv)")
):
    """
    Process multiple papers from a text file containing PMC IDs or PMIDs (one per line).
    Optionally save the results to a file in JSON or CSV format.
    """
    # Check if input file exists
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        raise typer.Exit(1)

    # Read paper IDs from file
    paper_ids = read_ids_from_file(input_file)
    if not paper_ids:
        logger.error("No paper IDs found in the input file")
        raise typer.Exit(1)

    exporter = BatchResultExporter()
    exporter.start_timing()
    results = []

    logger.info(f"Processing {len(paper_ids)} paper(s) from {input_file}...")

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
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
        with open(output, 'w') as f:
            f.write(formatted_output)
        logger.info(f"Results saved to {output}")
    else:
        print(formatted_output)

if __name__ == "__main__":
    cli()