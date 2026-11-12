"""Local sentence embeddings for Stage 1 (sentence-transformers on CPU)."""

from functools import cache

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MAX_CHARS = 2000  # the model reads about 256 tokens anyway


@cache
def _model():
    from sentence_transformers import (
        SentenceTransformer,  # heavy import, only when scoring
    )

    try:
        return SentenceTransformer(
            MODEL_NAME, local_files_only=True
        )  # no network once cached
    except OSError:
        return SentenceTransformer(MODEL_NAME)  # first run: download


def similarities(query: str, texts: list[str]) -> list[float]:
    """Cosine similarity of each text to the query."""
    model = _model()
    query_vec = model.encode([query[:MAX_CHARS]], normalize_embeddings=True)[0]
    doc_vecs = model.encode(
        [t[:MAX_CHARS] for t in texts], normalize_embeddings=True, batch_size=64
    )
    return (doc_vecs @ query_vec).tolist()
