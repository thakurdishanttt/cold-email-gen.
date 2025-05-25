from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from typing import Dict, Any, Optional, List

from app.models.schemas import EmailRequest, EmailResponse, CompanyInfo, SendEmailRequest, SendEmailResponse, GenerateAndSendRequest, GmailAuthRequest, GmailAuthResponse
from app.scraper.website_scraper import WebsiteScraper
from app.services.email_generator import EmailGenerator
from app.services.gmail_sender import GmailSender
from app.utils.helpers import validate_url, create_error_response, extract_domain_name

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Cold Email Generator API",
    description="API for generating personalized cold emails based on company websites using Gemini AI",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your AI company information - customize this
YOUR_COMPANY_INFO = {
    "name": "AI Solutions Inc.",
    "company": "AI Solutions Inc.",
    "specialization": "Custom AI solutions for business optimization and growth",
}

# Cache for storing previously scraped websites to avoid redundant scraping
website_cache = {}


async def get_company_data(url: str, company_name: Optional[str] = None) -> CompanyInfo:
    """
    Get company data either from cache or by scraping the website.
    
    Args:
        url: Website URL
        company_name: Optional company name
        
    Returns:
        CompanyInfo: Extracted company information
    """
    domain = extract_domain_name(url)
    cache_key = f"{domain}_{int(time.time() / (3600 * 24))}"  # Cache key with daily expiration
    
    # Check if we have cached data for this domain
    if cache_key in website_cache:
        logger.info(f"Using cached data for {domain}")
        company_data = website_cache[cache_key]
    else:
        # Scrape the website
        logger.info(f"Scraping website: {url}")
        scraper = WebsiteScraper(url)
        company_data = scraper.scrape()
        
        # Cache the results
        website_cache[cache_key] = company_data
        
    # If company name was provided, use it
    if company_name:
        company_data.name = company_name
        
    return company_data


@app.post("/api/generate-email", response_model=EmailResponse)
async def generate_email(request: EmailRequest, background_tasks: BackgroundTasks):
    """
    Generate a personalized cold email based on a company website.
    
    Args:
        request: Email generation request containing website URL and optional parameters
        background_tasks: FastAPI background tasks
        
    Returns:
        EmailResponse: Generated email with subject, body, and company info
    """
    try:
        # Validate URL
        if not validate_url(str(request.website_url)):
            raise HTTPException(status_code=400, detail="Invalid website URL")
            
        # Get company data (either from cache or by scraping)
        company_data = await get_company_data(str(request.website_url), request.company_name)
        
        # Prepare sender information
        sender_info = YOUR_COMPANY_INFO.copy()
        if request.sender_name:
            sender_info["name"] = request.sender_name
        if request.sender_company:
            sender_info["company"] = request.sender_company
            
        # Generate the email
        email_generator = EmailGenerator()
        email_response = email_generator.generate_email(company_data, sender_info)
        
        # Schedule cache cleanup in the background
        background_tasks.add_task(cleanup_old_cache_entries)
        
        return email_response
        
    except Exception as e:
        logger.error(f"Error generating email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating email: {str(e)}")


@app.post("/api/send-email", response_model=SendEmailResponse)
async def send_email(request: SendEmailRequest):
    """
    Send an email using Gmail via Composio integration.
    
    Args:
        request: Email sending request containing recipient, subject, and body
        
    Returns:
        SendEmailResponse: Result of the email sending operation
    """
    try:
        # Initialize the Gmail sender with the user's entity ID
        # Default to "default" if not specified
        entity_id = getattr(request, "entity_id", "default")
        gmail_sender = GmailSender(entity_id=entity_id)
        
        # Send the email
        result = gmail_sender.send_email(
            to_email=request.to_email,
            subject=request.subject,
            body=request.body,
            cc=request.cc,
            bcc=request.bcc
        )
        
        # Return the result
        return SendEmailResponse(
            success=result.get("success", False),
            message=result.get("message", "Unknown error"),
            data=result.get("data")
        )
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")


