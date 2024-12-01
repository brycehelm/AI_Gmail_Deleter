import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from src.gmail_fetcher import GmailFetcher
import os

class EmailProcessor:
    def __init__(self):
        self.logger = setup_logger()
        self.batch_size = 500
        self.max_emails = 50000
        self.clear_local_cache()
        self.batch_dir = self._create_batch_directory()
        self.fetcher = GmailFetcher()

    def clear_local_cache(self):
        """Clears local cache directories from previous runs"""
        try:
            # Clear any existing batch directories older than current run
            current_dir = os.getcwd()
            for item in os.listdir(current_dir):
                if item.startswith('email_batches_') and os.path.isdir(item):
                    try:
                        import shutil
                        shutil.rmtree(item)
                        self.logger.info(f"Cleared old batch directory: {item}")
                    except Exception as e:
                        self.logger.warning(f"Could not remove directory {item}: {str(e)}")
                        
            self.logger.info("Successfully cleared local cache")
        except Exception as e:
            self.logger.error(f"Error clearing local cache: {str(e)}")
            raise

def setup_logger():
    """Configure and return a logger instance"""
    logger = logging.getLogger(__name__)
    
    if not logger.handlers:  # Prevent duplicate handlers
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        file_handler = TimedRotatingFileHandler("app.log", when="midnight")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        
    return logger
