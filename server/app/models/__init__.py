"""
Models package — exports all SQLModel table classes so Alembic autogenerate
can discover them via SQLModel.metadata.
"""

from .agent import Agent, AgentPurchaseRequest, AgentRecommendation
from .dataset_embedding import DatasetEmbedding
from .dataset_key import DatasetKey

__all__ = [
    "Agent",
    "AgentPurchaseRequest",
    "AgentRecommendation",
    "DatasetEmbedding",
    "DatasetKey",
]
