import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from app.models.schemas import CompanyInfo

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class EmailGenerator:
    """
    A class for generating personalized cold emails using Google's Gemini AI.
    """
    
    def __init__(self):
        """
        Initialize the EmailGenerator with the Gemini API.
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("Google API key not found. Please set GOOGLE_API_KEY in .env file")
            raise ValueError("Google API key not found. Please set GOOGLE_API_KEY in .env file")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        logger.info("EmailGenerator initialized with Gemini API")

    def generate_email(self, company_data: CompanyInfo, sender_info: dict) -> dict:
        """
        Generate a personalized cold email using Gemini.
        
        Args:
            company_data: Extracted company information
            sender_info: Information about the sender and their company
            
        Returns:
            dict: Generated email with subject and body
        """
        # Format the company data for the prompt
        company_name = company_data.name or "the company"
        company_description = company_data.description or ""
        company_about = company_data.about or ""
        products_services = ", ".join(company_data.products_services) if company_data.products_services else ""
        company_values = ", ".join(company_data.values) if company_data.values else ""
        company_industry = company_data.industry or "your industry"
        
        # Get sender information
        sender_name = sender_info.get('name', 'Our Team')
        sender_company = sender_info.get('company', 'Our AI Company')
        sender_specialization = sender_info.get('specialization', 'AI solutions for businesses')
        sender_phone = sender_info.get('phone', '[Phone Number]')
        sender_website = sender_info.get('website', '[Website]')
        
        # Create a detailed prompt for Gemini with enhanced focus on value proposition
        prompt = f"""
        You are an expert cold email writer for an AI company. Using the company information below, create a personalized, concise, and compelling cold email that offers AI solutions tailored to their specific business needs.

        COMPANY INFORMATION:
        Name: {company_name}
        Description: {company_description}
        About: {company_about}
        Products/Services: {products_services}
        Industry: {company_industry}
        Values: {company_values}
        
        SENDER INFORMATION:
        Name: {sender_name}
        Company: {sender_company}
        Specialization: {sender_specialization}
        Phone: {sender_phone}
        Website: {sender_website}
        
        REQUIREMENTS:
        1. Keep the email under 200 words
        2. Include a personalized subject line that mentions the company name and a specific benefit
        3. Demonstrate understanding of their business and industry challenges
        4. Mention 2-3 SPECIFIC ways your AI solutions could help their business needs based on their products/services
        5. EMPHASIZE how you can be VERY HELPFUL to their business with concrete examples
        6. Create a sense of NEED for your services by highlighting problems they might be facing that your AI can solve
        7. Include a clear but non-pushy call to action (like scheduling a brief call)
        8. Avoid generic language, spam-like phrases, and excessive formality
        9. Make it sound like it's written by a thoughtful human, not AI
        10. Do not mention that you scraped their website
        11. If the company has specific values, subtly align with them
        12. Use a professional but conversational tone
        13. Include the sender's name, company, phone number, and website in the signature

        FORMAT YOUR RESPONSE AS:
        Subject: [email subject]

        [email body with appropriate greeting and signature including the sender's name, company, phone number, and website]
        """
        
        try:
            logger.info(f"Generating email for {company_name}")
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract subject and body
            lines = response_text.strip().split('\n')
            subject_line = ""
            email_body = ""
            
            # Find the subject line
            for i, line in enumerate(lines):
                if line.lower().startswith("subject:"):
                    subject_line = line.replace('Subject:', '').strip()
                    email_body = '\n'.join(lines[i+1:]).strip()
                    break
            
            # If subject line wasn't found in the expected format, make a best guess
            if not subject_line and lines:
                subject_line = lines[0].strip()
                email_body = '\n'.join(lines[1:]).strip()
            
            logger.info(f"Successfully generated email with subject: {subject_line}")
            
            # Replace placeholders in the email body if they exist
            email_body = email_body.replace('[Phone Number]', sender_phone)
            email_body = email_body.replace('[Website]', sender_website)
            
            return {
                "email_subject": subject_line,
                "email_body": email_body,
                "company_info": company_data
            }
            
        except Exception as e:
            logger.error(f"Error generating email: {e}")
            # Provide a fallback response
            return {
                "email_subject": f"AI Solutions for {company_name}",
                "email_body": f"Dear {company_name} Team,\n\nI recently came across your company and was impressed by what you're doing in the {company_industry} space. I believe our AI solutions at {sender_company} could help enhance your operations.\n\nWould you be open to a brief conversation about how we might be able to support your goals?\n\nBest regards,\n{sender_name}\n{sender_company}\n{sender_phone}\n{sender_website}",
                "company_info": company_data
            }
