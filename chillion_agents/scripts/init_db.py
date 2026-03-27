"""Initialize database tables"""
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import Base, engine
from app.config import settings

if __name__ == "__main__":
    print(f"Creating database tables in: {settings.database_url}")
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

