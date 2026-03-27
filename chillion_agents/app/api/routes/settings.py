"""Settings API routes for templates, products, and knowledge base"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime

router = APIRouter()

# ==================== Data Storage (In-memory for now, should be moved to DB) ====================

from app.prompts import templates as prompt_templates


def _catalog_with_keys(items: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {key: {"key": key, **value} for key, value in items.items()}


CHILLION_PRODUCTS = _catalog_with_keys(prompt_templates.CHILLION_PRODUCTS)
EMAIL_TEMPLATES = _catalog_with_keys(prompt_templates.EMAIL_TEMPLATES)
LINKEDIN_TEMPLATES = {
    key: {
        "key": key,
        "name": value["name"],
        "message": value.get("message") or "",
    }
    for key, value in prompt_templates.LINKEDIN_TEMPLATES.items()
}

# Knowledge Base Documents (in-memory tracking)
KNOWLEDGE_DOCS: Dict[str, Dict] = {}


# ==================== Pydantic Models ====================

class ProductCreate(BaseModel):
    key: str
    name: str
    short_name: str = ""
    description: str = ""
    key_features: List[str] = []
    pain_points: List[str] = []
    blog_links: List[str] = []


class TemplateCreate(BaseModel):
    key: str
    name: str
    subject: Optional[str] = None
    body: Optional[str] = None
    message: Optional[str] = None


class KnowledgeStats(BaseModel):
    total_docs: int
    total_chunks: int


# ==================== Products API ====================

@router.get("/products")
async def get_all_products():
    """Get all products with full details"""
    return list(CHILLION_PRODUCTS.values())


@router.get("/products/{product_key}")
async def get_product(product_key: str):
    """Get a single product by key"""
    if product_key not in CHILLION_PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    return CHILLION_PRODUCTS[product_key]


@router.put("/products/{product_key}")
async def update_product(product_key: str, product: ProductCreate):
    """Update a product"""
    CHILLION_PRODUCTS[product_key] = product.model_dump()
    return CHILLION_PRODUCTS[product_key]


@router.post("/products")
async def create_product(product: ProductCreate):
    """Create a new product"""
    if product.key in CHILLION_PRODUCTS:
        raise HTTPException(status_code=400, detail="Product already exists")
    CHILLION_PRODUCTS[product.key] = product.model_dump()
    return CHILLION_PRODUCTS[product.key]


@router.delete("/products/{product_key}")
async def delete_product(product_key: str):
    """Delete a product"""
    if product_key not in CHILLION_PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    del CHILLION_PRODUCTS[product_key]
    return {"success": True}


# ==================== Email Templates API ====================

@router.get("/email-templates")
async def get_all_email_templates():
    """Get all email templates with full details"""
    return list(EMAIL_TEMPLATES.values())


@router.get("/email-templates/{template_key}")
async def get_email_template(template_key: str):
    """Get a single email template"""
    if template_key not in EMAIL_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")
    return EMAIL_TEMPLATES[template_key]


@router.put("/email-templates/{template_key}")
async def update_email_template(template_key: str, template: TemplateCreate):
    """Update an email template"""
    EMAIL_TEMPLATES[template_key] = {
        "key": template_key,
        "name": template.name,
        "subject": template.subject or "",
        "body": template.body or ""
    }
    return EMAIL_TEMPLATES[template_key]


@router.post("/email-templates")
async def create_email_template(template: TemplateCreate):
    """Create a new email template"""
    if template.key in EMAIL_TEMPLATES:
        raise HTTPException(status_code=400, detail="Template already exists")
    EMAIL_TEMPLATES[template.key] = {
        "key": template.key,
        "name": template.name,
        "subject": template.subject or "",
        "body": template.body or ""
    }
    return EMAIL_TEMPLATES[template.key]


# ==================== LinkedIn Templates API ====================

@router.get("/linkedin-templates")
async def get_all_linkedin_templates():
    """Get all LinkedIn templates with full details"""
    return list(LINKEDIN_TEMPLATES.values())


@router.get("/linkedin-templates/{template_key}")
async def get_linkedin_template(template_key: str):
    """Get a single LinkedIn template"""
    if template_key not in LINKEDIN_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")
    return LINKEDIN_TEMPLATES[template_key]


@router.put("/linkedin-templates/{template_key}")
async def update_linkedin_template(template_key: str, template: TemplateCreate):
    """Update a LinkedIn template"""
    LINKEDIN_TEMPLATES[template_key] = {
        "key": template_key,
        "name": template.name,
        "message": template.message or ""
    }
    return LINKEDIN_TEMPLATES[template_key]


@router.post("/linkedin-templates")
async def create_linkedin_template(template: TemplateCreate):
    """Create a new LinkedIn template"""
    if template.key in LINKEDIN_TEMPLATES:
        raise HTTPException(status_code=400, detail="Template already exists")
    LINKEDIN_TEMPLATES[template.key] = {
        "key": template.key,
        "name": template.name,
        "message": template.message or ""
    }
    return LINKEDIN_TEMPLATES[template.key]


# ==================== Knowledge Base API ====================

@router.get("/knowledge/documents")
async def get_knowledge_documents():
    """Get all knowledge base documents"""
    return list(KNOWLEDGE_DOCS.values())


@router.get("/knowledge/stats")
async def get_knowledge_stats():
    """Get knowledge base statistics"""
    total_chunks = sum(doc.get("chunks_count", 0) for doc in KNOWLEDGE_DOCS.values())
    return KnowledgeStats(
        total_docs=len(KNOWLEDGE_DOCS),
        total_chunks=total_chunks
    )


@router.post("/knowledge/upload")
async def upload_knowledge_documents(files: List[UploadFile] = File(...)):
    """Upload documents to knowledge base"""
    uploaded = []
    for file in files:
        doc_id = f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(KNOWLEDGE_DOCS)}"
        
        # Determine file type
        ext = file.filename.split(".")[-1].lower() if file.filename else "unknown"
        
        # Read content (in production, process and chunk the document)
        content = await file.read()
        
        # Simulate chunking (in production, use actual text splitting)
        estimated_chunks = max(1, len(content) // 1000)
        
        KNOWLEDGE_DOCS[doc_id] = {
            "id": doc_id,
            "filename": file.filename,
            "file_type": ext,
            "uploaded_at": datetime.now().isoformat(),
            "chunks_count": estimated_chunks,
            "status": "ready"
        }
        uploaded.append(KNOWLEDGE_DOCS[doc_id])
    
    return {"uploaded_count": len(uploaded), "documents": uploaded}


@router.delete("/knowledge/documents/{doc_id}")
async def delete_knowledge_document(doc_id: str):
    """Delete a knowledge base document"""
    if doc_id not in KNOWLEDGE_DOCS:
        raise HTTPException(status_code=404, detail="Document not found")
    del KNOWLEDGE_DOCS[doc_id]
    return {"success": True}


@router.post("/knowledge/reindex")
async def reindex_knowledge_base():
    """Reindex all documents in knowledge base"""
    # In production, this would re-process all documents
    for doc_id in KNOWLEDGE_DOCS:
        KNOWLEDGE_DOCS[doc_id]["status"] = "ready"
    return {"success": True, "reindexed": len(KNOWLEDGE_DOCS)}

