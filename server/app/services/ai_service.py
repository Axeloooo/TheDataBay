"""
AI Service for ranking datasets based on query embeddings.
"""

from typing import List
from functools import lru_cache
import torch
import torch.nn.functional as F
from fastapi import Depends

from ..schemas.ai_schema import DataItem, SimilarityResult
from ..services.llm_service import generate_single_embedding
from ..services.pinata_service import PinataService, get_pinata_service


class AIService:
    def __init__(self, pinata_service: PinataService):
        """Constructor for AIService.

        Args:
            pinata_service (PinataService): Pinata service instance
        """
        self._cache: dict[str, torch.Tensor] = {}
        self.pinata_service = pinata_service

    def _normalize_rows(self, X: torch.Tensor) -> torch.Tensor:
        """Normalize rows of a tensor.

        Args:
            X (torch.Tensor): Input tensor with rows to normalize

        Returns:
            torch.Tensor: Tensor with normalized rows
        """
        return F.normalize(X, p=2, dim=1)

    def _get_cached_tensor(self, signature_hash: str) -> torch.Tensor | None:
        """Retrieve cached tensor by signature hash.

        Args:
            signature_hash (str): Signature hash used as the cache key

        Returns:
            torch.Tensor | None: Cached tensor if found, else None
        """
        return self._cache.get(signature_hash.lower())

    def _set_cached_tensor(self, signature_hash: str, X: torch.Tensor) -> None:
        """Set cached tensor by signature hash.

        Args:
            signature_hash (str): Signature hash used as the cache key
            X (torch.Tensor): Tensor to cache
        """
        self._cache[signature_hash.lower()] = X

    def _dataset_score_topk_mean(
        self, q: torch.Tensor, Xn: torch.Tensor, k_rows: int
    ) -> float:
        """Calculate the mean of the top-k similarity scores between a query and dataset embeddings.

        Args:
            q (torch.Tensor): Normalized query tensor of shape (embedding_dim,)
            Xn (torch.Tensor): Normalized dataset embeddings tensor of shape (num_embeddings, embedding_dim)
            k_rows (int): Number of top similarity scores to consider

        Returns:
            float: Mean of the top-k similarity scores
        """
        sims = Xn @ q  # cosine similarities
        k_eff = min(k_rows, sims.numel())
        topk = torch.topk(sims, k_eff).values
        return float(topk.mean().item())

    async def rank_datasets(
        self,
        query: str,
        datasets: List[DataItem],
        top_k_datasets: int = 10,
        threshold: float | None = None,
        k_rows: int = 100,
    ) -> List[SimilarityResult]:
        """Rank datasets based on similarity to the query embedding.

        Args:
            query (str): Input query string
            datasets (List[DataItem]): List of dataset dictionaries to rank
            top_k_datasets (int, optional): Number of top datasets to return. Defaults to 10.
            threshold (float | None, optional): Minimum score threshold to include a dataset. Defaults to None.
            k_rows (int, optional): Number of top similarity scores to consider per dataset. Defaults to 100.
        Returns:
            List[SimilarityResult]: List of ranked dataset results with scores and metadata
        """
        q_list, dim = generate_single_embedding(query)
        q: torch.Tensor = torch.tensor(q_list, dtype=torch.float32)
        q: torch.Tensor = F.normalize(q, p=2, dim=0)

        results: List[SimilarityResult] = []

        for ds in datasets:
            ds_id = str(ds.id)
            sig_url = ds.signature_url
            sig_hash = ds.signature_hash

            Xn: torch.Tensor | None = None
            if sig_hash:
                Xn = self._get_cached_tensor(sig_hash)

            if Xn is None:
                embeddings = await self.pinata_service.download_signature_embeddings(
                    signature_url=sig_url,
                    expected_signature_hash=sig_hash,
                    compressed=True,
                )
                X = torch.tensor(embeddings, dtype=torch.float32)
                if X.ndim != 2 or X.shape[1] != q.shape[0]:
                    # dimension mismatch (wrong model, wrong file, etc.)
                    continue

                Xn = self._normalize_rows(X)
                if sig_hash:
                    self._set_cached_tensor(sig_hash, Xn)

            score: float = self._dataset_score_topk_mean(q, Xn, k_rows=k_rows)

            if threshold is not None and score < threshold:
                continue

            results.append(
                SimilarityResult(
                    id=ds_id,
                    score=score,
                    content=ds.description,
                    metadata={
                        "signature_url": sig_url,
                        "k_rows": k_rows,
                        "rows": int(Xn.shape[0]),
                        "dimension": int(Xn.shape[1]),
                    },
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k_datasets]


@lru_cache(maxsize=1)
def get_ai_service(
    pinata_service: PinataService = Depends(get_pinata_service),
) -> AIService:
    """Get singleton AIService instance.

    Args:
        pinata_service (PinataService, optional): PinataService instance. Defaults to Depends(get_pinata_service).

    Returns:
        AIService: Singleton AIService instance with persistent cache
    """
    return AIService(pinata_service)
