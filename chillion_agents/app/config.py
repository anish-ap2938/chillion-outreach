"""Application configuration"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")
    
    # Database
    database_url: str = "sqlite:///./chillion_agents.db"
    
    # AI/LLM
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    llm_provider: str = "ollama"  # ollama, openai, or google
    
    # Ollama (for local open-source models)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"  # or mistral, qwen, etc.
    ollama_timeout: int = 120  # seconds
    
    # Google Custom Search (for intent listener)
    google_search_cx: Optional[str] = None  # Custom Search Engine ID
    
    # News API (for intent listener)
    news_api_key: Optional[str] = None
    
    # Google OAuth (for Gmail integration)
    google_oauth_client_id: Optional[str] = None
    google_oauth_client_secret: Optional[str] = None
    google_oauth_redirect_uri: Optional[str] = None
    
    # LinkedIn
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    
    # Email
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    sendgrid_api_key: Optional[str] = None
    
    # Rate limits
    max_linkedin_dms_per_day: int = 50
    max_emails_per_day: int = 200
    
    # RAG
    rag_docs_path: str = "./docs/chillion_products"
    vector_store_path: str = "./chroma_db"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Calendly
    calendly_access_token: Optional[str] = None
    calendly_user_uri: Optional[str] = None
    
    # Frontend URL (for OAuth redirects)
    frontend_url: str = "http://localhost:3000"

    # Prospeo people search
    prospeo_api_key: Optional[str] = None


settings = Settings()

