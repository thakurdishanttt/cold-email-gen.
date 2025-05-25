# Cold Email Generator

A FastAPI application that generates personalized cold emails for businesses using Google's Gemini AI. The service analyzes company websites to understand their business and crafts tailored emails offering AI solutions.

## Features

- **Intelligent Web Scraping**: Extracts meaningful company information from various website structures
- **AI-Powered Email Generation**: Creates personalized emails using Google's Gemini AI
- **Clean API Design**: Well-structured FastAPI endpoints with proper validation and error handling
- **Caching System**: Reduces redundant scraping of the same websites

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

## Prerequisites

- Python 3.12
- Google API Key for Gemini access

## Setup Instructions

### 1. Clone the repository

```bash
git clone <repository-url>
cd cold-email-generator
```

### 2. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root directory:

```
GOOGLE_API_KEY=your_google_api_key_here
```

You can obtain a Google API key from the [Google AI Studio](https://makersuite.google.com/).

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### Generate Email

**Endpoint:** `POST /api/generate-email`

**Request Body:**
```json
{
  "website_url": "https://example.com",
  "company_name": "Example Corp",  // Optional
  "sender_name": "John Doe",       // Optional
  "sender_company": "AI Solutions" // Optional
}
```

**Response:**
```json
{
  "email_subject": "Enhancing Example Corp's Digital Experience with AI",
  "email_body": "Dear Example Corp Team,\n\nI recently visited your website and was impressed by your innovative approach...",
  "company_info": {
    "name": "Example Corp",
    "description": "Example Corp provides enterprise solutions...",
    "products_services": ["Product A", "Service B"],
    "about": "Founded in 2010, Example Corp...",
    "contact": "Email: contact@example.com | Phone: (123) 456-7890",
    "industry": "Technology",
    "values": ["Innovation", "Customer Focus", "Integrity"],
    "team": [],
    "clients": []
  }
}
```

### Health Check

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## Best Practices

### Web Scraping

- The application uses a respectful scraping approach with proper headers and rate limiting
- Only scrapes a limited number of pages per website to avoid excessive requests
- Focuses on common pages like home, about, and services pages

### Email Generation

- Prompts are designed to create personalized, non-generic emails
- Emails highlight specific AI solutions relevant to the company's business
- The tone is professional but conversational
- Includes a clear call to action

## Error Handling

The application includes comprehensive error handling for:
- Invalid URLs
- Failed website scraping
- API rate limits
- Gemini API errors

## Customization

You can customize your company information in `app/main.py`:

```python
YOUR_COMPANY_INFO = {
    "name": "AI Solutions Inc.",
    "company": "AI Solutions Inc.",
    "specialization": "Custom AI solutions for business optimization and growth",
}
```

## Future Enhancements

- Add authentication for API access
- Implement more advanced web scraping for JavaScript-heavy websites
- Add email templates for different industries
- Implement feedback mechanism to improve email quality
- Add support for multiple languages

## License

[MIT License](LICENSE)
