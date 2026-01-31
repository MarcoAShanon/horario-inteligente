"""
Serviço de criptografia para dados sensíveis em repouso (LGPD)
Usa Fernet (AES-128-CBC com HMAC-SHA256) para criptografar PII
"""
import os
import logging
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import TypeDecorator, String

logger = logging.getLogger(__name__)

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is None:
        if not ENCRYPTION_KEY:
            logger.warning("ENCRYPTION_KEY nao configurada. Dados sensiveis nao serao criptografados.")
            return None
        _fernet = Fernet(ENCRYPTION_KEY.encode())
    return _fernet


def encrypt_value(value: str) -> str:
    """Criptografa um valor string. Retorna o valor original se a chave nao estiver configurada."""
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    """Descriptografa um valor string. Retorna o valor original se nao for possivel descriptografar."""
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except (InvalidToken, Exception):
        # Valor pode nao estar criptografado (dados antigos)
        return value


class EncryptedString(TypeDecorator):
    """
    TypeDecorator SQLAlchemy que criptografa/descriptografa transparentemente.
    Armazena dados criptografados no banco e retorna texto plano na aplicacao.
    Compativel com dados nao-criptografados existentes (migracao gradual).
    """
    impl = String
    cache_ok = True

    def __init__(self, length=None, **kwargs):
        if length:
            self.impl = String(length)
        super().__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        """Criptografa antes de salvar no banco"""
        if value is None:
            return value
        return encrypt_value(str(value))

    def process_result_value(self, value, dialect):
        """Descriptografa ao ler do banco"""
        if value is None:
            return value
        return decrypt_value(value)
