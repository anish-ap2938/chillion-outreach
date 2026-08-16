"""
Database Storage Module

SQLite database for persisting leads, companies, and contacts.
Provides normalized tables with deduplication.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from ..models import SocialLead, Company, FinanceContact, Platform, IntentLevel, LeadStatus
from ..config import get_config

logger = logging.getLogger(__name__)


class LeadDatabase:
    """
    SQLite database for lead generation data.
    
    Tables:
    - social_leads: Social media and forum leads
    - companies: Company information
    - contacts: Finance contacts
    
    Example usage:
        db = LeadDatabase("leads.db")
        db.initialize()
        
        # Insert leads
        db.insert_social_lead(lead)
        
        # Query
        leads = db.get_social_leads(min_intent_score=0.5)
        
        # Export
        db.export_leads_to_csv("exports/leads.csv")
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path or get_config().storage.database_path)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def initialize(self):
        """Create database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Social leads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS social_leads (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    source_id TEXT,
                    author_username TEXT,
                    author_display_name TEXT,
                    author_profile_url TEXT,
                    author_bio TEXT,
                    author_company TEXT,
                    author_title TEXT,
                    author_followers INTEGER,
                    title TEXT,
                    text TEXT NOT NULL,
                    text_excerpt TEXT,
                    created_at TIMESTAMP,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_meta TEXT,
                    intent_score REAL DEFAULT 0.0,
                    intent_level TEXT DEFAULT 'none',
                    intent_keywords_matched TEXT,
                    product_keywords_matched TEXT,
                    reason_for_relevance TEXT,
                    status TEXT DEFAULT 'new',
                    notes TEXT
                )
            """)
            # Indexes for social leads
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_platform ON social_leads(platform)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_intent ON social_leads(intent_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_discovered ON social_leads(discovered_at)")
            
            # Companies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    domain TEXT UNIQUE,
                    website TEXT,
                    industry TEXT,
                    sub_industry TEXT,
                    employee_count INTEGER,
                    employee_range TEXT,
                    revenue_usd INTEGER,
                    revenue_range TEXT,
                    headquarters_city TEXT,
                    headquarters_state TEXT,
                    headquarters_country TEXT,
                    description TEXT,
                    founded_year INTEGER,
                    stock_symbol TEXT,
                    linkedin_url TEXT,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    source_url TEXT,
                    enrichment_data TEXT,
                    is_target_profile INTEGER DEFAULT 0,
                    target_score REAL DEFAULT 0.0,
                    UNIQUE(name, domain)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_companies_industry ON companies(industry)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_companies_target ON companies(is_target_profile)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name)")
            
            # Contacts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id TEXT PRIMARY KEY,
                    company_id TEXT,
                    company_name TEXT NOT NULL,
                    company_domain TEXT,
                    full_name TEXT NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    title TEXT NOT NULL,
                    email TEXT,
                    email_status TEXT,
                    phone TEXT,
                    linkedin_url TEXT,
                    twitter_handle TEXT,
                    source TEXT,
                    source_url TEXT,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bio TEXT,
                    seniority_level TEXT,
                    department TEXT DEFAULT 'Finance',
                    enrichment_data TEXT,
                    is_decision_maker INTEGER DEFAULT 0,
                    relevance_score REAL DEFAULT 0.0,
                    UNIQUE(company_name, full_name),
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_title ON contacts(title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_relevance ON contacts(relevance_score)")

            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    actor TEXT,
                    action TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at)")
            
            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_platform ON social_leads(platform)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_intent ON social_leads(intent_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON social_leads(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_companies_industry ON companies(industry)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_companies_target ON companies(is_target_profile)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_title ON contacts(title)")
            
            # Lightweight migrations for existing DBs
            self._ensure_column(conn, "social_leads", "reason_for_relevance", "TEXT")
            self._ensure_column(conn, "contacts", "provider", "TEXT")
            self._ensure_column(conn, "contacts", "provider_id", "TEXT")
            self._ensure_column(conn, "contacts", "email_confidence", "REAL")
            self._ensure_column(conn, "contacts", "email_source", "TEXT")

            conn.commit()
            self.logger.info(f"Database initialized: {self.db_path}")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, col_type: str):
        """Add column if it does not exist (simple SQLite migration)."""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [row["name"] for row in cursor.fetchall()]
        if column not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            self.logger.info(f"Added missing column '{column}' to '{table}'")
    
    # =========================================================================
    # Social Leads
    # =========================================================================
    
    def insert_social_lead(self, lead: SocialLead) -> bool:
        """
        Insert a social lead into the database.
        
        Args:
            lead: SocialLead to insert
            
        Returns:
            True if inserted, False if duplicate
        """
        import json
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO social_leads (
                        id, platform, url, source_id, author_username, author_display_name,
                        author_profile_url, author_bio, author_company, author_title,
                        author_followers, title, text, text_excerpt, created_at,
                        discovered_at, source_meta, intent_score, intent_level,
                    intent_keywords_matched, product_keywords_matched, reason_for_relevance, status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lead.id,
                    lead.platform.value if isinstance(lead.platform, Platform) else lead.platform,
                    lead.url,
                    lead.source_id,
                    lead.author_username,
                    lead.author_display_name,
                    lead.author_profile_url,
                    lead.author_bio,
                    lead.author_company,
                    lead.author_title,
                    lead.author_followers,
                    lead.title,
                    lead.text,
                    lead.text_excerpt,
                    lead.created_at.isoformat() if lead.created_at else None,
                    lead.discovered_at.isoformat() if lead.discovered_at else None,
                    json.dumps(lead.source_meta) if lead.source_meta else None,
                    lead.intent_score,
                    lead.intent_level.value if isinstance(lead.intent_level, IntentLevel) else lead.intent_level,
                    json.dumps(lead.intent_keywords_matched) if lead.intent_keywords_matched else None,
                    json.dumps(lead.product_keywords_matched) if lead.product_keywords_matched else None,
                    lead.reason_for_relevance,
                    lead.status.value if isinstance(lead.status, LeadStatus) else lead.status,
                    lead.notes,
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                self.logger.debug(f"Duplicate lead: {lead.url}")
                return False
    
    def insert_social_leads_batch(self, leads: List[SocialLead]) -> Dict[str, int]:
        """Insert multiple leads, handling duplicates"""
        inserted = 0
        duplicates = 0
        
        for lead in leads:
            if self.insert_social_lead(lead):
                inserted += 1
            else:
                duplicates += 1
        
        self.logger.info(f"Inserted {inserted} leads, {duplicates} duplicates skipped")
        return {"inserted": inserted, "duplicates": duplicates}

    def insert_audit_event(self, actor: str, action: str, entity_type: Optional[str] = None, entity_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Record an audit event"""
        import json
        audit_id = f"audit_{int(datetime.utcnow().timestamp() * 1000)}"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_events (id, actor, action, entity_type, entity_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                audit_id,
                actor,
                action,
                entity_type,
                entity_id,
                json.dumps(metadata) if metadata else None,
            ))
            conn.commit()
        return audit_id
    
    def get_social_leads(
        self,
        platform: Optional[str] = None,
        min_intent_score: Optional[float] = None,
        status: Optional[str] = None,
        since_days: Optional[int] = None,
        limit: int = 1000,
        offset: int = 0,
        sort_by: str = "intent_score",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Query social leads with optional filters and pagination"""
        import json

        # Whitelist sort columns
        sort_column = "intent_score" if sort_by not in {"intent_score", "discovered_at"} else sort_by
        order = "DESC" if sort_order.lower() != "asc" else "ASC"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            base_query = "FROM social_leads WHERE 1=1"
            params = []
            
            if platform:
                base_query += " AND platform = ?"
                params.append(platform)
            
            if min_intent_score is not None:
                base_query += " AND intent_score >= ?"
                params.append(min_intent_score)
            
            if status:
                base_query += " AND status = ?"
                params.append(status)

            if since_days is not None:
                base_query += " AND discovered_at >= datetime('now', ?)"
                params.append(f"-{since_days} days")
            
            # Count total
            cursor.execute(f"SELECT COUNT(*) {base_query}", params)
            total = cursor.fetchone()[0]

            query = f"SELECT * {base_query} ORDER BY {sort_column} {order}, discovered_at DESC LIMIT ? OFFSET ?"
            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()
            
            leads = []
            for row in rows:
                lead = dict(row)
                if lead.get('source_meta'):
                    lead['source_meta'] = json.loads(lead['source_meta'])
                if lead.get('intent_keywords_matched'):
                    lead['intent_keywords_matched'] = json.loads(lead['intent_keywords_matched'])
                if lead.get('product_keywords_matched'):
                    lead['product_keywords_matched'] = json.loads(lead['product_keywords_matched'])
                leads.append(lead)
            
            return {"total": total, "leads": leads}
    
    # =========================================================================
    # Companies
    # =========================================================================
    
    def insert_company(self, company: Company) -> bool:
        """Insert a company into the database"""
        import json
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO companies (
                        id, name, domain, website, industry, sub_industry,
                        employee_count, employee_range, revenue_usd, revenue_range,
                        headquarters_city, headquarters_state, headquarters_country,
                        description, founded_year, stock_symbol, linkedin_url,
                        discovered_at, source, source_url, enrichment_data,
                        is_target_profile, target_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company.id or f"company_{hash(company.name)}",
                    company.name,
                    company.domain,
                    company.website,
                    company.industry,
                    company.sub_industry,
                    company.employee_count,
                    company.employee_range,
                    company.revenue_usd,
                    company.revenue_range,
                    company.headquarters_city,
                    company.headquarters_state,
                    company.headquarters_country,
                    company.description,
                    company.founded_year,
                    company.stock_symbol,
                    company.linkedin_url,
                    company.discovered_at.isoformat() if company.discovered_at else None,
                    company.source,
                    company.source_url,
                    json.dumps(company.enrichment_data) if company.enrichment_data else None,
                    1 if company.is_target_profile else 0,
                    company.target_score,
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                self.logger.debug(f"Duplicate company: {company.name}")
                return False
    
    def get_companies(
        self,
        industry: Optional[str] = None,
        is_target: Optional[bool] = None,
        limit: int = 1000,
        offset: int = 0,
        sort_by: str = "target_score",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Query companies with optional filters and pagination"""
        sort_column = "target_score" if sort_by not in {"target_score", "name", "industry"} else sort_by
        order = "DESC" if sort_order.lower() != "asc" else "ASC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            base_query = "FROM companies WHERE 1=1"
            params = []
            
            if industry:
                base_query += " AND industry LIKE ?"
                params.append(f"%{industry}%")
            
            if is_target is not None:
                base_query += " AND is_target_profile = ?"
                params.append(1 if is_target else 0)
            
            cursor.execute(f"SELECT COUNT(*) {base_query}", params)
            total = cursor.fetchone()[0]

            query = f"SELECT * {base_query} ORDER BY {sort_column} {order} LIMIT ? OFFSET ?"
            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()
            return {"total": total, "companies": [dict(row) for row in rows]}
    
    # =========================================================================
    # Contacts
    # =========================================================================
    
    def insert_contact(self, contact: FinanceContact) -> bool:
        """Insert a contact into the database"""
        import json
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO contacts (
                        id, company_id, company_name, company_domain, full_name,
                        first_name, last_name, title, email, email_status, phone,
                        linkedin_url, twitter_handle, source, source_url,
                        discovered_at, bio, seniority_level, department,
                        enrichment_data, is_decision_maker, relevance_score,
                        provider, provider_id, email_confidence, email_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    contact.id or f"contact_{hash(contact.full_name + contact.company_name)}",
                    contact.company_id,
                    contact.company_name,
                    contact.company_domain,
                    contact.full_name,
                    contact.first_name,
                    contact.last_name,
                    contact.title,
                    contact.email,
                    contact.email_status,
                    contact.phone,
                    contact.linkedin_url,
                    contact.twitter_handle,
                    contact.source.value if hasattr(contact.source, 'value') else contact.source,
                    contact.source_url,
                    contact.discovered_at.isoformat() if contact.discovered_at else None,
                    contact.bio,
                    contact.seniority_level,
                    contact.department,
                    json.dumps(contact.enrichment_data) if contact.enrichment_data else None,
                    1 if contact.is_decision_maker else 0,
                    contact.relevance_score,
                    contact.provider,
                    contact.provider_id,
                    contact.email_confidence,
                    getattr(contact, "email_source", None),
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                self.logger.debug(f"Duplicate contact: {contact.full_name} at {contact.company_name}")
                existing = self.get_contact_for_upsert(contact)
                if existing:
                    return self._update_existing_contact(existing, contact)
                return False

    def get_contact_for_upsert(self, contact: FinanceContact) -> Optional[Dict[str, Any]]:
        """Find an existing lead contact by provider id, then name+company."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if contact.provider_id:
                cursor.execute(
                    "SELECT * FROM contacts WHERE provider = ? AND provider_id = ? LIMIT 1",
                    (contact.provider or "prospeo", contact.provider_id),
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
            cursor.execute(
                """
                SELECT * FROM contacts
                WHERE lower(company_name) = lower(?) AND lower(full_name) = lower(?)
                LIMIT 1
                """,
                (contact.company_name, contact.full_name),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def upsert_contact(self, contact: FinanceContact) -> bool:
        """
        Insert a new lead contact or upgrade an existing one.

        Never replaces a verified email with a pattern guess.
        Never erases populated fields with None.
        """
        existing = self.get_contact_for_upsert(contact)
        if not existing:
            return self.insert_contact(contact)
        return self._update_existing_contact(existing, contact)

    def _update_existing_contact(self, existing: Dict[str, Any], contact: FinanceContact) -> bool:
        merged = _merge_contact_row(existing, contact)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE contacts SET
                    company_domain = ?,
                    first_name = ?,
                    last_name = ?,
                    title = ?,
                    email = ?,
                    email_status = ?,
                    email_confidence = ?,
                    email_source = ?,
                    linkedin_url = ?,
                    source = ?,
                    source_url = ?,
                    seniority_level = ?,
                    department = ?,
                    enrichment_data = ?,
                    is_decision_maker = ?,
                    relevance_score = ?,
                    provider = ?,
                    provider_id = ?
                WHERE id = ?
                """,
                (
                    merged["company_domain"],
                    merged["first_name"],
                    merged["last_name"],
                    merged["title"],
                    merged["email"],
                    merged["email_status"],
                    merged["email_confidence"],
                    merged["email_source"],
                    merged["linkedin_url"],
                    merged["source"],
                    merged["source_url"],
                    merged["seniority_level"],
                    merged["department"],
                    merged["enrichment_data"],
                    merged["is_decision_maker"],
                    merged["relevance_score"],
                    merged["provider"],
                    merged["provider_id"],
                    existing["id"],
                ),
            )
            conn.commit()
            contact.id = existing["id"]
            return True
    
    def get_contacts(
        self,
        company_name: Optional[str] = None,
        seniority: Optional[str] = None,
        has_email: Optional[bool] = None,
        limit: int = 1000,
        offset: int = 0,
        sort_by: str = "relevance_score",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Query contacts with optional filters and pagination"""
        sort_column = "relevance_score" if sort_by not in {"relevance_score", "company_name", "full_name"} else sort_by
        order = "DESC" if sort_order.lower() != "asc" else "ASC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            base_query = "FROM contacts WHERE 1=1"
            params = []
            
            if company_name:
                base_query += " AND company_name LIKE ?"
                params.append(f"%{company_name}%")
            
            if seniority:
                base_query += " AND seniority_level = ?"
                params.append(seniority)
            
            if has_email is True:
                base_query += " AND email IS NOT NULL AND email != ''"
            elif has_email is False:
                base_query += " AND (email IS NULL OR email = '')"
            
            cursor.execute(f"SELECT COUNT(*) {base_query}", params)
            total = cursor.fetchone()[0]

            query = f"SELECT * {base_query} ORDER BY {sort_column} {order} LIMIT ? OFFSET ?"
            cursor.execute(query, params + [limit, offset])
            return {"total": total, "contacts": [dict(row) for row in cursor.fetchall()]}
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM social_leads")
            stats["total_social_leads"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM social_leads WHERE intent_score >= 0.5")
            stats["high_intent_leads"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM companies")
            stats["total_companies"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM companies WHERE is_target_profile = 1")
            stats["target_companies"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM contacts")
            stats["total_contacts"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM contacts WHERE email IS NOT NULL AND email != ''")
            stats["contacts_with_email"] = cursor.fetchone()[0]
            
            return stats


_EMAIL_RANK = {
    "verified": 5,
    "likely": 4,
    "unverified": 3,
    "pattern_guess": 2,
    "invalid": 1,
    "not_found": 0,
}


def _prefer_text(incoming: Any, existing: Any) -> Any:
    if incoming is None or incoming == "":
        return existing
    if existing is None or existing == "":
        return incoming
    return incoming


def _merge_contact_row(existing: Dict[str, Any], incoming: FinanceContact) -> Dict[str, Any]:
    """Upgrade stored contact fields without destroying stronger data."""
    incoming_status = (incoming.email_status or "").lower()
    existing_status = (existing.get("email_status") or "").lower()
    incoming_rank = _EMAIL_RANK.get(incoming_status, 0)
    existing_rank = _EMAIL_RANK.get(existing_status, 0)

    email = existing.get("email")
    email_status = existing.get("email_status")
    email_confidence = existing.get("email_confidence")
    email_source = existing.get("email_source")
    if incoming.email:
        if incoming_rank >= existing_rank or not existing.get("email"):
            email = incoming.email
            email_status = incoming.email_status
            email_confidence = incoming.email_confidence if incoming.email_confidence is not None else existing.get("email_confidence")
            email_source = getattr(incoming, "email_source", None) or existing.get("email_source")

    linkedin_url = existing.get("linkedin_url")
    if incoming.linkedin_url and not linkedin_url:
        linkedin_url = incoming.linkedin_url
    elif incoming.linkedin_url and (incoming.provider or "") == "prospeo":
        linkedin_url = incoming.linkedin_url

    provider = existing.get("provider")
    provider_id = existing.get("provider_id")
    source = existing.get("source")
    if (incoming.provider or "") == "prospeo":
        provider = "prospeo"
        source = incoming.source.value if hasattr(incoming.source, "value") else (incoming.source or source)
        if incoming.provider_id:
            provider_id = incoming.provider_id
    elif not provider_id and incoming.provider_id:
        provider = incoming.provider or provider
        provider_id = incoming.provider_id

    incoming_enrichment = incoming.enrichment_data or {}
    existing_enrichment = existing.get("enrichment_data")
    merged_enrichment = incoming_enrichment
    if existing_enrichment and not incoming_enrichment:
        merged_enrichment = existing_enrichment
    elif incoming_enrichment:
        try:
            previous = json.loads(existing_enrichment) if isinstance(existing_enrichment, str) else (existing_enrichment or {})
        except (TypeError, ValueError):
            previous = {}
        if isinstance(previous, dict):
            merged_enrichment = {**previous, **incoming_enrichment}

    return {
        "company_domain": _prefer_text(incoming.company_domain, existing.get("company_domain")),
        "first_name": _prefer_text(incoming.first_name, existing.get("first_name")),
        "last_name": _prefer_text(incoming.last_name, existing.get("last_name")),
        "title": _prefer_text(incoming.title, existing.get("title")),
        "email": email,
        "email_status": email_status,
        "email_confidence": email_confidence,
        "email_source": email_source,
        "linkedin_url": linkedin_url,
        "source": source,
        "source_url": _prefer_text(incoming.source_url, existing.get("source_url")),
        "seniority_level": _prefer_text(incoming.seniority_level, existing.get("seniority_level")),
        "department": _prefer_text(incoming.department, existing.get("department")),
        "enrichment_data": json.dumps(merged_enrichment) if isinstance(merged_enrichment, dict) else merged_enrichment,
        "is_decision_maker": 1 if incoming.is_decision_maker else existing.get("is_decision_maker") or 0,
        "relevance_score": incoming.relevance_score if incoming.relevance_score else existing.get("relevance_score") or 0,
        "provider": provider,
        "provider_id": provider_id,
    }


