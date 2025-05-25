# Cold Email Generator with FastAPI and Gemini

## Project Overview

This documentation outlines how to build a FastAPI application that generates personalized cold emails for potential clients based on their company website. The application will:

1. Accept a company website URL as input
2. Scrape and analyze the website content 
3. Use Gemini to generate a tailored cold email pitch
4. Return the customized email that highlights how your AI solutions can benefit their business

## Prerequisites

- Python 3.12
- FastAPI
- Google API Key for Gemini access
- Basic understanding of web scraping and API development

## Project Structure

```
cold-email-generator/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point
│   ├── scraper/
│   │   ├── __init__.py
│   │   └── website_scraper.py   # Website scraping functionality
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic models for request/response
│   ├── services/
│   │   ├── __init__.py
│   │   └── email_generator.py   # Gemini integration for email generation
│   └── utils/
│       ├── __init__.py
│       └── helpers.py           # Utility functions
├── requirements.txt
├── .env                         # Environment variables (API keys)
└── README.md
```

## Setup Instructions

### 1. Environment Setup

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install fastapi uvicorn google-generativeai beautifulsoup4 requests python-dotenv
```

### 2. Environment Variables

Create a `.env` file in the root directory:

```
GOOGLE_API_KEY=your_google_api_key_here
```

### 3. Implementation

#### Step 1: Define Pydantic Models

Create `app/models/schemas.py`:

```python
from pydantic import BaseModel, HttpUrl

class EmailRequest(BaseModel):
    website_url: HttpUrl
    company_name: str = None

class EmailResponse(BaseModel):
    email_subject: str
    email_body: str
    company_info: dict
```

#### Step 2: Website Scraper

Create `app/scraper/website_scraper.py`:

```python
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

class WebsiteScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.visited_urls = set()
        self.company_data = {
            "name": "",
            "description": "",
            "products_services": [],
            "about": "",
            "contact": "",
            "industry": "",
            "values": [],
            "team": [],
            "clients": []
        }
        # Limit the number of pages to scrape
        self.max_pages = 5
        self.pages_visited = 0

    def scrape(self):
        """Main method to scrape the website"""
        try:
            # Start with home page
            self._scrape_page(self.base_url)
            
            # Try to scrape common important pages
            important_pages = ["about", "about-us", "services", "products", "solutions"]
            for page in important_pages:
                if self.pages_visited >= self.max_pages:
                    break
                    
                page_url = urljoin(self.base_url, page)
                if page_url not in self.visited_urls:
                    self._scrape_page(page_url)
            
            return self.company_data
        except Exception as e:
            print(f"Error scraping website: {e}")
            return self.company_data

    def _scrape_page(self, url):
        """Scrape a single page and extract relevant information"""
        if url in self.visited_urls or self.pages_visited >= self.max_pages:
            return
        
        try:
            self.visited_urls.add(url)
            self.pages_visited += 1
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract page information
            self._extract_company_name(soup)
            self._extract_description(soup)
            self._extract_about_info(soup)
            self._extract_products_services(soup)
            
        except Exception as e:
            print(f"Error processing {url}: {e}")

    def _extract_company_name(self, soup):
        """Extract company name from the page"""
        if not self.company_data["name"]:
            # Try logo alt text
            logo = soup.find('img', {'alt': re.compile('logo', re.I)})
            if logo and logo.get('alt'):
                name = logo.get('alt').replace('logo', '').replace('Logo', '').strip()
                if name:
                    self.company_data["name"] = name
                    return
            
            # Try title
            title = soup.find('title')
            if title and title.text:
                name = title.text.split('|')[0].split('-')[0].strip()
                if name:
                    self.company_data["name"] = name
                    return

    def _extract_description(self, soup):
        """Extract company description from meta tags or main content"""
        if not self.company_data["description"]:
            # Try meta description
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                self.company_data["description"] = meta_desc.get('content')
                return
                
            # Try hero section text
            hero = soup.find(['div', 'section'], {'class': re.compile('hero|banner|jumbotron', re.I)})
            if hero:
                paragraphs = hero.find_all('p')
                if paragraphs:
                    self.company_data["description"] = paragraphs[0].text.strip()
                    return

    def _extract_about_info(self, soup):
        """Extract about information"""
        # Check if we're on an about page
        if 'about' in soup.find('title').text.lower() if soup.find('title') else False:
            about_content = ""
            main_content = soup.find(['main', 'div'], {'class': re.compile('content|main', re.I)})
            
            if main_content:
                paragraphs = main_content.find_all('p')
                about_content = " ".join([p.text.strip() for p in paragraphs[:3]])
            
            if about_content:
                self.company_data["about"] = about_content

    def _extract_products_services(self, soup):
        """Extract products and services information"""
        service_sections = soup.find_all(['div', 'section'], {'class': re.compile('service|product|solution', re.I)})
        
        for section in service_sections:
            headings = section.find_all(['h1', 'h2', 'h3'])
            for heading in headings:
                if heading.text.strip() and heading.text.strip() not in self.company_data["products_services"]:
                    self.company_data["products_services"].append(heading.text.strip())
