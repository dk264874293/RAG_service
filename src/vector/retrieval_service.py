"""
Retrieval service
Provides vector similarity search and advanced retrieval capabilities
"""

import logging
from typing import List, Tuple, Dict, Any, Optional

from langchain_core.documents import Document as LangchainDocument

from ..models.document import Document
from .embed_service import EmbeddingService
from .vector_store import FAISSVectorStore
from ..retrieval.query_rewriter import QueryRewriter
from ..retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class RetrievalService:
    """Retrieval service"""

    def __init__(
        self,
        config_obj,
        vector_store: FAISSVectorStore,
        embedding_service: EmbeddingService,
    ):
        self.config = config_obj
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.query_rewriter = QueryRewriter()
        self.reranker = Reranker(model_name=config_obj.reranker_model)

    async def search(
        self, query: str, k: int = 5, filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """
        Semantic search

        Args:
            query: Query text
            k: Number of results to return
            filter_dict: Metadata filter conditions

        Returns:
            List of relevant documents
        """
        try:
            langchain_docs = await self.vector_store.similarity_search(
                query, k=k, filter_dict=filter_dict
            )

            # Convert to our Document format
            documents = []
            for lc_doc in langchain_docs:
                doc = Document(
                    page_content=lc_doc.page_content,
                    id_=lc_doc.metadata.get("doc_id", ""),
                    metadata=lc_doc.metadata,
                )
                documents.append(doc)

            logger.info(
                f"Retrieval successful: query='{query[:50]}...', returned {len(documents)} results"
            )
            return documents

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []

    async def search_with_scores(
        self, query: str, k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Search and return similarity scores

        Args:
            query: Query text
            k: Number of results to return

        Returns:
            List of (document, similarity score) tuples
        """
        try:
            results = await self.vector_store.similarity_search_with_score(query, k=k)

            # Convert format
            documents_with_scores = []
            for lc_doc, score in results:
                doc = Document(
                    page_content=lc_doc.page_content,
                    id_=lc_doc.metadata.get("doc_id", ""),
                    metadata=lc_doc.metadata,
                )
                documents_with_scores.append((doc, score))

            logger.info(
                f"Retrieval with scores successful: returned {len(documents_with_scores)} results"
            )
            return documents_with_scores

        except Exception as e:
            logger.error(f"Retrieval with scores failed: {e}")
            return []

    async def search_with_expansion(
        self, query: str, k: int = 5, filter_dict: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Search with query expansion for better recall

        Args:
            query: Query text
            k: Number of results to return
            filter_dict: Metadata filter conditions

        Returns:
            Dict containing:
                - results: List of documents
                - query_info: Information about query expansion
                - expansion_used: Whether expansion was used
        """
        try:
            enhanced = self.query_rewriter.enhance_query(query)
            expanded_queries = enhanced["expanded"]

            all_results = []
            for expanded_query in expanded_queries:
                results = await self.vector_store.similarity_search_with_score(
                    expanded_query, k=k * 2
                )
                all_results.append(results)

            merged_results = self.query_rewriter.merge_search_results(all_results, k=k)

            documents = []
            for lc_doc, fused_score in merged_results:
                doc = Document(
                    page_content=lc_doc.page_content,
                    id_=lc_doc.metadata.get("doc_id", ""),
                    metadata=lc_doc.metadata,
                )
                documents.append(doc)

            logger.info(
                f"Expanded search successful: query='{query[:50]}...', "
                f"expanded to {len(expanded_queries)} variants, returned {len(documents)} results"
            )

            return {
                "results": documents,
                "query_info": {
                    "original": enhanced["original"],
                    "rewritten": enhanced["rewritten"],
                    "expanded_count": enhanced["count"],
                    "variants": expanded_queries,
                },
                "expansion_used": len(expanded_queries) > 1,
            }

        except Exception as e:
            logger.error(f"Expanded search failed: {e}")
            return {
                "results": [],
                "query_info": {},
                "expansion_used": False,
                "error": str(e),
            }

    async def search_with_reranking(
        self, query: str, k: int = 5, filter_dict: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Search with reranking for better accuracy

        First retrieves top-k*3 documents, then reranks them using cross-encoder

        Args:
            query: Query text
            k: Number of results to return
            filter_dict: Metadata filter conditions

        Returns:
            Dict containing:
                - results: List of reranked documents
                - reranking_used: Whether reranking was used
                - reranking_scores: List of reranking scores
        """
        try:
            initial_k = k * 3

            langchain_docs = await self.vector_store.similarity_search(
                query, k=initial_k, filter_dict=filter_dict
            )

            if not self.reranker.is_available():
                logger.warning("Reranker not available, returning original results")

                documents = []
                for lc_doc in langchain_docs[:k]:
                    doc = Document(
                        page_content=lc_doc.page_content,
                        id_=lc_doc.metadata.get("doc_id", ""),
                        metadata=lc_doc.metadata,
                    )
                    documents.append(doc)

                return {
                    "results": documents,
                    "reranking_used": False,
                    "reranking_scores": [],
                }

            reranked_docs = self.reranker.rerank_documents(
                query, langchain_docs, top_k=k
            )

            documents = []
            scores = []
            for doc, score in reranked_docs:
                document = Document(
                    page_content=doc.page_content,
                    id_=doc.metadata.get("doc_id", ""),
                    metadata=doc.metadata,
                )
                documents.append(document)
                scores.append(score)

            logger.info(
                f"Reranked search successful: query='{query[:50]}...', "
                f"returned {len(documents)} reranked results"
            )

            return {
                "results": documents,
                "reranking_used": True,
                "reranking_scores": scores,
            }

        except Exception as e:
            logger.error(f"Reranked search failed: {e}")
            return {
                "results": [],
                "reranking_used": False,
                "reranking_scores": [],
                "error": str(e),
            }
