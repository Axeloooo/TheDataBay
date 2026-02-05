"""
Marketplace service module for handling marketplace-related operations.
"""

from typing import List

from ..schemas.marketplace_schema import MarketplaceDataItem
from ..config.settings import Settings


async def get_marketplace_items(settings: Settings) -> List[MarketplaceDataItem]:
    """Retrieve all marketplace items.

    Returns:
        List[MarketplaceDataItem]: List of marketplace data items
    """
    _ = settings
    return [
        MarketplaceDataItem(
            id=1,
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
