from functools import lru_cache
from typing import List
from fastapi import Depends

from ..schemas.marketplace_schema import MarketplaceDataItem
from ..config.settings import Settings, get_settings


class MarketplaceService:
    """Service for managing marketplace items."""

    def __init__(self, settings: Settings):
        """Constructor for MarketplaceService.

        Args:
            settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).
        """
        self.settings = settings

    async def get_marketplace_items(self) -> List[MarketplaceDataItem]:
        """Retrieve all marketplace items.

        Returns:
            List[MarketplaceDataItem]: List of marketplace data items
        """

        return [
            MarketplaceDataItem(
                id="dataset1",
                title="Sample Dataset 1",
                description="This is a sample dataset for testing.",
                seller="0xSellerAddress1",
                price=10,
                dataset_url="ipfs://QmExampleHashDataset1",
                dataset_hash="0xExampleDatasetHash1",
                signature_url="ipfs://QmExampleHash1",
                signature_hash="0xExampleHash1",
                exists=True,
            ),
        ]


@lru_cache(maxsize=1)
def get_marketplace_service(
    settings: Settings = Depends(get_settings),
) -> MarketplaceService:
    """Get singleton instance of MarketplaceService.

    Args:
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        MarketplaceService: Instance of MarketplaceService
    """
    return MarketplaceService(settings)
