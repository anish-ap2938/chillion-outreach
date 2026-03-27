"""Base agent class"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from app.rag.vector_store import VectorStore
from app.models.database import AgentEvent
from sqlalchemy.orm import Session

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")


class BaseAgent(ABC, Generic[InputType, OutputType]):
    """Abstract base class for all agents"""
    
    def __init__(self, db: Session, vector_store: VectorStore = None):
        self.db = db
        self.vector_store = vector_store
    
    @abstractmethod
    def process(self, input_data: InputType) -> OutputType:
        """Process input and return output"""
        pass
    
    def log_event(self, event_type: str, payload: dict):
        """Log an agent event to the database"""
        event = AgentEvent(
            agent_type=self.__class__.__name__,
            event_type=event_type,
            payload=payload,
        )
        self.db.add(event)
        self.db.commit()
    
    def retrieve_rag_context(self, query: str, top_k: int = 3) -> str:
        """Retrieve relevant context from RAG vector store"""
        if not self.vector_store:
            return ""
        
        try:
            results = self.vector_store.search(query, top_k=top_k)
            context = "\n\n".join([r["text"] for r in results])
            self.log_event("rag_retrieved", {"query": query, "results_count": len(results)})
            return context
        except Exception as e:
            self.log_event("rag_error", {"error": str(e)})
            return ""

