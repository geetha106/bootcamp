# watcher.py
import os
import time
from pathlib import Path
from typing import List
from utils.logging import get_logger
from cli.cli import process_paper

logger = get_logger("figurex.watcher")


class FolderWatcher:
    """
    Watches a folder for paper ID files and processes them.
    """

    def __init__(self, folder_path: str = "data/watch", interval: int = 60):
        """
        Initialize the folder watcher.

        Args:
            folder_path: Path to the folder to watch
            interval: Check interval in seconds
        """
        self.folder_path = Path(folder_path)
        self.processed_dir = self.folder_path / "processed"
        self.interval = interval

        # Create directories if they don't exist
        self.folder_path.mkdir(exist_ok=True, parents=True)
        self.processed_dir.mkdir(exist_ok=True)

    def start(self):
        """
        Start watching the folder.
        """
        logger.info(f"Watching folder {self.folder_path} for paper ID files. Press Ctrl+C to stop.")

        try:
            while True:
                self._check_folder()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            logger.info("Folder watching stopped")

    def _check_folder(self):
        """
        Check the folder for new files and process them.
        """
        # Find all .txt files in the watch directory
        files = list(self.folder_path.glob("*.txt"))

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
                    self._process_paper_ids(paper_ids, file_path.name)

                    # Move the file to the processed directory
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    new_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                    file_path.rename(self.processed_dir / new_filename)

                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")

        else:
            logger.debug(f"No files found in {self.folder_path}. Waiting...")

    def _process_paper_ids(self, paper_ids: List[str], source_file: str):
        """
        Process a list of paper IDs.

        Args:
            paper_ids: List of paper IDs to process
            source_file: Source file name for logging
        """
        success_count = 0
        failed_count = 0

        for paper_id in paper_ids:
            if process_paper(paper_id):
                success_count += 1
            else:
                failed_count += 1

        logger.info(f"File {source_file} processed. Success: {success_count}, Failed: {failed_count}")