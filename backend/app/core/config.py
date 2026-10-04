from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    data_dir: Path = ROOT / "storage"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    embedding_model: str = "all-MiniLM-L6-v2"
    max_upload_mb: int = 25
    chunk_words: int = 550
    chunk_overlap_words: int = 100
    retrieval_count: int = 5

settings = Settings()
if not settings.data_dir.is_absolute():
    settings.data_dir = (ROOT / settings.data_dir).resolve()
for path in (settings.data_dir, settings.data_dir / "uploads", settings.data_dir / "chroma"):
    path.mkdir(parents=True, exist_ok=True)
