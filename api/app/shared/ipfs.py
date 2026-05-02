"""Pinata IPFS functions for uploading encrypted dataset bytes."""

import hashlib
from typing import Tuple

import httpx
from fastapi import HTTPException

from ..config.settings import Settings


def _get_credentials(settings: Settings) -> Tuple[str | None, str | None]:
    """Retrieve Pinata API credentials from settings.

    Args:
        settings (Settings): Application settings instance

    Returns:
        Tuple[str | None, str | None]: API key and secret key, or (None, None) if not configured
    """
    api_key = (
        settings.pinata_api_key.get_secret_value()
        if settings.pinata_api_key is not None
        else None
    )
    secret_key = (
        settings.pinata_secret_key.get_secret_value()
        if settings.pinata_secret_key is not None
        else None
    )
    return api_key, secret_key


def _get_headers(settings: Settings) -> dict:
    """Generate headers for Pinata API requests.

    Args:
        settings (Settings): Application settings instance

    Returns:
        dict: Headers including Pinata API key and secret key
    """
    api_key, secret_key = _get_credentials(settings)
    return {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": secret_key,
    }


async def upload_bytes(
    payload: bytes,
    filename: str,
    settings: Settings,
) -> Tuple[str, str]:
    """Upload raw bytes to IPFS via Pinata.

    Args:
        payload (bytes): Raw bytes to upload
        filename (str): Original filename for metadata
        settings (Settings): Application settings instance

    Returns:
        Tuple[str, str]: IPFS URL and SHA-256 hash (0x-prefixed)
    """
    api_key, secret_key = _get_credentials(settings)
    if not api_key or not secret_key:
        raise HTTPException(
            status_code=500, detail="Pinata API credentials not configured"
        )

    base_url = "https://api.pinata.cloud"

    try:
        file_hash = "0x" + hashlib.sha256(payload).hexdigest()
        upload_filename = f"dataset_{filename}.enc"
        files = {"file": (upload_filename, payload, "application/octet-stream")}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/pinning/pinFileToIPFS",
                headers=_get_headers(settings),
                files=files,
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500, detail=f"Pinata upload failed: {response.text}"
            )

        result = response.json()
        ipfs_hash = result.get("IpfsHash")

        if not ipfs_hash:
            raise HTTPException(
                status_code=500, detail="No IPFS hash returned from Pinata"
            )

        ipfs_url = f"ipfs://{ipfs_hash}"

        return ipfs_url, file_hash

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=500, detail=f"Network error uploading to Pinata: {str(exc)}"
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error uploading to IPFS: {str(exc)}"
        ) from exc


async def test_connection(settings: Settings) -> bool:
    """Test connection to Pinata API.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    api_key, secret_key = _get_credentials(settings)
    if not api_key or not secret_key:
        return False

    try:
        base_url = "https://api.pinata.cloud"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/data/testAuthentication",
                headers=_get_headers(settings),
            )
        return response.status_code == 200
    except Exception:
        return False


def _to_gateway_url(ipfs_url: str, settings: Settings) -> str:
    """Convert an IPFS URL to a Pinata gateway URL.

    Args:
        ipfs_url (str): IPFS URL (e.g., ipfs://<cid>)
        settings (Settings): Application settings instance

    Raises:
        HTTPException: Invalid IPFS URL format

    Returns:
        str: Gateway URL for accessing the IPFS content
    """
    if not ipfs_url.startswith("ipfs://"):
        raise HTTPException(status_code=400, detail=f"Invalid IPFS url: {ipfs_url}")
    cid = ipfs_url.replace("ipfs://", "")
    gateway_url = settings.pinata_gateway_url
    return f"{gateway_url.rstrip('/')}/ipfs/{cid}"
