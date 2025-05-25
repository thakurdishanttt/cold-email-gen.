from pydantic import BaseModel, HttpUrl, Field, EmailStr
from typing import List, Dict, Optional, Union, Any


class EmailRequest(BaseModel):
    """
    Request model for generating a cold email based on a company website.
    """
    website_url: HttpUrl = Field(..., description="URL of the company website to analyze")
    company_name: Optional[str] = Field(None, description="Optional company name if known")
    sender_name: Optional[str] = Field(None, description="Name of the sender")
    sender_company: Optional[str] = Field(None, description="Name of the sender's company")


class CompanyInfo(BaseModel):
    """
    Model for storing extracted company information.
    """
    name: str = ""
    description: str = ""
    products_services: List[str] = []
    about: str = ""
    contact: str = ""
    industry: str = ""
    values: List[str] = []
    team: List[str] = []
    clients: List[str] = []


class EmailResponse(BaseModel):
    """
    Response model for the generated cold email.
    """
    email_subject: str
    email_body: str
    company_info: CompanyInfo


class SendEmailRequest(BaseModel):
    """
    Request model for sending an email.
    """
    to_email: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")

    from_name: Optional[str] = Field(None, description="Sender name (optional)")
    cc: Optional[List[EmailStr]] = Field(None, description="List of CC recipients (optional)")
    bcc: Optional[List[EmailStr]] = Field(None, description="List of BCC recipients (optional)")
    entity_id: Optional[str] = Field("default", description="Entity ID for Gmail connection")


class SendEmailResponse(BaseModel):
    """
    Response model for sending an email.
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class GenerateAndSendRequest(BaseModel):
    """
    Request model for generating and sending an email in one step.
    """
    website_url: HttpUrl = Field(..., description="URL of the company website to analyze")
    to_email: EmailStr = Field(..., description="Recipient email address")
    company_name: Optional[str] = Field(None, description="Optional company name if known")
    sender_name: Optional[str] = Field(None, description="Name of the sender")

    sender_company: Optional[str] = Field(None, description="Name of the sender's company")
    sender_phone: Optional[str] = Field(None, description="Phone number of the sender")
    sender_website: Optional[str] = Field(None, description="Website of the sender's company")
    cc: Optional[List[EmailStr]] = Field(None, description="List of CC recipients (optional)")
    bcc: Optional[List[EmailStr]] = Field(None, description="List of BCC recipients (optional)")
    entity_id: Optional[str] = Field("default", description="Entity ID for Gmail connection")


class GmailAuthRequest(BaseModel):
    """
    Request model for Gmail authentication setup.
    """
    entity_id: Optional[str] = Field("default", description="Entity ID for Gmail connection")


class GmailAuthResponse(BaseModel):
    """
    Response model for Gmail authentication.
    """
    success: bool
    message: str
    redirect_url: Optional[str] = None
    entity_id: str
