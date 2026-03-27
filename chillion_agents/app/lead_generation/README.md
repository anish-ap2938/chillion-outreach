# Chillion Lead Generation System

A modular Python system for automated lead generation targeting finance decision makers interested in AR/O2C automation.

## Features

### Social & Forum Monitoring
- **Twitter/X**: Search public tweets for buying intent signals
- **Reddit**: Monitor finance-related subreddits for discussions
- **Forums/Quora**: Search Q&A sites for software recommendations
- **Intent Scoring**: Automatic classification of buying intent (high/medium/low)

### Company Discovery
- Load companies from CSV
- Discover company websites via search
- Enrich company data (industry, size, revenue)
- Match against ideal customer profile (ICP)

### Contact Discovery
- Parse leadership/team pages for finance executives
- Target titles: CFO, VP Finance, Director Finance, Controller, AR Managers
- Extract name, title, and source URL

### Email Discovery
- Generate email candidates using common corporate patterns
- Format validation (can integrate with external validation APIs)
- Pattern confidence scoring

## Project Structure

```
lead_generation/
├── __init__.py           # Package exports
├── config.py             # Configuration (keywords, targets, rate limits)
├── models.py             # Pydantic data models
├── cli.py                # Command-line interface
│
├── social/               # Social media scrapers
│   ├── base.py           # Base scraper class
│   ├── twitter.py        # Twitter/X scraper
│   ├── reddit.py         # Reddit scraper
│   └── forums.py         # Generic forum scraper
│
├── company/              # Company discovery
│   └── discovery.py      # Website discovery, enrichment
│
├── contacts/             # Contact discovery
│   ├── discovery.py      # Website parsing for contacts
│   └── email.py          # Email pattern generation
│
└── storage/              # Data persistence
    ├── database.py       # SQLite storage
    └── csv_export.py     # CSV export utilities
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: For enhanced social scraping
pip install snscrape praw
```

## Quick Start

### Command Line

```bash
# Run full pipeline
python -m app.lead_generation.cli run --companies-csv companies.csv

# Run social monitoring only
python -m app.lead_generation.cli social --platforms twitter,reddit

# Run company discovery
python -m app.lead_generation.cli companies --input companies.csv --discover-websites

# View statistics
python -m app.lead_generation.cli stats
```

### Python API

```python
from app.lead_generation.social.twitter import TwitterScraper
from app.lead_generation.social.reddit import RedditScraper
from app.lead_generation.company.discovery import CompanyDiscoveryService
from app.lead_generation.contacts.discovery import ContactDiscoveryService
from app.lead_generation.storage.database import LeadDatabase

# Initialize database
db = LeadDatabase()
db.initialize()

# Social monitoring
twitter = TwitterScraper()
leads = twitter.search_all_queries()
db.insert_social_leads_batch(leads)

# Company discovery
company_service = CompanyDiscoveryService()
companies = company_service.load_from_csv("companies.csv")
companies = company_service.process_companies(companies)

# Contact discovery
contact_service = ContactDiscoveryService()
for company in companies:
    contacts = contact_service.discover_contacts(company)
    for contact in contacts:
        db.insert_contact(contact)
```

### REST API

The system integrates with FastAPI at `/api/v1/lead-gen/`:

```bash
# Search social media
POST /api/v1/lead-gen/social/search
{
  "platforms": ["twitter", "reddit"],
  "keywords": ["accounts receivable automation"],
  "max_results": 50
}

# Discover companies
POST /api/v1/lead-gen/companies/discover
{
  "company_names": ["Acme Corp", "TechCo Inc"],
  "discover_websites": true,
  "enrich": true
}

# Discover contacts
POST /api/v1/lead-gen/contacts/discover
{
  "company_name": "Acme Corp",
  "company_domain": "acme.com"
}

# Generate email candidates
POST /api/v1/lead-gen/email/generate
{
  "first_name": "John",
  "last_name": "Smith",
  "company_domain": "acme.com"
}

# Get statistics
GET /api/v1/lead-gen/stats
```

## Configuration

Edit `config.py` or create a JSON config file:

```json
{
  "social": {
    "intent_keywords": ["looking for", "recommend", "need"],
    "product_keywords": ["accounts receivable", "order to cash", "AR automation"],
    "reddit_subreddits": ["accounting", "cfo", "finance"]
  },
  "company": {
    "target_industries": ["Retail", "E-commerce", "Manufacturing"],
    "min_revenue_usd": 50000000,
    "target_titles": ["CFO", "VP Finance", "Controller"]
  }
}
```

## Extending the System

### Adding a New Search Provider

```python
from app.lead_generation.company.discovery import SearchProvider

class GoogleSearchProvider(SearchProvider):
    def __init__(self, api_key: str, cx: str):
        self.api_key = api_key
        self.cx = cx
    
    def search(self, query: str, num_results: int = 10) -> List[Dict]:
        # Implement Google Custom Search API call
        pass
```

### Adding Email Validation

```python
from app.lead_generation.contacts.email import EmailValidator

class HunterValidator(EmailValidator):
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def validate_email(self, email: str) -> Dict:
        # Implement Hunter.io API call
        pass
```

### Adding Enrichment Provider

```python
from app.lead_generation.company.discovery import CompanyEnrichmentProvider

class ClearbitProvider(CompanyEnrichmentProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def enrich_company(self, name: str, domain: str = None) -> Dict:
        # Implement Clearbit API call
        pass
```

## Legal & Ethical Notes

- Uses only publicly available information
- Respects robots.txt and rate limits
- Does not scrape behind login walls
- Email collection uses only public sources or pattern generation
- Designed for GDPR compliance (data collection separate from outreach)

## Output

Data is stored in:
- **SQLite**: `./data/leads.db`
- **CSV**: `./data/exports/`

Tables:
- `social_leads`: Social media leads with intent scores
- `companies`: Company information
- `contacts`: Finance contacts with emails

