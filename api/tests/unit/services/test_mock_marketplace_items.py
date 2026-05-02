import json

import pytest

from app.seeds.mock_marketplace_items import (
    load_mock_marketplace_items,
    resolve_manifest_path,
)


def test_resolve_manifest_path_finds_repo_manifest():
    manifest_path = resolve_manifest_path()

    assert manifest_path.name == "mock-marketplace-items.json"
    assert manifest_path.exists()
    assert manifest_path.parts[-2] == "shared"


def test_load_mock_marketplace_items_uses_env_override(tmp_path, monkeypatch):
    manifest_path = tmp_path / "mock-marketplace-items.json"
    manifest_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "listing_id": "listing-1",
                        "title": "Demo dataset",
                        "description": "Synthetic test fixture",
                        "price_atomic": "1000",
                        "dataset_url": "ipfs://dataset",
                        "dataset_hash": "hash-a",
                        "signature_url": "ipfs://signature",
                        "signature_hash": "hash-b",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MOCK_MARKETPLACE_ITEMS_PATH", str(manifest_path))

    items = load_mock_marketplace_items()

    assert len(items) == 1
    assert items[0].listing_id == "listing-1"


def test_resolve_manifest_path_errors_for_missing_env_override(monkeypatch):
    monkeypatch.setenv("MOCK_MARKETPLACE_ITEMS_PATH", "/tmp/does-not-exist.json")

    with pytest.raises(FileNotFoundError, match="override path"):
        resolve_manifest_path()
