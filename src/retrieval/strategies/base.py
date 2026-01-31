"""
Base retrieval strategy interface
All retrieval strategies must inherit from this interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from src.models.document import Document


class BaseRetrievalStrategy(ABC):
    """
    Abstract base class for retrieval strategies

    All retrieval strategies must implement this interface to ensure
    consistency and enable dynamic switching.

    Example:
        class CustomStrategy(BaseRetrievalStrategy):
            async def search(self, query: str, k: int = 5, **kwargs) -> List[Document]:
                # Implementation
                return results
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize retrieval strategy with configuration

        Args:
            config: Strategy-specific configuration dictionary
        """
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def search(
        self, query: str, k: int = 5, filter_dict: Optional[Dict] = None, **kwargs
    ) -> List[Document]:
        """
        Execute search with this strategy

        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filters
            **kwargs: Additional strategy-specific parameters

        Returns:
            List of retrieved documents sorted by relevance
        """
        pass

    @abstractmethod
    async def search_with_scores(
        self, query: str, k: int = 5, filter_dict: Optional[Dict] = None, **kwargs
    ) -> List[tuple[Document, float]]:
        """
        Execute search and return scores

        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filters
            **kwargs: Additional strategy-specific parameters

        Returns:
            List of (document, score) tuples, sorted by score descending
        """
        pass

    def get_config(self) -> Dict[str, Any]:
        """
        Get strategy configuration

        Returns:
            Dictionary containing strategy configuration
        """
        return self.config

    def get_name(self) -> str:
        """
        Get strategy name

        Returns:
            Strategy class name
        """
        return self.name

    async def warmup(self) -> None:
        """
        Warmup strategy (optional)

        Called after initialization to prepare resources.
        Override if strategy needs warmup (e.g., loading models).

        Example:
            async def warmup(self):
                # Load BM25 index
                self.bm25_index = load_index(self.config['bm25_path'])
        """
        pass

    async def cleanup(self) -> None:
        """
        Cleanup resources (optional)

        Called when strategy is no longer needed.
        Override if strategy needs to cleanup resources.

        Example:
            async def cleanup(self):
                # Close database connections
                if self.bm25_index:
                    self.bm25_index.close()
        """
        pass
