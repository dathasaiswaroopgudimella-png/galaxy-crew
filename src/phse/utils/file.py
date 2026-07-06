import os
import logging
from typing import List

logger = logging.getLogger("phse")

def ensure_dir(path: str) -> str:
    """
    Ensures that a directory exists, creating it and parent directories if needed.
    
    Args:
        path (str): Path to directory.
        
    Returns:
        str: Absolute path of the directory.
    """
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        logger.debug(f"Creating directory: {abs_path}")
        os.makedirs(abs_path, exist_ok=True)
    return abs_path

def list_files(directory: str, extensions: List[str]) -> List[str]:
    """
    Lists all files in a directory that match any of the given extensions.
    
    Args:
        directory (str): Path to directory.
        extensions (List[str]): List of file extensions (e.g. ['.tif', '.tiff']).
        
    Returns:
        List[str]: List of absolute file paths matching the extensions.
    """
    if not os.path.exists(directory):
        logger.warning(f"Directory '{directory}' does not exist. Cannot list files.")
        return []
        
    matched_files = []
    normalized_exts = [ext.lower() for ext in extensions]
    
    for root, _, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in normalized_exts:
                matched_files.append(os.path.abspath(os.path.join(root, file)))
                
    return matched_files
