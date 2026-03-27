"""CSV Processing Service - Parse prospect CSVs"""
import csv
import io
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime


class ProspectCSVRow(BaseModel):
    """Single prospect from CSV"""
    name: str
    email: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None
    
    @validator('email', pre=True)
    def validate_email(cls, v):
        if v and '@' not in str(v):
            return None
        return v if v else None
    
    @validator('linkedin_url', pre=True)
    def validate_linkedin(cls, v):
        if v and 'linkedin.com' not in str(v).lower():
            return None
        return v if v else None


class CSVProcessResult(BaseModel):
    """Result of CSV processing"""
    success: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    prospects: List[ProspectCSVRow]
    errors: List[str]


class CSVProcessor:
    """Process prospect CSV files"""
    
    # Common column name mappings
    COLUMN_MAPPINGS = {
        # Name variations
        'name': 'name',
        'full name': 'name',
        'fullname': 'name',
        'contact name': 'name',
        'contact': 'name',
        'first name': 'first_name',
        'firstname': 'first_name',
        'last name': 'last_name',
        'lastname': 'last_name',
        
        # Email variations
        'email': 'email',
        'email address': 'email',
        'e-mail': 'email',
        'contact email': 'email',
        
        # Company variations
        'company': 'company',
        'company name': 'company',
        'organization': 'company',
        'org': 'company',
        'employer': 'company',
        
        # Title variations
        'title': 'title',
        'job title': 'title',
        'position': 'title',
        'role': 'title',
        
        # LinkedIn variations
        'linkedin': 'linkedin_url',
        'linkedin url': 'linkedin_url',
        'linkedin profile': 'linkedin_url',
        'linkedin_url': 'linkedin_url',
        
        # Industry variations
        'industry': 'industry',
        'sector': 'industry',
        
        # Notes variations
        'notes': 'notes',
        'comments': 'notes',
        'description': 'notes',
    }
    
    def process_csv(self, content: str) -> CSVProcessResult:
        """
        Process CSV content and return structured prospects
        """
        prospects = []
        errors = []
        
        try:
            # Parse CSV
            reader = csv.DictReader(io.StringIO(content))
            
            # Map columns
            column_map = self._map_columns(reader.fieldnames or [])
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                try:
                    prospect_data = self._extract_prospect(row, column_map)
                    if prospect_data.get('name'):
                        prospect = ProspectCSVRow(**prospect_data)
                        prospects.append(prospect)
                    else:
                        errors.append(f"Row {row_num}: Missing name")
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return CSVProcessResult(
                success=len(prospects) > 0,
                total_rows=row_num - 1 if 'row_num' in dir() else 0,
                valid_rows=len(prospects),
                invalid_rows=len(errors),
                prospects=prospects,
                errors=errors[:10],  # Limit errors shown
            )
            
        except Exception as e:
            return CSVProcessResult(
                success=False,
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                prospects=[],
                errors=[f"CSV parsing error: {str(e)}"],
            )
    
    def _map_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """Map CSV columns to our expected fields"""
        column_map = {}
        for field in fieldnames:
            normalized = field.lower().strip()
            if normalized in self.COLUMN_MAPPINGS:
                column_map[field] = self.COLUMN_MAPPINGS[normalized]
        return column_map
    
    def _extract_prospect(self, row: Dict[str, Any], column_map: Dict[str, str]) -> Dict[str, Any]:
        """Extract prospect data from a row"""
        data = {}
        first_name = None
        last_name = None
        
        for csv_col, our_col in column_map.items():
            value = row.get(csv_col, '').strip()
            if not value:
                continue
                
            if our_col == 'first_name':
                first_name = value
            elif our_col == 'last_name':
                last_name = value
            else:
                data[our_col] = value
        
        # Combine first/last name if needed
        if not data.get('name') and (first_name or last_name):
            data['name'] = f"{first_name or ''} {last_name or ''}".strip()
        
        return data
    
    def generate_sample_csv(self) -> str:
        """Generate a sample CSV template"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Name', 'Email', 'Company', 'Title', 'LinkedIn URL', 'Industry', 'Notes'])
        
        # Sample rows
        writer.writerow([
            'John Smith',
            'john.smith@acme.com',
            'Acme Corporation',
            'CFO',
            'https://linkedin.com/in/johnsmith',
            'Manufacturing',
            'Met at Finance Summit 2024'
        ])
        writer.writerow([
            'Sarah Johnson',
            'sarah.j@techcorp.io',
            'TechCorp Inc',
            'VP Finance',
            'https://linkedin.com/in/sarahjohnson',
            'Technology',
            'Interested in AR automation'
        ])
        
        return output.getvalue()


csv_processor = CSVProcessor()

