import os.path
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from .utils.logger import setup_logger
from .utils.text_cleaner import clean_text, clean_html

class GmailFetcher:
    def __init__(self):
        self.logger = setup_logger()
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.readonly',  # For reading emails
            'https://www.googleapis.com/auth/gmail.modify'     # For modifying/trashing emails
        ]
        self.creds = None
        self.service = None

    def authenticate(self):
        """Handles the OAuth2 authentication flow."""
        if os.path.exists('credentials/token.json'):
            self.creds = Credentials.from_authorized_user_file('credentials/token.json', self.SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials/credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open('credentials/token.json', 'w') as token:
                token.write(self.creds.to_json())

        self.service = build('gmail', 'v1', credentials=self.creds)
        self.logger.info("Successfully authenticated with Gmail API")

    def fetch_batch(self, max_results=500, page_token=None):
        """Fetches a batch of emails from Gmail using batch requests."""
        try:
            # Get list of message IDs first
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                pageToken=page_token
            ).execute()

            messages = results.get('messages', [])
            processed_messages = []
            message_map = {}

            # Process in chunks of 20
            for i in range(0, len(messages), 20):
                chunk = messages[i:i + 20]
                batch = self.service.new_batch_http_request()

                def callback(request_id, response, exception):
                    if exception is not None:
                        self.logger.error(f"Error fetching message {request_id}: {str(exception)}")
                        return
                    
                    headers = response['payload']['headers']
                    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
                    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                    body = self._get_message_body(response['payload'])
                    
                    message_map[request_id] = {
                        'id': response['id'],
                        'sender': clean_text(sender),
                        'subject': clean_text(subject),
                        'body': clean_text(clean_html(body)),
                        'has_attachment': bool(response.get('payload', {}).get('parts', []))
                    }

                # Add requests to current batch
                for message in chunk:
                    batch.add(
                        self.service.users().messages().get(
                            userId='me',
                            id=message['id'],
                            format='full'
                        ),
                        callback=callback,
                        request_id=message['id']
                    )

                # Execute current batch
                self.logger.info(f"Executing batch request for {len(chunk)} emails")
                batch.execute()

            # Process all results in order
            for message in messages:
                if message['id'] in message_map:
                    processed_messages.append(message_map[message['id']])

            return {
                'messages': processed_messages,
                'nextPageToken': results.get('nextPageToken')
            }

        except Exception as e:
            self.logger.error(f"Error fetching emails: {str(e)}")
            raise

    def _get_message_body(self, payload):
        """Extract message body from payload, handling both plain text and HTML content."""
        body = ""
        
        if 'parts' in payload:
            # Try to find plain text first
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data'].encode('UTF-8')).decode('UTF-8')
                        return body
                    
            # If no plain text, try HTML
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data'].encode('UTF-8')).decode('UTF-8')
                        return clean_html(body)
                    
        elif 'body' in payload:
            if 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data'].encode('UTF-8')).decode('UTF-8')
                if payload['mimeType'] == 'text/html':
                    body = clean_html(body)
                
        return body

    def delete_email(self, email_id):
        """Delete an email by its ID."""
        try:
            self.service.users().messages().trash(
                userId='me',
                id=email_id
            ).execute()
            self.logger.info(f"Successfully deleted email: {email_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete email {email_id}: {str(e)}")
            return False
