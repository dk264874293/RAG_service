"""Retrieval strategy factory
Creates retrieval strategies based on configuration
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class RetrievalStrategyFactory:
    """Factory for creating retrieval strategies"""

    _strategies = {}

    @classmethod
    def register(cls, name: str, strategy_class):
        """Register a retrieval strategy

        Args:
            name: Strategy name
            strategy_class: Strategy class
        """
        cls._strategies[name] = strategy_class
        logger.info(f"Registered retrieval strategy: {name}")

    @classmethod
    def create(
        cls,
        strategy_name: str,
        config: Dict[str, Any],
        dependencies: Optional[Dict[str, Any]] = None,
    ):
        """Create a retrieval strategy

        Args:
            strategy_name: Name of strategy to create
            config: Strategy configuration
            dependencies: Required dependencies (vector_store, embedding_service, etc.)

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy_name is unknown
        """
        strategy_class = cls._strategies.get(strategy_name)

        if not strategy_class:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown strategy: {strategy_name}. Available strategies: {available}"
            )

        logger.info(f"Creating retrieval strategy: {strategy_name}")

        full_config = {**config}
        if dependencies:
            full_config.update(dependencies)

        return strategy_class(full_config)

    @classmethod
    def get_available_strategies(cls) -> list:
        """Get list of available strategies"""
        return list(cls._strategies.keys())

    @classmethod
    def auto_register(cls):
        """
        Auto-register all strategy classes in strategies module

        This method scans strategies module and registers all
        classes that inherit from BaseRetrievalStrategy.
        """
        try:
            from .vector_strategy import VectorRetrievalStrategy

            cls.register("vector", VectorRetrievalStrategy)
            logger.info("Auto-registered: VectorRetrievalStrategy")
        except ImportError as e:
            logger.warning(f"Failed to import VectorRetrievalStrategy: {e}")

        try:
            from .hybrid_strategy import HybridRetrievalStrategy

            cls.register("hybrid", HybridRetrievalStrategy)
            logger.info("Auto-registered: HybridRetrievalStrategy")
        except ImportError as e:
            logger.warning(f"Failed to import HybridRetrievalStrategy: {e}")

        try:
            from .parent_child_strategy import ParentChildRetrievalStrategy

            cls.register("parent_child", ParentChildRetrievalStrategy)
            logger.info("Auto-registered: ParentChildRetrievalStrategy")
        except ImportError as e:
            logger.warning(f"Failed to import ParentChildRetrievalStrategy: {e}")
