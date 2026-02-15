from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    chroma_path: str = "./chroma_db"
    
    groq_api_key: str = ""
    
    max_file_size: int = 1000000
    supported_languages: list = ["python", "javascript", "java"]
    
    class Config:
        env_file = ".env"

settings = Settings()
