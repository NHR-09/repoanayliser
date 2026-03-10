from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    
    chroma_path: str
    
    groq_api_key: str
    
    max_file_size: int = 1000000
    supported_languages: list = ["python", "javascript", "java"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
