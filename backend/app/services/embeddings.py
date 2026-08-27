from functools import lru_cache

from fastembed import TextEmbedding

from app.config import settings
from app.models import FAQ
from app.services.search_aliases import faq_search_aliases


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(model_name=settings.embedding_model)


@lru_cache(maxsize=1024)
def embed_query(text: str) -> list[float]:
    return next(_model().query_embed(text)).tolist()


@lru_cache(maxsize=256)
def embed_passage(text: str) -> list[float]:
    return next(_model().passage_embed([text])).tolist()


def faq_embedding_text(question: str, answer: str, category: str) -> str:
    aliases = " ".join(
        alias for alias in faq_search_aliases(question)
        if not any("\u0400" <= character <= "\u04ff" for character in alias)
    )
    return f"{answer} {question} Category: {category}. {aliases}"


def embed_faq(faq: FAQ) -> list[float]:
    return embed_passage(faq_embedding_text(faq.question, faq.answer, faq.category))
