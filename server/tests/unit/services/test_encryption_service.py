from app.shared.encryption import decrypt_bytes, encrypt_bytes, generate_key


def test_encrypt_decrypt_roundtrip():
    key = generate_key()
    aad = b"listing-id"
    plaintext = b"hello world"

    ciphertext, nonce = encrypt_bytes(plaintext, key, aad)
    recovered = decrypt_bytes(ciphertext, key, nonce, aad)

    assert recovered == plaintext
