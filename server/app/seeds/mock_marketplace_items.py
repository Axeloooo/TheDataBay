"""
Shared mock marketplace item manifest loader.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MANIFEST_RELATIVE_PATH = Path("shared") / "mock-marketplace-items.json"


@dataclass(frozen=True)
class MockMarketplaceItem:
    listing_id: str
    title: str
    description: str
    price_atomic: str
    dataset_url: str
    dataset_hash: str
    signature_url: str
    signature_hash: str


def resolve_manifest_path() -> Path:
    env_path = os.getenv("MOCK_MARKETPLACE_ITEMS_PATH")
    if env_path:
        manifest_path = Path(env_path).expanduser()
        if manifest_path.exists():
            return manifest_path
        raise FileNotFoundError(
            f"Mock marketplace manifest not found at override path: {manifest_path}"
        )

    checked_paths: list[Path] = []
    for parent in Path(__file__).resolve().parents:
        candidate = parent / DEFAULT_MANIFEST_RELATIVE_PATH
        checked_paths.append(candidate)
        if candidate.exists():
            return candidate

    searched = ", ".join(str(path) for path in checked_paths)
    raise FileNotFoundError(
        "Mock marketplace manifest not found. Checked: "
        f"{searched}. Set MOCK_MARKETPLACE_ITEMS_PATH to override."
    )


def load_mock_marketplace_items() -> list[MockMarketplaceItem]:
    manifest_path = resolve_manifest_path()
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [MockMarketplaceItem(**item) for item in raw["items"]]