```

#### Step 3: Email Generator Service with Gemini

Create `app/services/email_generator.py`:

```python
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class EmailGenerator:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Google API key not found. Please set GOOGLE_API_KEY in .env file")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')

    def generate_email(self, company_data, your_company_info):
        """Generate a personalized cold email using Gemini"""
        # Format the company data for the prompt
        company_name = company_data.get("name", "the company")
        company_description = company_data.get("description", "")
        company_about = company_data.get("about", "")
        products_services = ", ".join(company_data.get("products_services", []))
        
        # Create the prompt for Gemini
        prompt = f"""
        You are an expert cold email writer for an AI company. Using the company information below, create a personalized, concise, and compelling cold email that offers AI solutions tailored to their specific business needs.

        COMPANY INFORMATION:
        Name: {company_name}
        Description: {company_description}
        About: {company_about}
        Products/Services: {products_services}

        YOUR COMPANY INFORMATION:
        Name: {your_company_info.get('name', 'Our AI Company')}
        Specialization: {your_company_info.get('specialization', 'AI solutions for businesses')}
        
        REQUIREMENTS:
        1. Keep the email under 200 words
        2. Include a personalized subject line
        3. Demonstrate understanding of their business
        4. Mention 1-2 specific ways your AI solutions could help their specific business needs
        5. Include a clear but non-pushy call to action
        6. Avoid generic language and spam-like phrases
        7. Make it sound like it's written by a thoughtful human, not AI
        8. Do not mention that you scraped their website

        FORMAT YOUR RESPONSE AS:
        Subject: [email subject]

        [email body]
        """
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract subject and body
            lines = response_text.strip().split('\n')
            subject_line = lines[0].replace('Subject:', '').strip()
            email_body = '\n'.join(lines[1:]).strip()
            
            return {
                "email_subject": subject_line,
                "email_body": email_body,
                "company_info": company_data
            }
        except Exception as e:
            print(f"Error generating email: {e}")
            return {
                "email_subject": f"AI Solutions for {company_name}",
                "email_body": "Error generating personalized email. Please try again later.",
                "company_info": company_data
            }
```

#### Step 4: FastAPI Application

Create `app/main.py`:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import EmailRequest, EmailResponse
from app.scraper.website_scraper import WebsiteScraper
from app.services.email_generator import EmailGenerator

# Initialize FastAPI app
app = FastAPI(
    title="Cold Email Generator API",
    description="API for generating personalized cold emails based on company websites",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your AI company information - customize this
YOUR_COMPANY_INFO = {
    "name": "AI Solutions Inc.",
    "specialization": "Custom AI solutions for business optimization and growth",
}

@app.post("/generate-email", response_model=EmailResponse)
async def generate_email(request: EmailRequest):
    """
    Generate a personalized cold email based on a company website
    """
    try:
        # Step 1: Scrape the website
        scraper = WebsiteScraper(str(request.website_url))
        company_data = scraper.scrape()
        
        # If company name was provided, use it
        if request.company_name:
            company_data["name"] = request.company_name
            
        # Step 2: Generate the email using Gemini
        email_generator = EmailGenerator()
        email_response = email_generator.generate_email(company_data, YOUR_COMPANY_INFO)
        
        return email_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating email: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

### 4. Running the Application

```bash
# From the project root directory
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### Generate Email

**Endpoint:** `POST /generate-email`

**Request Body:**
```json
{
  "website_url": "https://example.com",
  "company_name": "Example Corp" // Optional, will be extracted from website if not provided
}
```

**Response:**
```json
{
  "email_subject": "Enhancing Example Corp's Digital Experience with AI",
  "email_body": "Dear [Name],\n\nI recently visited Example Corp's website and was impressed by your innovative approach to...",
  "company_info": {
    "name": "Example Corp",
    "description": "Example Corp provides enterprise solutions...",
    "products_services": ["Product A", "Service B"],
    "about": "Founded in 2010, Example Corp...",
    "contact": "",
    "industry": "",
    "values": [],
    "team": [],
    "clients": []
  }
}
```

## Enhancement Ideas

1. **Caching**: Implement Redis to cache scraped website data and reduce processing time for repeated requests.

2. **Email Templates**: Create multiple email templates for different industries or use cases.

3. **Sentiment Analysis**: Analyze the tone of the company's website to match the email tone.

4. **Company Contact Discovery**: Extract contact information to personalize the email further.

5. **Error Handling**: Implement more robust error handling for website scraping failures.

6. **Rate Limiting**: Add rate limiting to prevent abuse of the API.

7. **Authentication**: Add API key authentication for secure access.

8. **Logging**: Implement detailed logging for debugging and analytics.

## Potential Challenges and Solutions

### Challenge: Website Anti-Scraping Measures

**Solution**: 
- Use rotating user agents and implement delay between requests
- Consider using headless browsers like Playwright or Selenium for JavaScript-heavy websites

### Challenge: Gemini API Rate Limits

**Solution**:
- Implement a queue system for processing requests
- Cache common responses

### Challenge: Email Quality

**Solution**:
- Fine-tune your prompts based on successful email templates
- Implement a feedback loop where users can rate the generated emails

## Conclusion

This FastAPI application provides an efficient way to generate personalized cold emails based on company websites. By analyzing the company's web presence and using Gemini to craft tailored messages, you can create compelling outreach that highlights how your AI solutions can address specific business needs.

Remember to continuously refine the email generation prompts based on response rates and feedback to improve the system over time.
