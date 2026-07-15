"""AES and RSA encryption helpers — using cryptography (ships with HA)."""
import base64
import binascii
import uuid

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives import serialization


def _generate_uuid() -> str:
    return binascii.hexlify(uuid.uuid4().bytes).decode("utf-8")


def pad(data: str) -> bytes:
    block_size = 16
    p = block_size - len(data) % block_size
    return (data + chr(p) * p).encode("utf-8")


def unpad(data: bytes) -> str:
    return data[: -data[-1]].decode("utf-8")


def aes_encrypt(data: str, key: str) -> str:
    cipher = Cipher(algorithms.AES(key.encode("utf-8")), modes.ECB())
    enc = cipher.encryptor()
    ct = enc.update(pad(data)) + enc.finalize()
    return base64.b64encode(ct).decode("utf-8")


def aes_decrypt(encrypted_data: str, key: str) -> str:
    cipher = Cipher(algorithms.AES(key.encode("utf-8")), modes.ECB())
    dec = cipher.decryptor()
    pt = dec.update(base64.b64decode(encrypted_data)) + dec.finalize()
    return unpad(pt)


def generate_aes_key() -> str:
    return _generate_uuid()


def rsa_load_public_key(pem_data: str):
    key_bytes = base64.b64decode(pem_data)
    return serialization.load_der_public_key(key_bytes)


def rsa_encrypt(data: str, public_key) -> str:
    key_size = public_key.key_size // 8
    max_chunk = key_size - 11
    data_bytes = data.encode("utf-8")
    encrypted = bytearray()
    for i in range(0, len(data_bytes), max_chunk):
        chunk = data_bytes[i : i + max_chunk]
        encrypted.extend(
            public_key.encrypt(chunk, asym_padding.PKCS1v15())
        )
    return base64.b64encode(bytes(encrypted)).decode("utf-8")
