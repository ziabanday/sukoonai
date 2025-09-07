from pydantic import BaseModel
from dotenv import load_dotenv
import os

class Settings(BaseModel):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000

def load_settings():
    load_dotenv()
    api = os.getenv("OPENAI_API_KEY")
    if not api or not api.strip():
        raise RuntimeError("OPENAI_API_KEY missing. Create .env from .env.example")
    return Settings(
        OPENAI_API_KEY=api.strip(),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        EMBEDDING_MODEL=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        PORT=int(os.getenv("PORT", "8000")),
    )
