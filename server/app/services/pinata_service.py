"""
Pinata IPFS service for uploading embedding signatures.
"""

import json
import gzip
import hashlib
import httpx
from typing import Tuple, List
from functools import lru_cache
from fastapi import Depends, HTTPException
from ..config.settings import Settings, get_settings


class PinataService:
    """Service for uploading files to IPFS via Pinata."""

    def __init__(self, settings: Settings):
        """Constructor for PinataService.

        Args:
            settings (Settings): Application settings instance
        """
        self.api_key = (
            settings.pinata_api_key.get_secret_value()
            if settings.pinata_api_key is not None
            else None
        )
        self.secret_key = (
            settings.pinata_secret_key.get_secret_value()
            if settings.pinata_secret_key is not None
            else None
        )
        self.base_url = "https://api.pinata.cloud"
        self.gateway_url = settings.pinata_gateway_url

    def _get_headers(self) -> dict:
        """Get authentication headers for Pinata API."""
        return {
            "pinata_api_key": self.api_key,
            "pinata_secret_api_key": self.secret_key,
        }

    async def upload_signature(
        self, embeddings: List[List[float]], filename: str, compress: bool = True
    ) -> Tuple[str, str]:
        """Upload embedding signature to IPFS via Pinata.

        Args:
            embeddings (List[List[float]]): List of embedding vectors
            filename (str): Original filename for metadata
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
        if not self.api_key or not self.secret_key:
            raise HTTPException(
                status_code=500, detail="Pinata API credentials not configured"
            )

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
                    f"{self.base_url}/pinning/pinFileToIPFS",
                    headers=self._get_headers(),
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

        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=500, detail=f"Network error uploading to Pinata: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error uploading to IPFS: {str(e)}"
            )

    async def test_connection(self) -> bool:
        """Test connection to Pinata API.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        if not self.api_key or not self.secret_key:
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/data/testAuthentication",
                    headers=self._get_headers(),
                )
            return response.status_code == 200
        except Exception:
            return False

    def _to_gateway_url(self, ipfs_url: str) -> str:
        """Convert an IPFS URL to a Pinata gateway URL.

        Args:
            ipfs_url (str): IPFS URL (e.g., ipfs://<cid>)

        Raises:
            HTTPException: Invalid IPFS URL format

        Returns:
            str: Gateway URL for accessing the IPFS content
        """
        if not ipfs_url.startswith("ipfs://"):
            raise HTTPException(status_code=400, detail=f"Invalid IPFS url: {ipfs_url}")
        cid = ipfs_url.replace("ipfs://", "")
        return f"{self.gateway_url.rstrip('/')}/ipfs/{cid}"

    async def download_signature_embeddings(
        self,
        signature_url: str,
        expected_signature_hash: str | None = None,
        compressed: bool = True,
    ) -> List[List[float]]:
        """Download embedding signature from IPFS via Pinata gateway.

        Args:
            signature_url (str): IPFS URL of the signature
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
        url = self._to_gateway_url(signature_url)

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
                    detail=f"Signature hash mismatch. expected={expected_signature_hash} actual={actual}",
                )

        if compressed:
            try:
                data_bytes = gzip.decompress(data_bytes)
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Failed to decompress signature: {e}"
                )

        try:
            payload = json.loads(data_bytes.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid signature JSON: {e}")

        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise HTTPException(
                status_code=400, detail="Signature JSON missing embeddings"
            )

        return embeddings


@lru_cache(maxsize=1)
def get_pinata_service(settings: Settings = Depends(get_settings)) -> PinataService:
    """Get singleton PinataService instance.

    Args:
        settings (Settings, optional): Application settings instance. Defaults to Depends(get_settings).

    Returns:
        PinataService: Singleton PinataService instance
    """
    return PinataService(settings)
