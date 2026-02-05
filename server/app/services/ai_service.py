"""
AI Service for ranking datasets based on query embeddings.
"""

from typing import List, OrderedDict
from functools import lru_cache
import torch
import torch.nn.functional as F
from fastapi import Depends

from ..config.settings import Settings, get_settings

from ..schemas.marketplace_schema import MarketplaceDataItem

from ..schemas.ai_schema import RankedDataset, ScoreExplanation
from ..services.llm_service import generate_single_embedding
from ..services.pinata_service import download_signature_embeddings


class AIService:
    """AI Service for ranking datasets based on query embeddings."""

    def __init__(
        self,
        settings: Settings,
    ):
        """Constructor for AIService.

        Args:
            settings (Settings): Application settings instance
        """
        self._cache: OrderedDict[str, torch.Tensor] = OrderedDict()
        self.settings = settings

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

        Uses LRU eviction: moves accessed items to the end of the cache.

        Args:
            signature_hash (str): Signature hash used as the cache key

        Returns:
            torch.Tensor | None: Cached tensor if found, else None
        """
        key = signature_hash.lower()
        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def _set_cached_tensor(self, signature_hash: str, X: torch.Tensor) -> None:
        """Set cached tensor by signature hash with LRU eviction.

        If cache exceeds maxsize, removes the least recently used item.

        Args:
            signature_hash (str): Signature hash used as the cache key
            X (torch.Tensor): Tensor to cache
        """
        key = signature_hash.lower()

        # If key exists, move to end
        if key in self._cache:
            self._cache.move_to_end(key)

        self._cache[key] = X

        # Evict least recently used if cache is full
        if len(self._cache) > self.settings.cache_maxsize:
            self._cache.popitem(last=False)  # Remove oldest (first) item

    def _dataset_score_topk_mean(self, q: torch.Tensor, Xn: torch.Tensor) -> float:
        """Calculate the mean of the top-k similarity scores between a query and dataset embeddings.

        Args:
            q (torch.Tensor): Normalized query tensor of shape (embedding_dim,)
            Xn (torch.Tensor): Normalized dataset embeddings tensor of shape (num_embeddings, embedding_dim)

        Returns:
            float: Mean of the top-k similarity scores
        """
        sims: torch.Tensor = Xn @ q  # cosine similarities
        k_eff: int = min(self.settings.k_rows, sims.numel())
        topk: torch.Tensor = torch.topk(sims, k_eff).values
        return float(topk.mean().item())

    async def rank_datasets(
        self,
        query: str,
        datasets: List[MarketplaceDataItem],
    ) -> List[RankedDataset]:
        """Rank datasets based on similarity to the query embedding.

        Args:
            query (str): Input query string
            datasets (List[MarketplaceDataItem]): List of dataset dictionaries to rank

        Returns:
            List[RankedDataset]: List of ranked dataset results with scores and metadata
        """
        q_list, dim = generate_single_embedding(query, self.settings)
        q: torch.Tensor = torch.tensor(q_list, dtype=torch.float32)
        q: torch.Tensor = F.normalize(q, p=2, dim=0)

        results: List[RankedDataset] = []

        for ds in datasets:
            sig_url = ds.signature_url
            sig_hash = ds.signature_hash

            Xn: torch.Tensor | None = None
            if sig_hash:
                Xn = self._get_cached_tensor(sig_hash)

            if Xn is None:
                embeddings = await download_signature_embeddings(
                    signature_url=sig_url,
                    expected_signature_hash=sig_hash,
                    compressed=True,
                    settings=self.settings,
                )
                X = torch.tensor(embeddings, dtype=torch.float32)
                if X.ndim != 2 or X.shape[1] != q.shape[0]:
                    continue

                Xn = self._normalize_rows(X)
                if sig_hash:
                    self._set_cached_tensor(sig_hash, Xn)

            score: float = self._dataset_score_topk_mean(q, Xn)

            if (
                self.settings.similarity_threshold is not None
                and score < self.settings.similarity_threshold
            ):
                continue

            results.append(
                RankedDataset(
                    item=MarketplaceDataItem(
                        id=ds.id,
                        title=ds.title,
                        description=ds.description,
                        seller=ds.seller,
                        price=ds.price,
                        dataset_url=ds.dataset_url,
                        dataset_hash=ds.dataset_hash,
                        signature_url=ds.signature_url,
                        signature_hash=ds.signature_hash,
                        exists=ds.exists,
                        purchase_count=ds.purchase_count,
                    ),
                    score=score,
                    explanation=ScoreExplanation(
                        method="topk_mean_cosine",
                        k_rows=self.settings.k_rows,
                        rows_in_dataset=Xn.shape[0],
                        dimension=dim,
                        normalized=True,
                    ),
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[: self.settings.top_k]


@lru_cache(maxsize=1)
def get_ai_service(
    settings: Settings = Depends(get_settings),
) -> AIService:
    """Get singleton AIService instance.

    Args:
        settings (Settings, optional): Application settings instance. Defaults to Depends(get_settings).
    Returns:
        AIService: Singleton AIService instance with persistent LRU cache
    """
    return AIService(settings)
