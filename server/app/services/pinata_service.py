"""
Pinata IPFS functions for uploading and downloading embedding signatures.
"""

import json
import gzip
import hashlib
from typing import Tuple, List

import httpx
from fastapi import HTTPException

from ..config.settings import Settings


def _get_credentials(settings: Settings) -> Tuple[str | None, str | None]:
    """Retrieve Pinata API credentials from settings.

    Args:
        settings (Settings): Application settings instance

    Returns:
        tuple[str | None, str | None]: API key and secret key, or (None, None) if not configured
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


async def upload_signature(
    embeddings: List[List[float]],
    filename: str,
    settings: Settings,
    compress: bool = True,
) -> Tuple[str, str]:
    """Upload embedding signature to IPFS via Pinata.

    Args:
        embeddings (List[List[float]]): List of embedding vectors
        filename (str): Original filename for metadata
        settings (Settings): Application settings instance
        compress (bool, optional): Whether to gzip compress the data. Defaults to True.

    Raises:
        HTTPException: If Pinata API credentials are not configured
        HTTPException: If the upload to Pinata fails
        HTTPException: If no IPFS hash is returned from Pinata
        HTTPException: If there is a network error during upload
        HTTPException: For any other errors during upload
    Returns:
        Tuple[str, str]: IPFS URL and SHA-256 signature hash
    """
    api_key, secret_key = _get_credentials(settings)
    if not api_key or not secret_key:
        raise HTTPException(
            status_code=500, detail="Pinata API credentials not configured"
        )

    base_url = "https://api.pinata.cloud"

    try:
        json_data = json.dumps({"embeddings": embeddings, "filename": filename})
        file_bytes = json_data.encode("utf-8")

        if compress:
            file_bytes = gzip.compress(file_bytes)
            file_ext = "json.gz"
        else:
            file_ext = "json"

        signature_hash = "0x" + hashlib.sha256(file_bytes).hexdigest()

        upload_filename = f"signature_{filename}.{file_ext}"

        files = {"file": (upload_filename, file_bytes, "application/octet-stream")}

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

        return ipfs_url, signature_hash

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=500, detail=f"Network error uploading to Pinata: {str(exc)}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error uploading to IPFS: {str(exc)}"
        ) from exc


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


async def download_signature_embeddings(
    signature_url: str,
    settings: Settings,
    expected_signature_hash: str | None = None,
    compressed: bool = True,
) -> List[List[float]]:
    """Download embedding signature from IPFS via Pinata gateway.

    Args:
        signature_url (str): IPFS URL of the signature
        settings (Settings): Application settings instance
        expected_signature_hash (str | None, optional): Expected SHA-256 hash of the signature (0x-prefixed). Defaults to None.
        compressed (bool, optional): Whether the signature file is compressed with gzip. Defaults to True.

    Raises:
        HTTPException: Failed to fetch signature from gateway
        HTTPException: Signature hash mismatch
        HTTPException: Failed to decompress signature
        HTTPException: Invalid signature JSON
        HTTPException: Signature JSON missing embeddings

    Returns:
        List[List[float]]: Embeddings extracted from the signature JSON
    """
    url = _to_gateway_url(signature_url, settings)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch signature from gateway: {resp.text}",
        )

    data_bytes = resp.content

    if expected_signature_hash:
        actual = "0x" + hashlib.sha256(data_bytes).hexdigest()
        if actual.lower() != expected_signature_hash.lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Signature hash mismatch. expected={expected_signature_hash} "
                    f"actual={actual}"
                ),
            )

    if compressed:
        try:
            data_bytes = gzip.decompress(data_bytes)
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Failed to decompress signature: {exc}"
            ) from exc

    try:
        payload = json.loads(data_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid signature JSON: {exc}"
        ) from exc

    embeddings = payload.get("embeddings")
    if not isinstance(embeddings, list) or not embeddings:
        raise HTTPException(status_code=400, detail="Signature JSON missing embeddings")

    return embeddings
