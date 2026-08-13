import os

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:

    key = os.getenv(
        "TRADEPILOT_BROKER_ENCRYPTION_KEY"
    )

    if not key:

        raise RuntimeError(
            "TRADEPILOT_BROKER_ENCRYPTION_KEY "
            "is not configured."
        )

    return Fernet(
        key.encode("utf-8")
    )


def encrypt_secret(value: str) -> str:

    return _get_fernet().encrypt(
        value.encode("utf-8")
    ).decode("utf-8")


def decrypt_secret(value: str) -> str:

    return _get_fernet().decrypt(
        value.encode("utf-8")
    ).decode("utf-8")


def generate_encryption_key() -> str:

    return Fernet.generate_key().decode(
        "utf-8"
    )
