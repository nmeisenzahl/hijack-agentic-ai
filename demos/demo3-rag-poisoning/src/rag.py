"""RAG module for Demo 3: ChromaDB + Azure OpenAI embeddings."""

import os
from pathlib import Path

import chromadb
from chromadb.config import Settings
from openai import AzureOpenAI


class RAGStore:
    """RAG store using ChromaDB with Azure OpenAI embeddings."""
    
    def __init__(
        self,
        chromadb_url: str | None = None,
        collection_name: str = "forecasting_kb"
    ):
        self.chromadb_url = chromadb_url or os.getenv("CHROMADB_URL", "http://localhost:8000")
        self.collection_name = collection_name
        
        # Parse ChromaDB URL
        # Format: http://host:port
        url_parts = self.chromadb_url.replace("http://", "").replace("https://", "")
        host, port = url_parts.split(":")
        
        # Initialize ChromaDB client
        self.client = chromadb.HttpClient(
            host=host,
            port=int(port),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize Azure OpenAI client for embeddings
        self.openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_API_KEY"),
            api_version=os.getenv("AZURE_API_VERSION", "2024-12-01-preview"),
            azure_endpoint=os.getenv("AZURE_API_BASE"),
        )
        self.embedding_model = os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", 
            "text-embedding-3-small"
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Forecasting knowledge base documents"}
        )
    
    def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding using Azure OpenAI."""
        response = self.openai_client.embeddings.create(
            input=text,
            model=self.embedding_model
        )
        return response.data[0].embedding
    
    def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = self.openai_client.embeddings.create(
            input=texts,
            model=self.embedding_model
        )
        return [item.embedding for item in response.data]
    
    def ingest_documents(self, documents_dir: str | Path) -> int:
        """Ingest all markdown documents from a directory.
        
        Returns the number of documents ingested.
        """
        documents_dir = Path(documents_dir)
        documents = []
        ids = []
        metadatas = []
        
        for md_file in documents_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            doc_id = md_file.stem
            
            documents.append(content)
            ids.append(doc_id)
            metadatas.append({
                "filename": md_file.name,
                "source": str(md_file),
            })
            
            print(f"📄 Loaded: {md_file.name}")
        
        if not documents:
            print("⚠️  No documents found to ingest")
            return 0
        
        # Generate embeddings
        print(f"\n🔄 Generating embeddings for {len(documents)} documents...")
        embeddings = self._get_embeddings(documents)
        
        # Add to ChromaDB
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        print(f"✅ Ingested {len(documents)} documents into ChromaDB")
        return len(documents)
    
    def query(self, query_text: str, n_results: int = 3) -> list[str]:
        """Query the knowledge base and return relevant documents.
        
        Returns list of document contents.
        """
        # Generate query embedding
        query_embedding = self._get_embedding(query_text)
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas"]
        )
        
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        print(f"\n🔍 RAG Query: '{query_text[:50]}...'")
        print(f"📚 Retrieved {len(documents)} documents:")
        for meta in metadatas:
            print(f"   - {meta.get('filename', 'unknown')}")
        
        return documents
    
    def clear(self):
        """Clear all documents from the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Forecasting knowledge base documents"}
        )
        print("🗑️  Cleared knowledge base")
