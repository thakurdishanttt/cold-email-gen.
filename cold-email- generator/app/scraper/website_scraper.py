import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import logging
from app.models.schemas import CompanyInfo

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebsiteScraper:
    """
    A class for scraping company information from websites.
    Extracts relevant data like company name, description, products/services, etc.
    """
    
    def __init__(self, base_url: str):
        """
        Initialize the WebsiteScraper with a base URL.
        
        Args:
            base_url: The website URL to scrape
        """
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.visited_urls = set()
        self.company_data = CompanyInfo(
            name="",
            description="",
            products_services=[],
            about="",
            contact="",
            industry="",
            values=[],
            team=[],
            clients=[]
        )
        # Limit the number of pages to scrape to avoid excessive requests
        self.max_pages = 5
        self.pages_visited = 0
        
        # Common headers to mimic a browser request
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def scrape(self) -> CompanyInfo:
        """
        Main method to scrape the website and extract company information.
        
        Returns:
            CompanyInfo: Extracted company information
        """
        try:
            # Start with home page
            self._scrape_page(self.base_url)
            
            # Try to scrape common important pages that might contain valuable information
            important_pages = ["about", "about-us", "company", "services", "products", "solutions", "what-we-do"]
            for page in important_pages:
                if self.pages_visited >= self.max_pages:
                    break
                    
                page_url = urljoin(self.base_url, page)
                if page_url not in self.visited_urls:
                    self._scrape_page(page_url)
            
            # Try to infer industry if not found directly
            if not self.company_data.industry:
                self._infer_industry()
                
            # Post-process the extracted data
            self._post_process_data()
            
            logger.info(f"Completed scraping {self.pages_visited} pages from {self.domain}")
            return self.company_data
            
        except Exception as e:
            logger.error(f"Error scraping website {self.base_url}: {e}")
            return self.company_data

    def _scrape_page(self, url: str) -> None:
        """
        Scrape a single page and extract relevant information.
        
        Args:
            url: The URL of the page to scrape
        """
        if url in self.visited_urls or self.pages_visited >= self.max_pages:
            return
        
        try:
            self.visited_urls.add(url)
            self.pages_visited += 1
            
            logger.info(f"Scraping page: {url}")
            
            # Add a timeout to avoid hanging on slow sites
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to retrieve {url}, status code: {response.status_code}")
                return
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract page information
            self._extract_company_name(soup)
            self._extract_description(soup)
            self._extract_about_info(soup, url)
            self._extract_products_services(soup)
            self._extract_contact_info(soup)
            self._extract_values(soup)
            
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")

    def _extract_company_name(self, soup: BeautifulSoup) -> None:
        """
        Extract company name from the page.
        
        Args:
            soup: BeautifulSoup object of the page
        """
        if self.company_data.name:
            return
            
        # Try logo alt text
        logo = soup.find('img', {'alt': re.compile('logo', re.I)})
        if logo and logo.get('alt'):
            name = logo.get('alt').replace('logo', '').replace('Logo', '').strip()
            if name:
                self.company_data.name = name
                return
        
        # Try title
        title = soup.find('title')
        if title and title.text:
            name = title.text.split('|')[0].split('-')[0].strip()
            if name:
                self.company_data.name = name
                return
                
        # Try common header elements
        header = soup.find(['header', 'div'], {'class': re.compile('header|navbar', re.I)})
        if header:
            brand = header.find(['a', 'div', 'span'], {'class': re.compile('brand|logo-text|site-title', re.I)})
            if brand and brand.text.strip():
                self.company_data.name = brand.text.strip()
                return

    def _extract_description(self, soup: BeautifulSoup) -> None:
        """
        Extract company description from meta tags or main content.
        
        Args:
            soup: BeautifulSoup object of the page
        """
        if self.company_data.description:
            return
            
        # Try meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            self.company_data.description = meta_desc.get('content')
            return
            
        # Try open graph description
        og_desc = soup.find('meta', {'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            self.company_data.description = og_desc.get('content')
            return
                
        # Try hero section text
        hero = soup.find(['div', 'section'], {'class': re.compile('hero|banner|jumbotron|intro', re.I)})
        if hero:
            paragraphs = hero.find_all('p')
            if paragraphs:
                self.company_data.description = paragraphs[0].text.strip()
                return

    def _extract_about_info(self, soup: BeautifulSoup, url: str) -> None:
        """
        Extract about information from the page.
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page being processed
        """
        # Check if we're on an about page or company page
        is_about_page = ('about' in url.lower() or 'company' in url.lower() or 'who-we-are' in url.lower() or
                        (soup.find('title') and re.search(r'about|company|who we are', soup.find('title').text.lower())))
        
        if is_about_page or not self.company_data.about:
            about_content = ""
            
            # Look for about content in multiple potential containers with expanded selectors
            about_containers = soup.find_all(['main', 'div', 'section', 'article'], 
                                           {'class': re.compile('content|main|about|company|overview|who-we-are', re.I)})
            
            for container in about_containers:
                paragraphs = container.find_all('p')
                if paragraphs:
                    # Take first few paragraphs to avoid getting too much irrelevant content
                    about_content = " ".join([p.text.strip() for p in paragraphs[:3]])
                    if len(about_content) > 50:  # Only accept if it has substantial content
                        break
            
            # If still no content, try meta description
            if not about_content or len(about_content) < 50:
                meta_desc = soup.find('meta', {'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    about_content = meta_desc.get('content')
            
            # If still no content, try open graph description
            if not about_content or len(about_content) < 50:
                og_desc = soup.find('meta', {'property': 'og:description'})
                if og_desc and og_desc.get('content'):
                    about_content = og_desc.get('content')
            
            # Look for about headings followed by paragraphs
            if not about_content or len(about_content) < 50:
                about_headings = soup.find_all(['h1', 'h2', 'h3'], string=re.compile('about us|company|who we are', re.I))
                for heading in about_headings:
                    next_paragraph = heading.find_next('p')
                    if next_paragraph:
                        about_content = next_paragraph.text.strip()
                        if len(about_content) > 50:
                            break
            
            if about_content and len(about_content) > 20:  # Only update if we found meaningful content
                self.company_data.about = about_content

    def _extract_products_services(self, soup: BeautifulSoup) -> None:
        """
        Extract products and services information from the page.
        
        Args:
            soup: BeautifulSoup object of the page
        """
        # Look for service/product sections with expanded selectors
        service_sections = soup.find_all(['div', 'section', 'article', 'ul'], 
                                        {'class': re.compile('service|product|solution|feature|offering|capability|what-we-do', re.I)})
        
        for section in service_sections:
            headings = section.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
            for heading in headings:
                service_name = heading.text.strip()
                if service_name and service_name not in self.company_data.products_services and len(service_name) < 100:
                    self.company_data.products_services.append(service_name)
        
        # If no structured sections found, look for lists
        if not self.company_data.products_services:
            # Look for any list near service-related headings
            service_headings = soup.find_all(['h1', 'h2', 'h3'], string=re.compile('service|product|solution|offering|capability|what we do', re.I))
            
            for heading in service_headings:
                # Find the next list
                next_list = heading.find_next(['ul', 'ol'])
                if next_list:
                    items = next_list.find_all('li')
                    for item in items:
                        service_name = item.text.strip()
                        if service_name and service_name not in self.company_data.products_services and len(service_name) < 100:
                            self.company_data.products_services.append(service_name)
        
        # Check navigation menu items as they often contain service categories
        if len(self.company_data.products_services) < 3:  # Only if we don't have enough services yet
            nav_menus = soup.find_all(['nav', 'ul'], {'class': re.compile('nav|menu|main-menu', re.I)})
            for menu in nav_menus:
                items = menu.find_all('a')
                for item in items:
                    # Look for service-related links
                    if re.search(r'service|solution|offering|capability|industry', item.text.lower()):
                        service_name = item.text.strip()
                        if service_name and service_name not in self.company_data.products_services and len(service_name) < 50:
                            self.company_data.products_services.append(service_name)

    def _extract_contact_info(self, soup: BeautifulSoup) -> None:
        """
        Extract contact information from the page.
        
        Args:
            soup: BeautifulSoup object of the page
        """
        if self.company_data.contact:
            return
            
        # Look for contact sections with expanded selectors
        contact_sections = soup.find_all(['div', 'section', 'footer', 'address', 'article'], 
                                      {'class': re.compile('contact|footer|connect|get-in-touch', re.I)})
        
        contact_info = []
        
        # Process each potential contact section
        for section in contact_sections:
            section_text = section.get_text(strip=True, separator=' ')
            
            # Extract email using regex
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, section_text)
            
            # Extract phone numbers using regex - more strict pattern to avoid capturing dates
            phone_pattern = r'(?:(?:\+|00)[0-9]{1,3}[-\s]?)?(?:(?:\(\d{1,4}\)|\d{1,4})[-\s]?)?\d{3,4}[-\s]?\d{3,4}'
            phones = re.findall(phone_pattern, section_text)
            
            # Filter out short numbers that might be dates
            phones = [p for p in phones if len(re.sub(r'\D', '', p)) >= 7]
            
            if emails and "Email" not in str(contact_info):
                contact_info.append(f"Email: {emails[0]}")
            if phones and "Phone" not in str(contact_info):
                contact_info.append(f"Phone: {phones[0]}")
        
        # If no contact info found in dedicated sections, search the entire page
        if not contact_info:
            # Check for mailto links
            email_links = soup.find_all('a', href=re.compile('^mailto:', re.I))
            for link in email_links:
                email = link.get('href').replace('mailto:', '').split('?')[0].strip()
                if email and "@" in email and "Email" not in str(contact_info):
                    contact_info.append(f"Email: {email}")
                    break
            
            # Check for tel links
            phone_links = soup.find_all('a', href=re.compile('^tel:', re.I))
            for link in phone_links:
                phone = link.get('href').replace('tel:', '').strip()
                if phone and "Phone" not in str(contact_info) and len(re.sub(r'\D', '', phone)) >= 7:
                    contact_info.append(f"Phone: {phone}")
                    break
            
            # If still no contact info, search the entire page
            if not contact_info:
                page_text = soup.get_text(strip=True, separator=' ')
                
                # Extract email using regex from entire page
                emails = re.findall(email_pattern, page_text)
                if emails:
                    contact_info.append(f"Email: {emails[0]}")
                
                # Extract phone using regex from entire page with stricter filtering
                phones = re.findall(phone_pattern, page_text)
                phones = [p for p in phones if len(re.sub(r'\D', '', p)) >= 7]
                if phones:
                    contact_info.append(f"Phone: {phones[0]}")
        
        # Look for social media links
        social_links = []
        social_patterns = {
            "LinkedIn": re.compile(r'linkedin\.com', re.I),
            "Twitter": re.compile(r'twitter\.com|x\.com', re.I),
            "Facebook": re.compile(r'facebook\.com', re.I),
            "Instagram": re.compile(r'instagram\.com', re.I)
        }
        
        for name, pattern in social_patterns.items():
            social = soup.find('a', href=pattern)
            if social and social.get('href'):
                social_links.append(f"{name}: {social.get('href')}")
        
        # Add social links if found
        if social_links and len(social_links) <= 2:  # Limit to 2 social links
            contact_info.extend(social_links[:2])
                
        if contact_info:
            self.company_data.contact = " | ".join(contact_info)

    def _extract_values(self, soup: BeautifulSoup) -> None:
        """
        Extract company values or mission statements.
        
        Args:
            soup: BeautifulSoup object of the page
        """
        # Look for values/mission sections with expanded selectors
        values_section = soup.find(['div', 'section', 'article'], 
                                  {'class': re.compile('values|mission|vision|principles|purpose|culture', re.I)})
        
        if values_section:
            # Look for headings or list items that might contain values
            value_items = values_section.find_all(['h3', 'h4', 'h5', 'strong', 'b', 'li'])
            for item in value_items:
                value = item.text.strip()
                if value and value not in self.company_data.values and len(value) < 50:
                    self.company_data.values.append(value)
                    
        # If no values found yet, look for specific keywords in headings followed by paragraphs
        if not self.company_data.values:
            value_headings = soup.find_all(['h1', 'h2', 'h3', 'h4'], string=re.compile('values|mission|vision|principles|purpose', re.I))
            
            for heading in value_headings:
                # Find the next list or paragraph
                next_element = heading.find_next(['ul', 'ol', 'p'])
                if next_element:
                    if next_element.name in ['ul', 'ol']:
                        # Extract list items
                        items = next_element.find_all('li')
                        for item in items:
                            value = item.text.strip()
                            if value and value not in self.company_data.values and len(value) < 50:
                                self.company_data.values.append(value)
                    else:
                        # Extract paragraph text
                        value = next_element.text.strip()
                        if value and value not in self.company_data.values:
                            self.company_data.values.append(value)
        
        # If still no values found, extract from the about section
        if not self.company_data.values and self.company_data.about:
            # Look for value-related keywords in the about text
            value_keywords = ['integrity', 'innovation', 'excellence', 'quality', 'customer', 'service', 
                             'respect', 'responsibility', 'sustainability', 'diversity', 'inclusion', 
                             'teamwork', 'collaboration', 'trust', 'ethical', 'commitment', 'passion']
            
            about_text = self.company_data.about.lower()
            found_values = []
            
            for keyword in value_keywords:
                if keyword in about_text:
                    # Find the sentence containing this keyword
                    sentences = re.split(r'[.!?]\s+', self.company_data.about)
                    for sentence in sentences:
                        if keyword in sentence.lower() and len(sentence.strip()) < 150:
                            found_values.append(sentence.strip())
                            break
            
            # Add unique values
            for value in found_values:
                if value and value not in self.company_data.values:
                    self.company_data.values.append(value)
        
        # If still no values found, extract key phrases from company description
        if not self.company_data.values and self.company_data.description:
            # Extract key phrases that might represent values
            description = self.company_data.description
            phrases = re.split(r'[,;]\s+', description)
            
            for phrase in phrases:
                if any(keyword in phrase.lower() for keyword in value_keywords) and len(phrase) < 100:
                    if phrase and phrase not in self.company_data.values:
                        self.company_data.values.append(phrase.strip())
        
        # If we have values from about text but they're too long, extract key parts
        if self.company_data.values:
            refined_values = []
            for value in self.company_data.values:
                if len(value) > 100:  # If value is too long
                    # Try to extract key phrases
                    parts = re.split(r'[,;]\s+', value)
                    for part in parts:
                        if len(part) < 100 and part.strip():
                            refined_values.append(part.strip())
                else:
                    refined_values.append(value)
            
            if refined_values:
                self.company_data.values = refined_values[:5]  # Limit to 5 values

    def _infer_industry(self) -> None:
        """
        Attempt to infer the company's industry based on collected information.
        """
        # Create a text corpus from all the information we've collected
        corpus = " ".join([
            self.company_data.name,
            self.company_data.description,
            self.company_data.about,
            " ".join(self.company_data.products_services),
            " ".join(self.company_data.values)
        ]).lower()
        
        # Define expanded industry keywords with more comprehensive terms
        industry_keywords = {
            "Technology": ["software", "tech", "digital", "app", "application", "cloud", "data", "ai", "artificial intelligence", 
                         "platform", "saas", "automation", "internet", "web", "mobile", "computer", "it", "information technology",
                         "cyber", "security", "network", "programming", "developer", "code", "algorithm", "analytics"],
            "Healthcare": ["health", "medical", "healthcare", "patient", "hospital", "clinic", "doctor", "wellness", "pharma", 
                          "pharmaceutical", "biotech", "medicine", "therapy", "diagnostic", "treatment", "care", "nursing"],
            "Finance": ["finance", "financial", "banking", "investment", "insurance", "loan", "credit", "bank", "fintech", 
                       "payment", "transaction", "money", "capital", "fund", "asset", "wealth", "trading", "stock", "market"],
            "Education": ["education", "learning", "school", "university", "college", "student", "course", "training", 
                         "academic", "teaching", "classroom", "e-learning", "knowledge", "curriculum", "edtech"],
            "Manufacturing": ["manufacturing", "factory", "production", "industrial", "machinery", "equipment", "assembly", 
                             "fabrication", "processing", "engineering", "supply chain", "inventory", "quality control"],
            "Retail": ["retail", "shop", "store", "ecommerce", "product", "consumer", "customer", "shopping", "merchandise", 
                      "sales", "brand", "marketplace", "commerce", "purchase", "buyer", "seller"],
            "Real Estate": ["real estate", "property", "housing", "construction", "building", "apartment", "home", "commercial", 
                           "residential", "lease", "rent", "mortgage", "development", "architecture"],
            "Marketing": ["marketing", "advertising", "brand", "campaign", "media", "promotion", "content", "digital marketing", 
                        "seo", "ppc", "social media", "audience", "engagement", "lead generation"],
            "Consulting": ["consulting", "consultant", "advisory", "strategy", "solution", "business consulting", "management", 
                          "professional services", "expertise", "guidance", "recommendation", "analysis"],
            "Legal": ["legal", "law", "attorney", "lawyer", "compliance", "regulation", "litigation", "contract", "counsel", 
                     "firm", "practice", "legal services", "justice", "court"],
            "Professional Services": ["service", "professional", "business", "solution", "provider", "firm", "agency", "partner", 
                                     "client", "expertise", "specialist", "advisor"],
            "Entertainment & Media": ["media", "entertainment", "content", "film", "video", "music", "game", "streaming", 
                                      "publishing", "broadcast", "production", "creative", "studio"],
            "Telecommunications": ["telecom", "communication", "network", "mobile", "wireless", "broadband", "internet", 
                                  "phone", "cellular", "data", "connectivity"],
            "Energy & Utilities": ["energy", "power", "utility", "electricity", "gas", "oil", "renewable", "solar", "wind", 
                                  "sustainable", "grid", "resource"],
            "Transportation & Logistics": ["transport", "logistics", "shipping", "delivery", "freight", "supply chain", 
                                           "warehouse", "distribution", "fleet", "cargo", "fulfillment"]
        }
        
        # Count keyword matches for each industry with weighted scoring
        industry_scores = {industry: 0 for industry in industry_keywords}
        
        for industry, keywords in industry_keywords.items():
            for keyword in keywords:
                # Count occurrences of the keyword
                occurrences = corpus.count(keyword)
                if occurrences > 0:
                    # Add score based on occurrences (with diminishing returns)
                    industry_scores[industry] += min(occurrences, 3)
                    
                    # Give extra weight to keywords in the company name or description
                    if keyword in self.company_data.name.lower() or keyword in self.company_data.description.lower():
                        industry_scores[industry] += 2
        
        # We don't have soup in this method, so we can't check meta tags here
        
        # Select the industry with the highest score
        if industry_scores:
            max_industry = max(industry_scores.items(), key=lambda x: x[1])
            if max_industry[1] > 0:
                self.company_data.industry = max_industry[0]
                
    def _post_process_data(self) -> None:
        """
        Post-process the extracted data to clean and validate it.
        """
        # Filter out navigation items from products/services
        common_nav_items = ['home', 'about', 'about us', 'contact', 'contact us', 'careers', 
                           'login', 'sign in', 'register', 'blog', 'news', 'events', 
                           'privacy policy', 'terms', 'sitemap', 'search', 'locations']
        
        # Filter out common navigation items that aren't actual services
        if self.company_data.products_services:
            filtered_services = []
            for service in self.company_data.products_services:
                service_lower = service.lower()
                # Skip if it's a common navigation item
                if any(nav_item == service_lower for nav_item in common_nav_items):
                    continue
                # Skip if it's too short (likely not a real service)
                if len(service) < 4:
                    continue
                # Skip if it contains common navigation terms
                if any(term in service_lower for term in ['login', 'sign', 'contact', 'about']):
                    continue
                filtered_services.append(service)
            
            # If we filtered out everything, keep the original - better than nothing
            if filtered_services:
                self.company_data.products_services = filtered_services
                
        # Filter out dates from values
        if self.company_data.values:
            date_pattern = re.compile(r'^\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\s*$', re.I)
            self.company_data.values = [v for v in self.company_data.values if not date_pattern.match(v)]
            
        # Validate phone numbers in contact info
        if self.company_data.contact:
            # If contact info contains a phone number with fewer than 7 digits, remove it
            if "Phone:" in self.company_data.contact:
                parts = self.company_data.contact.split(" | ")
                filtered_parts = []
                for part in parts:
                    if part.startswith("Phone:"):
                        # Extract just the digits
                        digits = re.sub(r'\D', '', part)
                        # Only keep if it has at least 7 digits (a reasonable phone number)
                        if len(digits) >= 7:
                            filtered_parts.append(part)
                    else:
                        filtered_parts.append(part)
                
                if filtered_parts:
                    self.company_data.contact = " | ".join(filtered_parts)
                else:
                    self.company_data.contact = ""
        
        # If contact is still empty, add a default contact based on the domain
        if not self.company_data.contact:
            domain = urlparse(self.base_url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Add generic contact info based on domain
            contact_parts = []
            
            # Add social media
            if 'linkedin' not in self.company_data.contact.lower():
                contact_parts.append(f"LinkedIn: https://www.linkedin.com/company/{domain.split('.')[0]}")
            
            # Add website
            contact_parts.append(f"Website: {self.base_url}")
            
            if contact_parts:
                if self.company_data.contact:
                    self.company_data.contact += " | " + " | ".join(contact_parts)
                else:
                    self.company_data.contact = " | ".join(contact_parts)
        
        # If products/services is empty, extract from industry
        if not self.company_data.products_services and self.company_data.industry:
            industry = self.company_data.industry
            
            # Add generic services based on industry
            industry_services = {
                "Technology": ["Software Development", "Cloud Solutions", "Digital Transformation"],
                "Healthcare": ["Patient Care", "Medical Services", "Healthcare Solutions"],
                "Finance": ["Financial Services", "Investment Management", "Banking Solutions"],
                "Professional Services": ["Consulting", "Advisory Services", "Business Solutions"],
                "Consulting": ["Strategy Consulting", "Management Consulting", "Business Advisory"]
            }
            
            if industry in industry_services:
                self.company_data.products_services = industry_services[industry]
            else:
                # Generic fallback
                self.company_data.products_services = [f"{industry} Services", "Consulting", "Professional Solutions"]
        
        # If values is still empty, add default values based on industry
        if not self.company_data.values and self.company_data.industry:
            industry = self.company_data.industry
            
            # Add generic values based on industry
            industry_values = {
                "Technology": ["Innovation", "Excellence", "Customer-Centric"],
                "Healthcare": ["Patient-Focused", "Quality Care", "Compassion"],
                "Finance": ["Integrity", "Trust", "Excellence"],
                "Professional Services": ["Client Success", "Excellence", "Integrity"],
                "Consulting": ["Client Value", "Expertise", "Collaboration"]
            }
            
            if industry in industry_values:
                self.company_data.values = industry_values[industry]
            else:
                # Generic fallback values
                self.company_data.values = ["Excellence", "Integrity", "Client Focus"]
