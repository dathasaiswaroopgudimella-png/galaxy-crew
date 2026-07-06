import logging
import os
import sys
import json
from datetime import datetime
from typing import Optional

class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records in a structured JSON format.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logger(log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """
    Sets up a logger for the phse application.
    
    Configures a console stream handler (human-readable) and a file
    handler (JSON-structured) inside the specified log directory.
    
    Args:
        log_dir (str): Directory where log files will be written.
        level (str): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        
    Returns:
        logging.Logger: The configured Logger instance.
    """
    logger = logging.getLogger("phse")
    logger.setLevel(level.upper())
    
    # Prevent adding handlers repeatedly if logger is already configured
    if logger.hasHandlers():
        return logger
        
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Console Handler (Human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(module)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File Handler (JSON format)
    log_file_name = f"phse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_file_path = os.path.join(log_dir, log_file_name)
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    json_formatter = JsonFormatter(datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"PHSE logging framework initialized. Writing JSON logs to {log_file_path}")
    
    return logger
