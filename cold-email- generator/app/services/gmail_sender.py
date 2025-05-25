import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import Composio tools - handle gracefully if not installed
try:
    from composio_openai import ComposioToolSet, Action
    COMPOSIO_AVAILABLE = True
except ImportError:
    logger.warning("Composio package not installed. Gmail integration will not be available.")
    COMPOSIO_AVAILABLE = False


class GmailSender:
    """
    A class for sending emails using Gmail via Composio integration.
    """
    
    def __init__(self, entity_id: str = "default"):
        """
        Initialize the GmailSender with Composio integration.
        
        Args:
            entity_id: A unique identifier for the Gmail connection
        """
        self.entity_id = entity_id
        
        # Check if Composio is available
        if not COMPOSIO_AVAILABLE:
            logger.error("Composio package not installed. Please install it with: pip install composio-openai")
            raise ImportError("Composio package not installed")
        
        # Get API keys
        self.composio_api_key = os.getenv("COMPOSIO_API_KEY")
        if not self.composio_api_key:
            logger.error("Composio API key not found. Please set COMPOSIO_API_KEY in .env file")
            raise ValueError("Composio API key not found")
        
        # Initialize Composio tool set
        self.composio_tool_set = ComposioToolSet(api_key=self.composio_api_key)
        logger.info("GmailSender initialized with Composio integration")
    
    def setup_gmail_integration(self) -> Dict[str, Any]:
        """
        Setup Gmail integration if not already done.
        
        Returns:
            dict: Setup result with success status and message
        """
        try:
            # Get the Composio Entity object for this user
            entity = self.composio_tool_set.get_entity(id=self.entity_id)
            
            # Initiate connection to Gmail with the provided entity
            response = self.composio_tool_set.initiate_connection(
                app="GMAIL",
                entity_id=self.entity_id
            )
            
            # Access properties directly instead of using .get()
            if response and hasattr(response, 'redirectUrl'):
                logger.info("Gmail authentication URL generated")
                return {
                    "success": True,
                    "redirect_url": response.redirectUrl,
                    "message": "Please complete Gmail authentication by opening this URL in your browser"
                }
                
                # Check if connection is active
                if hasattr(response, 'connectedAccountId'):
                    connection = self.composio_tool_set.get_connected_account(
                        id=response.connectedAccountId,
                        entity_id=self.entity_id
                    )
                    # Check status directly as property
                    if connection and hasattr(connection, 'status') and connection.status == "ACTIVE":
                        logger.info("Gmail connection is active")
                        return {
                            "success": True,
                            "message": "Gmail connection is active"
                        }
            
            return {
                "success": False,
                "message": "Failed to setup Gmail integration"
            }
            
        except Exception as e:
            logger.error(f"Error setting up Gmail integration: {str(e)}")
            return {
                "success": False,
                "message": f"Error setting up Gmail integration: {str(e)}"
            }
    
    def send_email(self, 
                  to_email: str, 
                  subject: str, 
                  body: str, 
                  cc: Optional[List[str]] = None,
                  bcc: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send an email using Gmail via Composio integration.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            cc: List of CC recipients (optional)
            bcc: List of BCC recipients (optional)
            
        Returns:
            dict: Sending result with success status and message
        """
        try:
            # Prepare parameters for the Gmail action
            params = {
                "recipient_email": to_email,
                "subject": subject,
                "body": body
            }
            
            # Add CC and BCC if provided
            if cc:
                params["cc"] = ",".join(cc)
            
            if bcc:
                params["bcc"] = ",".join(bcc)
            
            # Execute the Gmail send action
            response = self.composio_tool_set.execute_action(
                action=Action.GMAIL_SEND_EMAIL,
                params=params,
                entity_id=self.entity_id
            )
            
            logger.info(f"Gmail API response received")
            
            # Check if response is successful
            if response:
                # Check for success information in different structures
                if hasattr(response, 'successfull') and response.successfull:
                    return {"success": True, "message": f"Email successfully sent to {to_email}"}
                elif hasattr(response, 'success') and response.success:
                    return {"success": True, "message": f"Email successfully sent to {to_email}"}
                elif hasattr(response, 'data') and response.data:
                    return {"success": True, "message": f"Email successfully sent to {to_email}"}
                elif isinstance(response, dict) and response.get('successfull'):
                    return {"success": True, "message": f"Email successfully sent to {to_email}"}
                elif isinstance(response, dict) and response.get('success'):
                    return {"success": True, "message": f"Email successfully sent to {to_email}"}
                elif isinstance(response, dict) and 'data' in response and response['data']:
                    return {"success": True, "message": f"Email successfully sent to {to_email}"}
            
            # If none of the success checks passed, return error
            error_message = None
            if hasattr(response, 'error'):
                error_message = response.error
            elif isinstance(response, dict) and 'error' in response:
                error_message = response['error']
                
            return {
                "success": False,
                "error": f"Failed to send email: {error_message or 'Unknown error in response format'}"
            }
        
        except Exception as e:
            logger.error(f"Error sending email via Gmail: {str(e)}")
            return {
                "success": False,
                "error": f"Error sending email via Gmail: {str(e)}"
            }
