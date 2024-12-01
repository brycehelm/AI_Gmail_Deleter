import re
import html
from bs4 import BeautifulSoup

def clean_html(html_content):
    """Convert HTML to plain text"""
    if not html_content:
        return ""
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
        
    # Get text content
    text = soup.get_text(separator=' ', strip=True)
    
    return text

def clean_text(text):
    """Clean plain text content"""
    if not text:
        return ""
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters and normalize
    text = re.sub(r'[^\w\s.,!?-]', ' ', text)
    
    return text.strip()
