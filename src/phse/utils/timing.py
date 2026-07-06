import time
import logging
from typing import Optional

logger = logging.getLogger("phse")

class Timer:
    """
    A context manager and decorator to measure and log execution time.
    """
    
    def __init__(self, description: str, level: str = "INFO"):
        """
        Args:
            description (str): Human-readable name of the block being timed.
            level (str): Logging level for the elapsed time message.
        """
        self.description = description
        self.level = level.upper()
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed: Optional[float] = None

    def __enter__(self) -> 'Timer':
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
        
        log_msg = f"TIMING: '{self.description}' completed in {self.elapsed:.4f} seconds."
        
        # Log to structured log framework
        log_level = getattr(logging, self.level, logging.INFO)
        logger.log(log_level, log_msg)
