import logging
import re
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def validate_url(url: str) -> bool:
    """
    Validate if a URL is properly formatted and accessible.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception as e:
        logger.error(f"URL validation error: {e}")
        return False


def clean_text(text: str) -> str:
    """
    Clean and normalize text by removing extra whitespace and special characters.
    
    Args:
        text: Text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
        
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that might interfere with processing
    text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
    
    return text.strip()


def extract_domain_name(url: str) -> str:
    """
    Extract the domain name from a URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        str: Domain name
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain
    except Exception as e:
        logger.error(f"Domain extraction error: {e}")
        return ""


def format_company_name(name: str) -> str:
    """
    Format a company name by removing common suffixes and cleaning.
    
    Args:
        name: Company name to format
        
    Returns:
        str: Formatted company name
    """
    if not name:
        return ""
        
    # Remove common company suffixes
    suffixes = [
        "Inc", "LLC", "Ltd", "Limited", "Corp", "Corporation", 
        "Co", "Company", "GmbH", "LLP", "LP", "S.A.", "AG", "PLC"
    ]
    
    # Create a regex pattern for suffixes with optional punctuation
    pattern = r'(?:,?\s+(?:' + '|'.join(suffixes) + r')\.?)$'
    
    # Remove the suffix
    cleaned_name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    return cleaned_name.strip()


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to a maximum length, adding ellipsis if truncated.
    
    Args:
        text: Text to truncate
        max_length: Maximum length of the text
        
    Returns:
        str: Truncated text
    """
    if not text or len(text) <= max_length:
        return text
        
    return text[:max_length].rsplit(' ', 1)[0] + '...'


def create_error_response(error_message: str, status_code: int = 500) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error_message: Error message
        status_code: HTTP status code
        
    Returns:
        dict: Error response dictionary
    """
    logger.error(f"Error: {error_message}")
    return {
        "status": "error",
        "status_code": status_code,
        "message": error_message
    }


def sanitize_company_data(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize and clean company data to ensure it's in a consistent format.
    
    Args:
        company_data: Raw company data
        
    Returns:
        dict: Sanitized company data
    """
    sanitized = {}
    
    for key, value in company_data.items():
        if isinstance(value, str):
            sanitized[key] = clean_text(value)
        elif isinstance(value, list):
            sanitized[key] = [clean_text(item) if isinstance(item, str) else item for item in value]
        else:
            sanitized[key] = value
            
    return sanitized
