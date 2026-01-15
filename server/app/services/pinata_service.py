"""
Pinata IPFS service for uploading embedding signatures.
"""

import json
import gzip
import hashlib
import httpx
from typing import Tuple, List
from fastapi import HTTPException
from ..config import settings


class PinataService:
    """Service for uploading files to IPFS via Pinata."""

    def __init__(self):
        self.api_key = settings.pinata_api_key
        self.secret_key = settings.pinata_secret_key
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
        except:
            return False


pinata_service = PinataService()
