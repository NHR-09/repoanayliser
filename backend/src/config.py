from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"
    
    # Qdrant Vector DB & Hugging Face Embedding Configuration
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_path: str = "./.data/qdrant"
    qdrant_collection_name: str = "architech_graph_rag"
    embedding_model: str = "BAAI/bge-base-en-v1.5"  # Small 768-dim Hugging Face model
    embedding_dim: int = 768
    sparse_model: str = "Qdrant/bm25"
    hybrid_search_limit: int = 10
    graph_expansion_hops: int = 2
    
    max_file_size: int = 1000000
    supported_languages: list = ["python", "javascript", "typescript", "tsx", "java"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()
