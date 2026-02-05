"""
Encryption helpers for dataset files.
"""

import os
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_key() -> bytes:
    """ "Generate a 256-bit AES key.

    Returns:
        bytes: The generated key
    """

    return AESGCM.generate_key(bit_length=256)


def encrypt_bytes(plaintext: bytes, key: bytes, aad: bytes) -> Tuple[bytes, bytes]:
    """Encrypt plaintext with AES-GCM.

    Args:
        plaintext (bytes): The plaintext data to encrypt
        key (bytes): The AES key for encryption
        aad (bytes): Additional authenticated data

    Returns:
        Tuple[bytes, bytes]: The ciphertext and nonce used for encryption
    """

    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
    return ciphertext, nonce


def decrypt_bytes(ciphertext: bytes, key: bytes, nonce: bytes, aad: bytes) -> bytes:
    """Decrypt ciphertext with AES-GCM.

    Args:
        ciphertext (bytes): The ciphertext data to decrypt
        key (bytes): The AES key for decryption
        nonce (bytes): The nonce used during encryption
        aad (bytes): Additional authenticated data

    Returns:
        bytes: The decrypted plaintext
    """

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, aad)
