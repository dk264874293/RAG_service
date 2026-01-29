"""
DashScope text embedding service
"""

import logging
from typing import List

from langchain_community.embeddings import DashScopeEmbeddings
from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """DashScope text embedding service"""

    def __init__(self, config_obj):
        self.embedding_model = DashScopeEmbeddings(
            model=config_obj.dashscope_embedding_model,
            dashscope_api_key=config_obj.dashscope_api_key,
        )
        self.dimension = 1536  # text-embedding-v2 dimension
        logger.info(
            f"Initialized DashScope embedding service: {config_obj.dashscope_embedding_model}"
        )

    async def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text

        Args:
            text: Text to embed

        Returns:
            Vector representation (1536 dimensions)
        """
        try:
            vector = await self.embedding_model.aembed_query(text)
            logger.debug(
                f"Text embedded successfully: length={len(text)}, vector_dimension={len(vector)}"
            )
            return vector
        except Exception as e:
            logger.error(f"Text embedding failed: {e}")
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch embed texts

        Args:
            texts: List of texts to embed

        Returns:
            List of vectors
        """
        try:
            vectors = await self.embedding_model.aembed_documents(texts)
            logger.info(
                f"Batch embedding successful: count={len(texts)}, vector_dimension={len(vectors[0]) if vectors else 0}"
            )
            return vectors
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            raise

    def get_dimension(self) -> int:
        """Get vector dimension"""
        return self.dimension
