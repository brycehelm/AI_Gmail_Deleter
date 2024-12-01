# Gmail Email Sorter

An intelligent email management tool that uses OpenAI's GPT model to analyze and sort your Gmail messages, helping you maintain a cleaner inbox by automatically identifying which emails to keep or delete.

## Features

- Batch processing of emails for efficient analysis
- Concurrent OpenAI API calls for faster processing
- Intelligent email retention decisions based on content and context
- Real-time console-based progress visualization
- Rate-limited API calls to stay within usage limits
- Comprehensive logging system

## Prerequisites

- Python 3.8+
- Gmail account
- Google Cloud Project with Gmail API enabled
- OpenAI API key

## Setup

1. Clone the repository:


bash
git clone <repository-url>
cd gmail-sorter

2. Install dependencies:


bash
pip install -r requirements.txt

3. Set up credentials:
   - Copy `.env.example` to `.env` and add your OpenAI API key
   - Copy `credentials/credentials.json.example` to `credentials/credentials.json`
   - Set up Google Cloud Project and add Gmail API credentials

4. Configure Google Cloud:
   - Go to Google Cloud Console
   - Create a new project
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download credentials and save as `credentials/credentials.json`

## Usage

Run the script:


bash
python run.py

The application will:
1. Authenticate with Gmail
2. Fetch emails in batches
3. Analyze them using OpenAI's model
4. Make retention decisions
5. Process deletions automatically

## Configuration

- `batch_size`: Number of emails to process in each batch (default: 500)
- `max_emails`: Maximum number of emails to process (default: 50,000)
- Rate limits: 200,000 tokens per minute for OpenAI API

## Retention Criteria

Emails are analyzed based on:
1. Presence of attachments or calendar invites
2. Sender importance
3. Content relevance
4. Future reference value
5. Project/discussion context

## Directory Structure

```
├── src/
│   ├── main.py           # Main application logic
│   ├── gmail_fetcher.py  # Gmail API interactions
│   ├── openai_processor.py # OpenAI processing logic
│   └── utils/
│       └── logger.py     # Logging configuration
├── credentials/          # API credentials
├── logs/                # Application logs
└── batches/            # Temporary batch storage
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Security Note

Never commit your actual credentials or API keys. Use the example files as templates and keep your real credentials private.



