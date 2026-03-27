"""Load Chillion product documents into the RAG vector store"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

try:
    import PyPDF2
except ImportError:
    print("Installing PyPDF2...")
    os.system(f"{sys.executable} -m pip install PyPDF2")
    import PyPDF2

from app.rag.vector_store import VectorStore
from app.config import settings


def extract_text_from_pdf(pdf_path: str) -> str:
    text = []
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
    except Exception as e:
        print(f"  Error reading {pdf_path}: {e}")
    return "\n\n".join(text)


def extract_text_from_markdown(md_path: str) -> str:
    try:
        return Path(md_path).read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Error reading {md_path}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


def load_documents():
    docs_path = Path(settings.rag_docs_path)
    print(f"Loading documents from: {docs_path}")

    if not docs_path.exists():
        print(f"Docs path does not exist: {docs_path}")
        return

    files = list(docs_path.glob("*.pdf")) + list(docs_path.glob("*.md"))
    if not files:
        print(f"No PDF or Markdown files found in {docs_path}")
        return

    print(f"Found {len(files)} files")
    vector_store = VectorStore()

    all_chunks = []
    all_metadatas = []
    all_ids = []

    for doc_path in files:
        print(f"\nProcessing: {doc_path.name}")
        text = (
            extract_text_from_pdf(str(doc_path))
            if doc_path.suffix.lower() == ".pdf"
            else extract_text_from_markdown(str(doc_path))
        )
        if not text:
            print(f"  No text extracted from {doc_path.name}")
            continue

        chunks = chunk_text(text)
        doc_name = doc_path.stem
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadatas.append(
                {
                    "source": doc_path.name,
                    "document": doc_name,
                    "chunk_index": i,
                    "product_category": doc_name.lower().replace(" ", "_").replace("-", "_"),
                }
            )
            all_ids.append(f"{doc_name}_{i}")

    if not all_chunks:
        print("\nNo chunks to add to vector store")
        return

    print(f"\nAdding {len(all_chunks)} chunks to vector store...")
    vector_store.add_documents(documents=all_chunks, metadatas=all_metadatas, ids=all_ids)
    print("Successfully added documents to vector store!")


if __name__ == "__main__":
    load_documents()
