import faiss
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseFAISSIndex(ABC):
    """Abstract base class for FAISS index wrappers"""

    def __init__(self, dimension: int, config: Dict[str, Any]):
        self.dimension = dimension
        self.config = config
        self.index = None

    @abstractmethod
    def create_index(self) -> faiss.Index:
        """Create FAISS index"""
        pass

    @abstractmethod
    def train_index(self, vectors: list) -> None:
        """Train index (if needed)"""
        pass

    def get_index(self) -> faiss.Index:
        """Get FAISS index"""
        if self.index is None:
            self.index = self.create_index()
        return self.index


class FlatL2Index(BaseFAISSIndex):
    """Flat L2 index (exact search, no training)"""

    def create_index(self) -> faiss.Index:
        logger.info("Creating FlatL2 index for exact search")
        return faiss.IndexFlatL2(self.dimension)

    def train_index(self, vectors: list) -> None:
        pass


class IVFIndex(BaseFAISSIndex):
    """IVF index (approximate search, needs training)

    Parameters:
        nlist: Number of clusters (default: 100)
        nprobe: Number of clusters to search (default: 10)
    """

    def create_index(self) -> faiss.Index:
        nlist = self.config.get("nlist", 100)

        logger.info(f"Creating IVF index: nlist={nlist}")

        quantizer = faiss.IndexFlatL2(self.dimension)
        index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
        index.nprobe = self.config.get("nprobe", 10)

        return index

    def train_index(self, vectors: list) -> None:
        if self.index.is_trained:
            logger.info("Index already trained, skipping")
            return

        logger.info(f"Training IVF index with {len(vectors)} vectors")
        import numpy as np

        train_vectors = np.array(vectors).astype("float32")
        self.index.train(train_vectors)
        logger.info("IVF index training completed")


class IVFPQIndex(BaseFAISSIndex):
    """IVF-PQ index (approximate search, needs training)

    Parameters:
        nlist: Number of clusters (default: 100)
        m: Number of subquantizers (default: 64)
        nbits: Bits per subquantizer (default: 8)
    """

    def create_index(self) -> faiss.Index:
        nlist = self.config.get("nlist", 100)
        m = self.config.get("m", 64)
        nbits = self.config.get("nbits", 8)

        logger.info(f"Creating IVF-PQ index: nlist={nlist}, m={m}, nbits={nbits}")

        quantizer = faiss.IndexFlatL2(self.dimension)
        index = faiss.IndexIVFPQ(quantizer, self.dimension, nlist, m, nbits)
        return index

    def train_index(self, vectors: list) -> None:
        if self.index.is_trained:
            logger.info("Index already trained, skipping")
            return

        logger.info(f"Training IVF-PQ index with {len(vectors)} vectors")
        import numpy as np

        train_vectors = np.array(vectors).astype("float32")
        self.index.train(train_vectors)
        logger.info("IVF-PQ index training completed")


class HNSWIndex(BaseFAISSIndex):
    """HNSW index (graph-based approximate search)

    Parameters:
        M: Number of connections per node (default: 32)
        efConstruction: Build-time ef (default: 200)
        efSearch: Search-time ef (default: 64)
    """

    def create_index(self) -> faiss.Index:
        M = self.config.get("M", 32)

        logger.info(f"Creating HNSW index: M={M}")
        return faiss.IndexHNSWFlat(self.dimension, M)

    def train_index(self, vectors: list) -> None:
        pass

    def configure_search(self, ef_search: int):
        """Configure search-time ef parameter"""
        ef_search = self.config.get("efSearch", 64)
        self.index.hnsw.efSearch = ef_search
        logger.info(f"HNSW efSearch configured: {ef_search}")


class FAISSIndexFactory:
    """Factory for creating FAISS indexes"""

    _index_types = {
        "flat": FlatL2Index,
        "ivf": IVFIndex,
        "ivf_pq": IVFPQIndex,
        "hnsw": HNSWIndex,
    }

    @classmethod
    def create_index(
        cls,
        index_type: str,
        dimension: int,
        config: Optional[Dict[str, Any]] = None,
    ) -> BaseFAISSIndex:
        """Create FAISS index

        Args:
            index_type: Index type (flat, ivf_pq, hnsw)
            dimension: Vector dimension
            config: Index-specific configuration

        Returns:
            FAISS index wrapper instance

        Raises:
            ValueError: If index_type is unknown
        """
        config = config or {}
        index_class = cls._index_types.get(index_type.lower())

        if not index_class:
            available = ", ".join(cls._index_types.keys())
            raise ValueError(
                f"Unknown index type: {index_type}. Available types: {available}"
            )

        logger.info(f"Creating FAISS index type: {index_type}")
        return index_class(dimension, config)

    @classmethod
    def get_available_types(cls) -> list:
        """Get list of available index types"""
        return list(cls._index_types.keys())
