#!/usr/bin/env python3
import os
import time
import shutil
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import required modules for paper processing
from ingestion.paper_processor import PaperProcessor
from ingestion.id_converter import normalize_paper_id
from storage.duckdb_backend import DuckDBStorage
from config.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Directory paths
WATCHED_DIR = Path("watched_dir")
UNPROCESSED_DIR = WATCHED_DIR / "unprocessed"
UNDERPROCESS_DIR = WATCHED_DIR / "underprocess"
PROCESSED_DIR = WATCHED_DIR / "processed"

# Ensure directories exist
for directory in [UNPROCESSED_DIR, UNDERPROCESS_DIR, PROCESSED_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Initialize processor and storage
processor = PaperProcessor()
config = get_config()
storage = DuckDBStorage(config.storage.db_path)

def process_paper_ids(paper_ids):
    """
    Process a list of paper IDs (PMC IDs or PMIDs)
    This replicates the functionality from api/routes.py
    """
    results = []
    
    for paper_id in paper_ids:
        try:
            # Normalize the paper ID to get both PMC ID and PMID
            original_id, pmc_id, pmid = normalize_paper_id(paper_id)
            
            # Log the ID conversion for debugging
            if pmid and pmc_id:
                logger.info(f"Converted ID: Original={original_id}, PMC={pmc_id}, PMID={pmid}")
            elif pmid:
                logger.info(f"Using PMID: {pmid} (no PMC ID found)")
            elif pmc_id:
                logger.info(f"Using PMC ID: {pmc_id} (no PMC ID found)")
            else:
                logger.warning(f"Could not resolve ID: {original_id}")
            
            # Use the process_with_details method which handles both PMC IDs and PMIDs
            result = processor.process_with_details(paper_id)
            results.append(result)
            
            if result["status"] == "success":
                logger.info(f"Successfully processed paper: {paper_id}")
            else:
                logger.error(f"Failed to process paper: {paper_id}, Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error processing paper {paper_id}: {e}")
            results.append({
                "paper_id": paper_id,
                "status": "error",
                "message": str(e)
            })
    
    return results

def process_file(file_path):
    """Process a file containing paper IDs"""
    try:
        # Move to underprocess directory
        filename = os.path.basename(file_path)
        underprocess_path = UNDERPROCESS_DIR / filename
        shutil.move(file_path, underprocess_path)
        logger.info(f"Moved {filename} to underprocess directory")
        
        # Read paper IDs from file
        with open(underprocess_path, 'r') as f:
            paper_ids = [line.strip() for line in f if line.strip()]
        
        if not paper_ids:
            logger.warning(f"No paper IDs found in {filename}")
            shutil.move(underprocess_path, PROCESSED_DIR / filename)
            return
        
        # Process the paper IDs
        logger.info(f"Processing {len(paper_ids)} paper IDs from {filename}")
        results = process_paper_ids(paper_ids)
        
        # Log results
        success_count = sum(1 for r in results if r.get('status') == 'success')
        logger.info(f"Processed {filename}: {success_count}/{len(paper_ids)} successful")
        
        # Move to processed directory
        processed_path = PROCESSED_DIR / filename
        shutil.move(underprocess_path, processed_path)
        logger.info(f"Moved {filename} to processed directory")
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        # If there was an error, try to move the file back to unprocessed
        try:
            if os.path.exists(underprocess_path):
                shutil.move(underprocess_path, UNPROCESSED_DIR / filename)
                logger.info(f"Moved {filename} back to unprocessed directory due to error")
        except Exception:
            logger.exception("Failed to move file after error")

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.txt'):
            logger.info(f"New file detected: {event.src_path}")
            process_file(event.src_path)

def main():
    logger.info(f"Starting to monitor {UNPROCESSED_DIR} for new .txt files")
    
    # Process any existing files in the unprocessed directory
    for file_path in UNPROCESSED_DIR.glob('*.txt'):
        logger.info(f"Found existing file: {file_path}")
        process_file(str(file_path))
    
    # Set up the file watcher
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, str(UNPROCESSED_DIR), recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping file monitoring")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main() 