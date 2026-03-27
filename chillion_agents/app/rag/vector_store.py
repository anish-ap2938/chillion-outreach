"""Vector store for RAG"""
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings
from app.config import settings


class VectorStore:
    """Vector store for Chillion product documentation"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.vector_store_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="chillion_docs",
            metadata={"description": "Chillion product documentation"},
        )
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ):
        """Add documents to the vector store"""
        if ids is None:
            # Generate unique IDs
            existing_count = self.collection.count()
            ids = [f"doc_{existing_count + i}" for i in range(len(documents))]
        
        # Upsert to handle duplicates
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas or [{}] * len(documents),
            ids=ids,
        )
    
    def query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """Query the vector store - returns raw ChromaDB format"""
        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for similar documents - returns formatted results"""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )
        
        # Format results
        formatted = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })
        
        return formatted
    
    def get_context(self, query: str, max_chars: int = 2000) -> str:
        """Get relevant context as a single string for LLM prompts"""
        results = self.search(query, top_k=5)
        if not results:
            return ""
        
        context_parts = []
        total_chars = 0
        
        for result in results:
            text = result["text"]
            if total_chars + len(text) > max_chars:
                # Truncate if needed
                remaining = max_chars - total_chars
                if remaining > 100:
                    context_parts.append(text[:remaining] + "...")
                break
            context_parts.append(text)
            total_chars += len(text)
        
        return "\n\n---\n\n".join(context_parts)
    
    def count(self) -> int:
        """Get the number of documents in the collection"""
        return self.collection.count()
    
    def clear(self):
        """Clear all documents from the collection"""
        # Delete and recreate the collection
        self.client.delete_collection("chillion_docs")
        self.collection = self.client.get_or_create_collection(
            name="chillion_docs",
            metadata={"description": "Chillion product documentation"},
        )

