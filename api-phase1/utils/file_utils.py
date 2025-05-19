# utils/file_utils.py

import os
from pathlib import Path
import shutil
import time
from typing import List, Callable
from utils.logging import get_logger

logger = get_logger()


def read_ids_from_file(file_path: str) -> List[str]:
    """Read paper IDs from a file, one ID per line"""
    try:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return []


def process_file(file_path: str, processor_func: Callable[[str], bool]) -> tuple[int, int]:
    """
    Process a file containing paper IDs.

    Args:
        file_path: Path to the file containing paper IDs
        processor_func: Function to process each paper ID

    Returns:
        tuple: (success_count, failed_count)
    """
    paper_ids = read_ids_from_file(file_path)

    if not paper_ids:
        logger.warning(f"No paper IDs found in file: {file_path}")
        return 0, 0

    logger.info(f"Processing {len(paper_ids)} paper ID(s) from file: {file_path}")

    success_count = 0
    failed_count = 0

    for paper_id in paper_ids:
        if processor_func(paper_id):
            success_count += 1
        else:
            failed_count += 1

    logger.info(f"File processing complete. Success: {success_count}, Failed: {failed_count}")
    return success_count, failed_count


def move_to_processed(file_path: str, processed_dir: str) -> str:
    """
    Move a processed file to the processed directory with timestamp.

    Args:
        file_path: Path to the file to move
        processed_dir: Path to the processed directory

    Returns:
        str: New file path
    """
    # Create processed directory if it doesn't exist
    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir)

    # Generate new filename with timestamp
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    file_name = os.path.basename(file_path)
    name, ext = os.path.splitext(file_name)
    new_filename = f"{name}_{timestamp}{ext}"
    new_path = os.path.join(processed_dir, new_filename)

    # Move the file
    shutil.move(file_path, new_path)
    logger.info(f"Moved {file_path} to {new_path}")

    return new_path


def setup_watch_directory(watch_dir: str) -> tuple[str, str]:
    """
    Set up watch directory and processed subdirectory.

    Args:
        watch_dir: Path to watch directory

    Returns:
        tuple: (watch_dir_path, processed_dir_path)
    """
    watch_dir_path = Path(watch_dir)
    processed_dir_path = watch_dir_path / "processed"

    # Create directories if they don't exist
    watch_dir_path.mkdir(exist_ok=True, parents=True)
    processed_dir_path.mkdir(exist_ok=True)

    return str(watch_dir_path), str(processed_dir_path)


def find_input_files(watch_dir: str, extension: str = ".txt") -> List[str]:
    """
    Find all input files in the watch directory.

    Args:
        watch_dir: Path to watch directory
        extension: File extension to look for

    Returns:
        List[str]: List of file paths
    """
    watch_path = Path(watch_dir)
    files = [str(f) for f in watch_path.glob(f"*{extension}")
             if "processed" not in str(f)]
    return files