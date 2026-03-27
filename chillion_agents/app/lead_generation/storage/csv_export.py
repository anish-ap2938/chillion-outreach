"""
CSV Export Module

Exports leads, companies, and contacts to CSV files.
"""

from typing import List, Optional
from datetime import datetime
import logging
import csv
from pathlib import Path

from ..models import SocialLead, Company, FinanceContact
from ..config import get_config

logger = logging.getLogger(__name__)


class CSVExporter:
    """
    Exports lead generation data to CSV files.
    
    Example usage:
        exporter = CSVExporter()
        
        # Export social leads
        exporter.export_social_leads(leads, "social_leads.csv")
        
        # Export companies
        exporter.export_companies(companies, "companies.csv")
        
        # Export contacts
        exporter.export_contacts(contacts, "contacts.csv")
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the CSV exporter.
        
        Args:
            output_dir: Directory for CSV output files
        """
        self.output_dir = Path(output_dir or get_config().storage.csv_export_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def export_social_leads(
        self,
        leads: List[SocialLead],
        filename: str = "social_leads.csv"
    ) -> str:
        """
        Export social leads to CSV.
        
        Args:
            leads: List of SocialLead objects
            filename: Output filename
            
        Returns:
            Path to exported file
        """
        filepath = self.output_dir / filename
        
        fieldnames = [
            'id', 'platform', 'url', 'author_username', 'author_display_name',
            'author_company', 'author_title', 'author_followers', 'title',
            'text', 'intent_score', 'intent_level', 'intent_keywords',
            'product_keywords', 'status', 'created_at', 'discovered_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for lead in leads:
                writer.writerow({
                    'id': lead.id,
                    'platform': lead.platform.value if hasattr(lead.platform, 'value') else lead.platform,
                    'url': lead.url,
                    'author_username': lead.author_username,
                    'author_display_name': lead.author_display_name,
                    'author_company': lead.author_company,
                    'author_title': lead.author_title,
                    'author_followers': lead.author_followers,
                    'title': lead.title,
                    'text': lead.text[:500] if lead.text else '',  # Truncate long text
                    'intent_score': lead.intent_score,
                    'intent_level': lead.intent_level.value if hasattr(lead.intent_level, 'value') else lead.intent_level,
                    'intent_keywords': ', '.join(lead.intent_keywords_matched or []),
                    'product_keywords': ', '.join(lead.product_keywords_matched or []),
                    'status': lead.status.value if hasattr(lead.status, 'value') else lead.status,
                    'created_at': lead.created_at.isoformat() if lead.created_at else '',
                    'discovered_at': lead.discovered_at.isoformat() if lead.discovered_at else '',
                })
        
        self.logger.info(f"Exported {len(leads)} social leads to {filepath}")
        return str(filepath)
    
    def export_companies(
        self,
        companies: List[Company],
        filename: str = "companies.csv"
    ) -> str:
        """
        Export companies to CSV.
        
        Args:
            companies: List of Company objects
            filename: Output filename
            
        Returns:
            Path to exported file
        """
        filepath = self.output_dir / filename
        
        fieldnames = [
            'id', 'name', 'domain', 'website', 'industry', 'employee_count',
            'employee_range', 'revenue_usd', 'revenue_range', 'headquarters_city',
            'headquarters_state', 'headquarters_country', 'linkedin_url',
            'is_target_profile', 'target_score', 'source', 'discovered_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for company in companies:
                writer.writerow({
                    'id': company.id,
                    'name': company.name,
                    'domain': company.domain,
                    'website': company.website,
                    'industry': company.industry,
                    'employee_count': company.employee_count,
                    'employee_range': company.employee_range,
                    'revenue_usd': company.revenue_usd,
                    'revenue_range': company.revenue_range,
                    'headquarters_city': company.headquarters_city,
                    'headquarters_state': company.headquarters_state,
                    'headquarters_country': company.headquarters_country,
                    'linkedin_url': company.linkedin_url,
                    'is_target_profile': company.is_target_profile,
                    'target_score': company.target_score,
                    'source': company.source,
                    'discovered_at': company.discovered_at.isoformat() if company.discovered_at else '',
                })
        
        self.logger.info(f"Exported {len(companies)} companies to {filepath}")
        return str(filepath)
    
    def export_contacts(
        self,
        contacts: List[FinanceContact],
        filename: str = "contacts.csv"
    ) -> str:
        """
        Export contacts to CSV.
        
        Args:
            contacts: List of FinanceContact objects
            filename: Output filename
            
        Returns:
            Path to exported file
        """
        filepath = self.output_dir / filename
        
        fieldnames = [
            'id', 'company_name', 'company_domain', 'full_name', 'first_name',
            'last_name', 'title', 'email', 'email_status', 'linkedin_url',
            'seniority_level', 'department', 'is_decision_maker', 'source',
            'source_url', 'discovered_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for contact in contacts:
                writer.writerow({
                    'id': contact.id,
                    'company_name': contact.company_name,
                    'company_domain': contact.company_domain,
                    'full_name': contact.full_name,
                    'first_name': contact.first_name,
                    'last_name': contact.last_name,
                    'title': contact.title,
                    'email': contact.email,
                    'email_status': contact.email_status,
                    'linkedin_url': contact.linkedin_url,
                    'seniority_level': contact.seniority_level,
                    'department': contact.department,
                    'is_decision_maker': contact.is_decision_maker,
                    'source': contact.source.value if hasattr(contact.source, 'value') else contact.source,
                    'source_url': contact.source_url,
                    'discovered_at': contact.discovered_at.isoformat() if contact.discovered_at else '',
                })
        
        self.logger.info(f"Exported {len(contacts)} contacts to {filepath}")
        return str(filepath)
    
    def export_all(
        self,
        leads: List[SocialLead],
        companies: List[Company],
        contacts: List[FinanceContact],
        prefix: str = ""
    ) -> dict:
        """
        Export all data types with optional prefix.
        
        Args:
            leads: Social leads to export
            companies: Companies to export
            contacts: Contacts to export
            prefix: Optional filename prefix
            
        Returns:
            Dict with paths to all exported files
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{prefix}_" if prefix else ""
        
        return {
            'social_leads': self.export_social_leads(
                leads, f"{prefix}social_leads_{timestamp}.csv"
            ),
            'companies': self.export_companies(
                companies, f"{prefix}companies_{timestamp}.csv"
            ),
            'contacts': self.export_contacts(
                contacts, f"{prefix}contacts_{timestamp}.csv"
            ),
        }