@app.post("/api/gmail/setup", response_model=GmailAuthResponse)
async def setup_gmail(request: GmailAuthRequest):
    """
    Setup Gmail integration and get authentication URL.
    
    Args:
        request: Gmail authentication request containing entity ID
    
    Returns:
        GmailAuthResponse: Authentication result with redirect URL if needed
    """
    try:
        # Initialize the Gmail sender with the user's entity ID
        gmail_sender = GmailSender(entity_id=request.entity_id)
        
        # Setup Gmail integration
        result = gmail_sender.setup_gmail_integration()
        
        # Add a note about authentication limitations
        message = result.get("message", "Unknown error")
        if result.get("success", False):
            message += " Note: All emails will be sent through the Composio organization account, even with different entity IDs."
            
        # Return the result
        return GmailAuthResponse(
            success=result.get("success", False),
            message=message,
            redirect_url=result.get("redirect_url"),
            entity_id=request.entity_id
        )
        
    except Exception as e:
        logger.error(f"Error setting up Gmail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error setting up Gmail: {str(e)}")


# Endpoint removed (redundant with /api/send-email)


# Endpoint removed (redundant with /api/generate-and-send-email)


@app.post("/api/generate-and-send-email", response_model=SendEmailResponse)
async def generate_and_send_email(request: GenerateAndSendRequest, background_tasks: BackgroundTasks):
    """
    Generate and send a personalized cold email based on a company website in one step.
    
    Args:
        request: Combined request for generating and sending an email
        background_tasks: FastAPI background tasks
        
    Returns:
        SendEmailResponse: Result of the email sending operation
    """
    try:
        # Validate URL
        if not validate_url(str(request.website_url)):
            raise HTTPException(status_code=400, detail="Invalid website URL")
            
        # Get company data (either from cache or by scraping)
        company_data = await get_company_data(str(request.website_url), request.company_name)
        
        # Prepare sender information
        sender_info = YOUR_COMPANY_INFO.copy()
        if request.sender_name:
            sender_info["name"] = request.sender_name
        if request.sender_company:
            sender_info["company"] = request.sender_company
        if hasattr(request, 'sender_phone') and request.sender_phone:
            sender_info["phone"] = request.sender_phone
        if hasattr(request, 'sender_website') and request.sender_website:
            sender_info["website"] = request.sender_website
            
        # Generate the email
        email_generator = EmailGenerator()
        email_response = email_generator.generate_email(company_data, sender_info)
        
        # Prepare the email sending request
        send_request = SendEmailRequest(
            to_email=request.to_email,
            subject=email_response["email_subject"],
            body=email_response["email_body"],
            from_name=request.sender_name,
            cc=request.cc,
            bcc=request.bcc,
            entity_id=request.entity_id
        )
        
        # Send the email
        result = await send_email(send_request)
        
        # Add company info to the result
        if hasattr(result, "data") and result.data is None:
            result.data = {}
        if hasattr(result, "data"):
            result.data["company_info"] = email_response["company_info"]
            result.data["email_subject"] = email_response["email_subject"]
        
        # Schedule cache cleanup in the background
        background_tasks.add_task(cleanup_old_cache_entries)
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating and sending email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating and sending email: {str(e)}")


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint to verify the service is running.
    
    Returns:
        dict: Health status
    """
    return {"status": "healthy", "version": app.version}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    Custom exception handler for HTTP exceptions.
    
    Args:
        request: Request that caused the exception
        exc: The exception
        
    Returns:
        JSONResponse: Formatted error response
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc.detail, exc.status_code)
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """
    General exception handler for all other exceptions.
    
    Args:
        request: Request that caused the exception
        exc: The exception
        
    Returns:
        JSONResponse: Formatted error response
    """
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=create_error_response("An unexpected error occurred", 500)
    )


def cleanup_old_cache_entries():
    """
    Clean up old cache entries to prevent memory issues.
    """
    current_day = int(time.time() / (3600 * 24))
    keys_to_remove = []
    
    for key in website_cache:
        # Extract the day from the cache key
        try:
            domain, day_str = key.rsplit('_', 1)
            day = int(day_str)
            
            # Remove entries older than 7 days
            if current_day - day > 7:
                keys_to_remove.append(key)
        except (ValueError, IndexError):
            # If the key format is invalid, remove it
            keys_to_remove.append(key)
    
    # Remove the old entries
    for key in keys_to_remove:
        website_cache.pop(key, None)
    
    if keys_to_remove:
        logger.info(f"Cleaned up {len(keys_to_remove)} old cache entries")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
