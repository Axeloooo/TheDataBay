import asyncio

from app.services.marketplace_service import get_marketplace_items


def test_get_marketplace_items_returns_data(settings):
    items = asyncio.run(get_marketplace_items(settings))

    assert len(items) == 1
    item = items[0]
    assert item.title == "Sample Dataset 1"
    assert item.exists is True
