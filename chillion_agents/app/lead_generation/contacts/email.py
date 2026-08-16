"""
Email Discovery Module

Generates and validates corporate email addresses.
Provides interfaces for email validation services.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import re
from abc import ABC, abstractmethod

from ..models import EmailCandidate, EmailDiscoveryResult, FinanceContact

logger = logging.getLogger(__name__)


# =============================================================================
# Email Validation Interface
# =============================================================================

class EmailValidator(ABC):
    """
    Abstract interface for email validation services.
    
    Implement this interface to integrate with:
    - Hunter.io
    - NeverBounce
    - ZeroBounce
    - EmailListVerify
    - Mailgun validation
    """
    
    @abstractmethod
    def validate_email(self, email: str) -> Dict[str, Any]:
        """
        Validate an email address.
        
        Args:
            email: Email address to validate
            
        Returns:
            Dict with keys:
            - valid: bool - Whether email is valid
            - status: str - Status code (valid, invalid, unknown, disposable, etc.)
            - confidence: float - Confidence score 0-1
            - mx_found: bool - Whether MX records exist
            - smtp_valid: bool - Whether SMTP check passed
            - reason: str - Explanation of result
        """
        pass
    
    @abstractmethod
    def validate_batch(self, emails: List[str]) -> List[Dict[str, Any]]:
        """
        Validate multiple email addresses.
        
        Args:
            emails: List of email addresses
            
        Returns:
            List of validation results
        """
        pass


class LocalEmailValidator(EmailValidator):
    """
    Local email validator that performs basic format validation.
    
    This is a development/testing implementation that:
    - Validates email format using regex
    - Checks for common disposable domains
    - Returns plausible results without external API calls
    
    For production, replace with a real validation service.
    """
    
    # Common corporate email domains (known valid)
    VALID_CORPORATE_DOMAINS = {
        'google.com', 'microsoft.com', 'amazon.com', 'apple.com',
        'facebook.com', 'meta.com', 'salesforce.com', 'oracle.com',
    }
    
    # Common disposable email domains
    DISPOSABLE_DOMAINS = {
        'guerrillamail.com', 'mailinator.com', 'tempmail.com',
        '10minutemail.com', 'throwaway.email', 'maildrop.cc',
    }
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # RFC 5322 compliant email regex (simplified)
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
    
    def validate_email(self, email: str) -> Dict[str, Any]:
        """
        Validate email format locally.
        
        Args:
            email: Email address to validate
            
        Returns:
            Validation result dict
        """
        self.logger.info(f"[LOCAL VALIDATION] Validating: {email}")
        
        result = {
            "email": email,
            "valid": False,
            "status": "unknown",
            "confidence": 0.0,
            "mx_found": None,  # Would check in production
            "smtp_valid": None,  # Would check in production
            "reason": "",
            "validated_at": datetime.utcnow().isoformat(),
        }
        
        # Check format
        if not self.email_pattern.match(email):
            result["status"] = "invalid_format"
            result["reason"] = "Email format is invalid"
            return result
        
        # Extract domain
        domain = email.split('@')[1].lower()
        
        # Check for disposable domains
        if domain in self.DISPOSABLE_DOMAINS:
            result["status"] = "disposable"
            result["reason"] = "Disposable email domain detected"
            result["confidence"] = 0.1
            return result
        
        # Check for known valid corporate domains
        if domain in self.VALID_CORPORATE_DOMAINS:
            result["valid"] = True
            result["status"] = "valid"
            result["confidence"] = 0.9
            result["reason"] = "Known corporate domain"
            return result
        
        # For other domains, mark as plausible but unverified
        result["valid"] = True  # Format is valid
        result["status"] = "unverified"
        result["confidence"] = 0.5
        result["reason"] = "Format valid, external verification recommended"
        
        return result
    
    def validate_batch(self, emails: List[str]) -> List[Dict[str, Any]]:
        """Validate multiple emails"""
        return [self.validate_email(email) for email in emails]


# =============================================================================
# Email Pattern Generator
# =============================================================================

class EmailPatternGenerator:
    """
    Generates corporate email address candidates.
    
    Uses common corporate email patterns to generate likely email addresses
    based on a person's name and company domain.
    
    Common patterns:
    - first.last@company.com
    - firstlast@company.com
    - first@company.com
    - flast@company.com (first initial + last)
    - first_last@company.com
    - lastf@company.com (last + first initial)
    """
    
    # Email patterns ordered by likelihood (most common first)
    PATTERNS = [
        {
            "name": "first.last",
            "template": "{first}.{last}@{domain}",
            "priority": 1,
            "description": "first.last@domain - Most common",
        },
        {
            "name": "firstlast",
            "template": "{first}{last}@{domain}",
            "priority": 2,
            "description": "firstlast@domain",
        },
        {
            "name": "first_last",
            "template": "{first}_{last}@{domain}",
            "priority": 3,
            "description": "first_last@domain",
        },
        {
            "name": "flast",
            "template": "{f}{last}@{domain}",
            "priority": 4,
            "description": "flast@domain (initial + last)",
        },
        {
            "name": "first",
            "template": "{first}@{domain}",
            "priority": 5,
            "description": "first@domain",
        },
        {
            "name": "last.first",
            "template": "{last}.{first}@{domain}",
            "priority": 6,
            "description": "last.first@domain",
        },
        {
            "name": "lastf",
            "template": "{last}{f}@{domain}",
            "priority": 7,
            "description": "lastf@domain (last + initial)",
        },
        {
            "name": "first.l",
            "template": "{first}.{l}@{domain}",
            "priority": 8,
            "description": "first.l@domain (first + last initial)",
        },
    ]
    
    def __init__(self, validator: Optional[EmailValidator] = None):
        """
        Initialize the email pattern generator.
        
        Args:
            validator: Optional email validator for testing candidates
        """
        self.validator = validator or LocalEmailValidator()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def generate_candidates(
        self,
        first_name: str,
        last_name: str,
        domain: str,
        num_patterns: int = 5
    ) -> List[EmailCandidate]:
        """
        Generate email address candidates for a person.
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            domain: Company domain (e.g., "company.com")
            num_patterns: Number of patterns to use
            
        Returns:
            List of EmailCandidate objects
        """
        candidates = []
        
        # Normalize inputs
        first = first_name.lower().strip()
        last = last_name.lower().strip()
        f = first[0] if first else ''
        l = last[0] if last else ''
        domain = domain.lower().strip()
        
        if not first or not last or not domain:
            self.logger.warning(f"Incomplete data: {first_name} {last_name} @ {domain}")
            return candidates
        
        # Generate candidates using patterns
        for pattern in self.PATTERNS[:num_patterns]:
            try:
                email = pattern["template"].format(
                    first=first,
                    last=last,
                    f=f,
                    l=l,
                    domain=domain
                )
                
                # Calculate confidence based on pattern priority
                base_confidence = 1.0 - (pattern["priority"] - 1) * 0.1
                
                candidate = EmailCandidate(
                    email=email,
                    pattern_used=pattern["name"],
                    confidence=max(0.3, base_confidence),
                    is_validated=False,
                )
                candidates.append(candidate)
                
            except Exception as e:
                self.logger.debug(f"Error generating pattern {pattern['name']}: {e}")
        
        return candidates
    
    def generate_and_validate(
        self,
        first_name: str,
        last_name: str,
        domain: str,
        num_patterns: int = 5
    ) -> EmailDiscoveryResult:
        """
        Generate and validate email candidates.
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            domain: Company domain
            num_patterns: Number of patterns to try
            
        Returns:
            EmailDiscoveryResult with candidates and best guess
        """
        candidates = self.generate_candidates(first_name, last_name, domain, num_patterns)
        
        # Validate each candidate
        for candidate in candidates:
            result = self.validator.validate_email(candidate.email)
            candidate.is_validated = True
            candidate.validation_result = result.get('status', 'unknown')
            
            # Adjust confidence based on validation
            if result.get('valid'):
                candidate.confidence = min(1.0, candidate.confidence + 0.2)
            else:
                candidate.confidence = max(0.0, candidate.confidence - 0.3)
        
        # Sort by confidence
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        # Determine best guess
        best_guess = None
        if candidates:
            # Take highest confidence that passed validation
            for c in candidates:
                if c.validation_result in ('valid', 'unverified'):
                    best_guess = c.email
                    break
            
            # Fall back to first candidate if none validated
            if not best_guess:
                best_guess = candidates[0].email
        
        return EmailDiscoveryResult(
            contact_name=f"{first_name} {last_name}",
            company_domain=domain,
            candidates=candidates,
            best_guess=best_guess,
        )


# =============================================================================
# Email Discovery Service
# =============================================================================

class EmailDiscoveryService:
    """
    High-level service for email discovery.
    
    Combines pattern generation and validation with
    website scraping for publicly available emails.
    """
    
    def __init__(
        self,
        validator: Optional[EmailValidator] = None,
        pattern_generator: Optional[EmailPatternGenerator] = None
    ):
        """
        Initialize the email discovery service.
        
        Args:
            validator: Email validator instance
            pattern_generator: Pattern generator instance
        """
        self.validator = validator or LocalEmailValidator()
        self.generator = pattern_generator or EmailPatternGenerator(self.validator)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def discover_email(self, contact: FinanceContact) -> FinanceContact:
        """
        Discover email for a contact.
        
        Attempts pattern-based discovery if no email exists.
        
        Args:
            contact: FinanceContact to enrich
            
        Returns:
            Contact with email field populated
        """
        # Never overwrite a provider-verified or likely professional email
        # with local regex results or a pattern guess.
        existing_status = (contact.email_status or "").lower()
        if contact.email and (
            existing_status in ("verified", "likely")
            or (contact.provider or "") == "prospeo"
        ):
            if not getattr(contact, "email_source", None):
                contact.email_source = "prospeo"
            return contact

        # If email already exists, run local format checks only.
        # Local "valid" is syntax/domain-list — not mailbox verification.
        if contact.email:
            result = self.validator.validate_email(contact.email)
            status = result.get('status', 'unverified')
            if status in ('valid',):
                status = 'unverified'
            contact.email_status = status
            return contact
        
        # Need first name, last name, and domain
        if not contact.first_name or not contact.last_name or not contact.company_domain:
            self.logger.warning(f"Incomplete data for email discovery: {contact.full_name}")
            contact.email_status = "not_found"
            return contact
        
        # Generate and validate candidates
        discovery = self.generator.generate_and_validate(
            contact.first_name,
            contact.last_name,
            contact.company_domain
        )
        
        # Pattern generator output is a guess, never a verified mailbox.
        if discovery.best_guess:
            contact.email = discovery.best_guess
            contact.email_status = "pattern_guess"
            contact.email_source = "pattern_guess"
            matching = next((c for c in discovery.candidates if c.email == discovery.best_guess), None)
            if matching:
                contact.email_confidence = matching.confidence
        else:
            contact.email_status = "not_found"
            contact.email_source = "none"
        
        return contact
    
    def discover_emails_batch(self, contacts: List[FinanceContact]) -> List[FinanceContact]:
        """
        Discover emails for multiple contacts.
        
        Args:
            contacts: List of contacts
            
        Returns:
            Contacts with emails populated where possible
        """
        for contact in contacts:
            self.discover_email(contact)
        
        return contacts
    
    def find_public_email(self, contact: FinanceContact, company_url: str) -> Optional[str]:
        """
        Search company website for publicly listed email.
        
        This looks for emails on:
        - Contact pages
        - Leadership bios
        - Press releases
        
        Args:
            contact: Contact to find email for
            company_url: Company website URL
            
        Returns:
            Email if found publicly, None otherwise
        """
        # PLACEHOLDER: In production, implement web scraping for emails
        # This is a complex task that requires:
        # 1. Crawling relevant pages (contact, about, leadership)
        # 2. Regex extraction of email addresses
        # 3. Matching emails to the specific person
        
        self.logger.info(f"[PLACEHOLDER] Would search {company_url} for {contact.full_name}'s email")
        return None

