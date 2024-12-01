import os
import json
from datetime import datetime
from .gmail_fetcher import GmailFetcher
from .utils.logger import setup_logger
from .openai_processor import OpenAIProcessor

class EmailProcessor:
    def __init__(self):
        self.logger = setup_logger()
        self.batch_size = 500
        self.max_emails = 50000
        self.clear_local_cache()
        self.batch_dir = 'batches'
        os.makedirs(self.batch_dir, exist_ok=True)
        self.fetcher = GmailFetcher()
        self.openai_processor = OpenAIProcessor(self.fetcher)

    def clear_local_cache(self):
        """Clears contents of the batches directory"""
        try:
            if os.path.exists('batches'):
                for file in os.listdir('batches'):
                    file_path = os.path.join('batches', file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        self.logger.warning(f"Could not remove {file_path}: {str(e)}")
                self.logger.info("Successfully cleared batches directory")
        except Exception as e:
            self.logger.error(f"Error clearing batches directory: {str(e)}")
            raise

    def process_emails(self):
        try:
            self.logger.info("Starting email processing")
            self.fetcher.authenticate()
            
            emails_fetched = 0
            page_token = None
            batch_number = 1
            
            while emails_fetched < self.max_emails:
                # Fetch batch
                self.logger.info(f"Fetching batch {batch_number}")
                result = self.fetcher.fetch_batch(
                    max_results=self.batch_size,
                    page_token=page_token
                )
                
                if not result['messages']:
                    self.logger.info("No more emails to fetch")
                    break
                
                # Process current batch
                self.logger.info(f"Processing batch {batch_number}")
                self.openai_processor.process_batch(result['messages'])
                
                emails_fetched += len(result['messages'])
                page_token = result.get('nextPageToken')
                batch_number += 1
                
                if not page_token:
                    self.logger.info("No more pages to fetch")
                    break
            
            self.logger.info(f"Completed! Total emails processed: {emails_fetched}")
            
        except Exception as e:
            self.logger.error(f"Error during email processing: {str(e)}")
            raise

def main():
    processor = EmailProcessor()
    processor.process_emails()
