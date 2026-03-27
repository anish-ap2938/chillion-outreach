"""
Lead Generation CLI

Command-line interface for running the lead generation pipeline.

Example usage:
    # Run full pipeline
    python -m app.lead_generation.cli run --companies-csv companies.csv
    
    # Run only social monitoring
    python -m app.lead_generation.cli social --platforms twitter,reddit
    
    # Run company discovery
    python -m app.lead_generation.cli companies --input companies.csv --discover-websites
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import get_config, load_config, LeadGenerationConfig
from .models import SocialLead, Company, FinanceContact
from .social.twitter import TwitterScraper
from .social.reddit import RedditScraper
from .social.forums import ForumScraper
from .company.discovery import CompanyDiscoveryService
from .contacts.discovery import ContactDiscoveryService
from .contacts.email import EmailDiscoveryService
from .storage.database import LeadDatabase
from .storage.csv_export import CSVExporter


def setup_logging(level: str = "INFO"):
    """Configure logging for CLI"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def run_social_monitoring(
    platforms: list,
    max_results: int = 100,
    db: Optional[LeadDatabase] = None,
    exporter: Optional[CSVExporter] = None
) -> list:
    """
    Run social media monitoring.
    
    Args:
        platforms: List of platforms to monitor ('twitter', 'reddit', 'forums')
        max_results: Max results per platform
        db: Optional database for persistence
        exporter: Optional CSV exporter
        
    Returns:
        List of discovered SocialLead objects
    """
    logger = logging.getLogger("social_monitoring")
    all_leads = []
    
    if 'twitter' in platforms:
        logger.info("=== Starting Twitter monitoring ===")
        scraper = TwitterScraper()
        leads = scraper.search_all_queries(max_results_per_query=max_results // 5)
        # Score all leads
        leads = [scraper.score_lead(lead) for lead in leads]
        all_leads.extend(leads)
        logger.info(f"Found {len(leads)} Twitter leads")
    
    if 'reddit' in platforms:
        logger.info("=== Starting Reddit monitoring ===")
        scraper = RedditScraper()
        # Search all configured subreddits with key queries
        for query in ["accounts receivable", "order to cash", "collections software"]:
            leads = scraper.search_all_subreddits(query, max_per_sub=max_results // 10)
            all_leads.extend(leads)
        logger.info(f"Found {len([l for l in all_leads if l.platform.value == 'reddit'])} Reddit leads")
    
    if 'forums' in platforms:
        logger.info("=== Starting forum monitoring ===")
        scraper = ForumScraper()
        leads = scraper.search("accounts receivable automation software", max_results)
        leads = [scraper.score_lead(lead) for lead in leads]
        all_leads.extend(leads)
        logger.info(f"Found {len([l for l in all_leads if l.platform.value in ('forum', 'quora')])} forum leads")
    
    # Filter high intent leads
    high_intent = [l for l in all_leads if l.intent_score >= 0.5]
    logger.info(f"Total leads: {len(all_leads)}, High intent: {len(high_intent)}")
    
    # Persist to database
    if db:
        result = db.insert_social_leads_batch(all_leads)
        logger.info(f"Database: {result['inserted']} inserted, {result['duplicates']} duplicates")
    
    # Export to CSV
    if exporter:
        exporter.export_social_leads(all_leads, "social_leads.csv")
        exporter.export_social_leads(high_intent, "social_leads_high_intent.csv")
    
    return all_leads


def run_company_discovery(
    input_csv: str,
    discover_websites: bool = True,
    enrich: bool = True,
    filter_targets: bool = False,
    db: Optional[LeadDatabase] = None,
    exporter: Optional[CSVExporter] = None
) -> list:
    """
    Run company discovery pipeline.
    
    Args:
        input_csv: Path to input CSV with company names
        discover_websites: Whether to discover websites
        enrich: Whether to enrich company data
        filter_targets: Whether to filter to target profile only
        db: Optional database
        exporter: Optional CSV exporter
        
    Returns:
        List of discovered Company objects
    """
    logger = logging.getLogger("company_discovery")
    logger.info("=== Starting company discovery ===")
    
    service = CompanyDiscoveryService()
    
    # Load companies from CSV
    companies = service.load_from_csv(input_csv)
    logger.info(f"Loaded {len(companies)} companies from {input_csv}")
    
    # Process companies
    companies = service.process_companies(
        companies,
        discover_websites=discover_websites,
        enrich=enrich,
        filter_targets=filter_targets
    )
    
    target_count = len([c for c in companies if c.is_target_profile])
    logger.info(f"Processed {len(companies)} companies, {target_count} match target profile")
    
    # Persist to database
    if db:
        for company in companies:
            db.insert_company(company)
    
    # Export to CSV
    if exporter:
        exporter.export_companies(companies, "companies.csv")
        target_companies = [c for c in companies if c.is_target_profile]
        if target_companies:
            exporter.export_companies(target_companies, "companies_targets.csv")
    
    return companies


def run_contact_discovery(
    companies: list,
    discover_emails: bool = True,
    db: Optional[LeadDatabase] = None,
    exporter: Optional[CSVExporter] = None
) -> list:
    """
    Run contact discovery for companies.
    
    Args:
        companies: List of Company objects
        discover_emails: Whether to discover emails
        db: Optional database
        exporter: Optional CSV exporter
        
    Returns:
        List of discovered FinanceContact objects
    """
    logger = logging.getLogger("contact_discovery")
    logger.info("=== Starting contact discovery ===")
    
    contact_service = ContactDiscoveryService()
    email_service = EmailDiscoveryService()
    
    all_contacts = []
    
    for company in companies:
        logger.info(f"Discovering contacts for: {company.name}")
        
        # Find contacts on company website
        contacts = contact_service.discover_contacts(company)
        
        # Discover emails
        if discover_emails:
            for contact in contacts:
                email_service.discover_email(contact)
        
        all_contacts.extend(contacts)
        logger.info(f"Found {len(contacts)} contacts for {company.name}")
    
    with_email = len([c for c in all_contacts if c.email])
    logger.info(f"Total contacts: {len(all_contacts)}, with email: {with_email}")
    
    # Persist to database
    if db:
        for contact in all_contacts:
            db.insert_contact(contact)
    
    # Export to CSV
    if exporter:
        exporter.export_contacts(all_contacts, "contacts.csv")
    
    return all_contacts


def run_full_pipeline(
    companies_csv: Optional[str] = None,
    platforms: list = ['twitter', 'reddit'],
    config_path: Optional[str] = None
):
    """
    Run the complete lead generation pipeline.
    
    1. Social monitoring
    2. Company discovery (if CSV provided)
    3. Contact discovery
    4. Email generation
    5. Export results
    """
    logger = logging.getLogger("pipeline")
    
    # Load config
    if config_path:
        config = load_config(config_path)
    else:
        config = get_config()
    
    # Initialize services
    db = LeadDatabase()
    db.initialize()
    
    exporter = CSVExporter()
    
    logger.info("=" * 60)
    logger.info("CHILLION LEAD GENERATION PIPELINE")
    logger.info("=" * 60)
    
    # Step 1: Social monitoring
    logger.info("\n[STEP 1] Social Media Monitoring")
    social_leads = run_social_monitoring(
        platforms=platforms,
        max_results=100,
        db=db,
        exporter=exporter
    )
    
    # Step 2: Company discovery
    companies = []
    if companies_csv:
        logger.info(f"\n[STEP 2] Company Discovery from {companies_csv}")
        companies = run_company_discovery(
            input_csv=companies_csv,
            discover_websites=True,
            enrich=True,
            filter_targets=False,
            db=db,
            exporter=exporter
        )
    else:
        logger.info("\n[STEP 2] Company Discovery (skipped - no input CSV)")
    
    # Step 3: Contact discovery
    contacts = []
    if companies:
        logger.info("\n[STEP 3] Contact Discovery")
        contacts = run_contact_discovery(
            companies=companies,
            discover_emails=True,
            db=db,
            exporter=exporter
        )
    else:
        logger.info("\n[STEP 3] Contact Discovery (skipped - no companies)")
    
    # Print summary
    stats = db.get_stats()
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETE - SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Social Leads:      {stats['total_social_leads']}")
    logger.info(f"  High Intent:     {stats['high_intent_leads']}")
    logger.info(f"Companies:         {stats['total_companies']}")
    logger.info(f"  Target Profile:  {stats['target_companies']}")
    logger.info(f"Contacts:          {stats['total_contacts']}")
    logger.info(f"  With Email:      {stats['contacts_with_email']}")
    logger.info(f"\nData saved to: {db.db_path}")
    logger.info(f"CSV exports in: {exporter.output_dir}")
    
    return {
        'social_leads': len(social_leads),
        'companies': len(companies),
        'contacts': len(contacts),
        'stats': stats
    }


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Chillion Lead Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python -m app.lead_generation.cli run --companies-csv companies.csv
  
  # Run social monitoring only
  python -m app.lead_generation.cli social --platforms twitter,reddit
  
  # Run company discovery only
  python -m app.lead_generation.cli companies --input companies.csv
  
  # Show database stats
  python -m app.lead_generation.cli stats
        """
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    parser.add_argument(
        '--config',
        help='Path to config JSON file'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run full pipeline')
    run_parser.add_argument('--companies-csv', help='Input CSV with company names')
    run_parser.add_argument('--platforms', default='twitter,reddit', help='Platforms to monitor')
    
    # Social command
    social_parser = subparsers.add_parser('social', help='Run social monitoring only')
    social_parser.add_argument('--platforms', default='twitter,reddit,forums', help='Platforms')
    social_parser.add_argument('--max-results', type=int, default=100, help='Max results per platform')
    
    # Companies command
    companies_parser = subparsers.add_parser('companies', help='Run company discovery')
    companies_parser.add_argument('--input', required=True, help='Input CSV file')
    companies_parser.add_argument('--discover-websites', action='store_true', help='Discover websites')
    companies_parser.add_argument('--enrich', action='store_true', help='Enrich data')
    companies_parser.add_argument('--filter-targets', action='store_true', help='Filter to targets only')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger("cli")
    
    if args.command == 'run':
        platforms = [p.strip() for p in args.platforms.split(',')]
        run_full_pipeline(
            companies_csv=args.companies_csv,
            platforms=platforms,
            config_path=args.config
        )
    
    elif args.command == 'social':
        platforms = [p.strip() for p in args.platforms.split(',')]
        db = LeadDatabase()
        db.initialize()
        exporter = CSVExporter()
        run_social_monitoring(
            platforms=platforms,
            max_results=args.max_results,
            db=db,
            exporter=exporter
        )
    
    elif args.command == 'companies':
        db = LeadDatabase()
        db.initialize()
        exporter = CSVExporter()
        run_company_discovery(
            input_csv=args.input,
            discover_websites=args.discover_websites,
            enrich=args.enrich,
            filter_targets=args.filter_targets,
            db=db,
            exporter=exporter
        )
    
    elif args.command == 'stats':
        db = LeadDatabase()
        stats = db.get_stats()
        print("\nDatabase Statistics:")
        print("-" * 40)
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

