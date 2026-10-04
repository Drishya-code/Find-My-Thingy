from functools import lru_cache
import logging
import os
from app.core.config import settings

logger = logging.getLogger(__name__)
MODEL_CACHE = settings.data_dir / "models"
os.environ.setdefault("HF_HOME", str(MODEL_CACHE))
from sentence_transformers import SentenceTransformer

@lru_cache(maxsize=1)
def model():
    MODEL_CACHE.mkdir(parents=True, exist_ok=True)
    # Fast path: always load a complete cached model without contacting the Hub.
    try:
        return SentenceTransformer(
            settings.embedding_model,
            cache_folder=str(MODEL_CACHE),
            local_files_only=True,
        )
    except Exception as local_error:
        logger.info("Embedding model is not available in the local cache; downloading it once.")
        try:
            # Hugging Face's normal cache is resumable, so an interrupted or offline
            # first run can be retried without discarding completed files.
            return SentenceTransformer(
                settings.embedding_model,
                cache_folder=str(MODEL_CACHE),
                local_files_only=False,
            )
        except Exception as download_error:
            raise RuntimeError(
                f"Could not load embedding model '{settings.embedding_model}'. "
                f"Check your internet connection and retry; the local model cache is "
                f"{MODEL_CACHE}. The download can resume on the next attempt."
            ) from download_error

def encode(texts):
    return model().encode(texts, normalize_embeddings=True).tolist()
