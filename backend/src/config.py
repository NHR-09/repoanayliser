from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"
    
    max_file_size: int = 1000000
    supported_languages: list = ["python", "javascript", "typescript", "tsx", "java"]
    
    db_path: str = "./.data/architech.db"
    session_expire_hours: int = 24
    hr_bootstrap_key: str = "architech_hr_bootstrap_key_2026"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
