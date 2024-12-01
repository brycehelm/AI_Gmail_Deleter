import os
import json
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
from .utils.logger import setup_logger
import time
from .colors import Colors
from datetime import datetime, timedelta
import tiktoken

load_dotenv()
logger = setup_logger()

class TokenRateLimiter:
    def __init__(self, tokens_per_minute=200000):
        self.tokens_per_minute = tokens_per_minute
        self.token_usage = []
        self.encoding = tiktoken.encoding_for_model("gpt-4")
    
    def count_tokens(self, text):
        return len(self.encoding.encode(text))
    
    async def wait_if_needed(self, required_tokens):
        # Remove entries older than 1 minute
        current_time = datetime.now()
        self.token_usage = [
            (time, tokens) for time, tokens in self.token_usage 
            if current_time - time < timedelta(minutes=1)
        ]
        
        # Calculate current token usage
        total_tokens = sum(tokens for _, tokens in self.token_usage)
        
        if total_tokens + required_tokens > self.tokens_per_minute:
            # Calculate wait time
            oldest_time = self.token_usage[0][0]
            wait_seconds = 60 - (current_time - oldest_time).seconds
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
                # Clear old usage after waiting
                self.token_usage = []
        
        # Add new token usage
        self.token_usage.append((current_time, required_tokens))

class OpenAIProcessor:
    def __init__(self, gmail_fetcher):
        self.logger = setup_logger()
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        self.model = "gpt-4o-mini"
        self.gmail_fetcher = gmail_fetcher
        self.total_processed = 0
        self.total_kept = 0
        self.total_deleted = 0
        self.start_time = time.time()
        self.delete_queue = []
        
        # Setup console display
        print("\033[?25l")  # Hide cursor
        self.output_buffer = []
        
        self.logger.info(f"OpenAI processor initialized with model: {self.model}")
        self.rate_limiter = TokenRateLimiter()

    def process_batch(self, messages):
        """Process a batch of messages with concurrent API calls"""
        try:
            # Process in smaller sub-batches
            sub_batch_size = 50
            sub_batches = [messages[i:i + sub_batch_size] 
                          for i in range(0, len(messages), sub_batch_size)]
            
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run concurrent analysis
            decisions = loop.run_until_complete(self._analyze_emails_concurrent(sub_batches))
            
            # Process decisions sequentially
            for decision in decisions:
                self._handle_decision(decision)
                
                # Process any pending deletions
                if len(self.delete_queue) >= 25:
                    self._process_delete_queue()
            
            loop.close()
                    
        except Exception as e:
            self.logger.error(f"Error processing batch: {str(e)}")

    async def _analyze_emails_concurrent(self, sub_batches):
        """Send emails to OpenAI for analysis concurrently"""
        try:
            client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            tasks = []
            
            for email_batch in sub_batches:
                prompt = self._construct_batch_prompt(email_batch)
                # Count tokens for this batch
                tokens = self.rate_limiter.count_tokens(prompt)
                # Wait if we need to
                await self.rate_limiter.wait_if_needed(tokens)
                
                task = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an email retention assistant expert. Respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                tasks.append(task)
            
            # Process in smaller chunks to maintain rate limit
            results = []
            for i in range(0, len(tasks), 5):  # Reduced from 10 to 5 concurrent requests
                batch = tasks[i:i+5]
                responses = await asyncio.gather(*batch)
                results.extend(responses)
                await asyncio.sleep(1)  # Small delay between chunks
            
            decisions = []
            for response in results:
                result = json.loads(response.choices[0].message.content)
                decisions.extend(result.get('decisions', []))
                
            return decisions
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            return []

    def _handle_decision(self, decision):
        try:
            message = f"[{decision['decision']}] Subject: {decision['subject'][:50]}..."
            self.output_buffer.append(message)
            
            if decision['decision'] == 'KEEP':
                self.total_kept += 1
            elif decision['decision'] == 'DELETE':
                self.total_deleted += 1
                self.delete_queue.append(decision['email_id'])
            
            self.total_processed += 1
            self._update_display()
            
        except Exception as e:
            self.logger.error(f"Error handling decision: {str(e)}")

    def _process_delete_queue(self):
        """Process queued emails for deletion"""
        if self.delete_queue:
            for email_id in self.delete_queue:
                success = self.gmail_fetcher.delete_email(email_id)
                if success:
                    self.logger.debug(f"Successfully deleted email: {email_id}")
                else:
                    self.logger.error(f"Failed to delete email: {email_id}")
            self.delete_queue.clear()

    def _construct_batch_prompt(self, emails):
        """Construct prompt for batch email retention analysis"""
        email_list = []
        for email in emails:
            email_list.append(f"""
Email ID: {email['id']}
Subject: {email['subject']}
From: {email['sender']}
Has Attachments: {email['has_attachment']}
Body:
{email['body']}
---""")
        
        return f"""Analyze these emails and return a JSON object with a 'decisions' array containing analysis for each email.

{chr(10).join(email_list)}

Act as an intelligent email assistant to organize and retain emails carefully. Your goal is to ensure no potentially important emails are lost, especially those that may hold value or be needed in the future. Always err on the side of caution, keeping emails unless their irrelevance is absolutely certain. Use the following principles:

1) Retain emails with reciepts, attachments, calendar invites, or any indication of future events, actions, or deadlines.

2) Focus on context by assessing the sender's identity and frequency of contact (e.g., prioritize emails from colleagues, clients, or frequently interacted senders).

3) Evaluate thread history to understand if the email is part of an ongoing discussion or project and keep it if it contributes context or continuity.

4) Ensure your process mimics human judgment and prioritization, keeping the user's potential future needs in mind at all times."



Return ONLY a JSON object in this format:
{{
    "decisions": [
        {{
            "email_id": "id",
            "subject": "email subject",
            "decision": "KEEP|DELETE",
            "reason": "explanation"
        }}
    ]
}}"""

    def _update_display(self):
        """Update the console display with current progress"""
        elapsed_time = time.time() - self.start_time
        rate = self.total_processed / elapsed_time if elapsed_time > 0 else 0
        
        print("\033[2J\033[H")  # Clear screen and move cursor to top
        print(f"{Colors.CYAN}Email Processing Status:{Colors.RESET}")
        print(f"Processed: {self.total_processed}")
        print(f"Kept: {Colors.GREEN}{self.total_kept}{Colors.RESET}")
        print(f"Deleted: {Colors.RED}{self.total_deleted}{Colors.RESET}")
        print(f"Rate: {rate:.2f} emails/second")
        print(f"\n{Colors.CYAN}Recent Decisions:{Colors.RESET}")
        
        # Show last 10 decisions with color coding
        for message in self.output_buffer[-10:]:
            if '[KEEP]' in message:
                message = message.replace('[KEEP]', f'{Colors.GREEN}[KEEP]{Colors.RESET}')
            elif '[DELETE]' in message:
                message = message.replace('[DELETE]', f'{Colors.RED}[DELETE]{Colors.RESET}')
            print(message)
