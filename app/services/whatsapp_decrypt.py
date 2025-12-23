"""
Serviço de Descriptografia de Mídia do WhatsApp
Descriptografa áudios criptografados baixados do WhatsApp
"""
import base64
import hashlib
import logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


def decrypt_whatsapp_media(encrypted_data: bytes, media_key_base64: str, media_type: str = "audio") -> bytes:
    """
    Descriptografa mídia do WhatsApp usando AES-256-CBC

    Args:
        encrypted_data: Dados criptografados baixados
        media_key_base64: mediaKey em base64 (do audioMessage)
        media_type: Tipo de mídia ("audio", "image", "video", etc)

    Returns:
        bytes: Dados descriptografados

    Raises:
        Exception: Se a descriptografia falhar
    """
    try:
        logger.info(f"🔐 Iniciando descriptografia de {media_type}...")
        logger.info(f"   📊 Tamanho criptografado: {len(encrypted_data)} bytes")

        # 1. Decodificar mediaKey de base64
        media_key = base64.b64decode(media_key_base64)
        logger.info(f"   🔑 MediaKey decodificado: {len(media_key)} bytes")

        # 2. Expandir a chave usando HKDF (WhatsApp Protocol)
        # O WhatsApp usa diferentes info strings para cada tipo de mídia
        media_info_map = {
            "audio": b"WhatsApp Audio Keys",
            "image": b"WhatsApp Image Keys",
            "video": b"WhatsApp Video Keys",
            "document": b"WhatsApp Document Keys",
            "ptt": b"WhatsApp Audio Keys",  # PTT (Push-to-Talk) usa mesma info de áudio
        }

        info = media_info_map.get(media_type, b"WhatsApp Audio Keys")
        logger.info(f"   📝 Info string: {info}")

        # Expandir chave com HKDF
        iv, cipher_key, mac_key = expand_key(media_key, info)
        logger.info(f"   🔑 IV: {len(iv)} bytes")
        logger.info(f"   🔑 Cipher Key: {len(cipher_key)} bytes")
        logger.info(f"   🔑 MAC Key: {len(mac_key)} bytes")

        # 3. Verificar MAC (últimos 10 bytes são o MAC)
        mac = encrypted_data[-10:]
        ciphertext = encrypted_data[:-10]

        logger.info(f"   📊 Tamanho ciphertext: {len(ciphertext)} bytes")
        logger.info(f"   🔐 MAC: {len(mac)} bytes")

        # Calcular MAC esperado
        mac_input = iv + ciphertext
        expected_mac = hmac_sha256(mac_key, mac_input)[:10]

        if mac != expected_mac:
            logger.warning("⚠️ MAC não confere - arquivo pode estar corrompido")
            # Tentar descriptografar mesmo assim
        else:
            logger.info("✅ MAC verificado com sucesso")

        # 4. Descriptografar com AES-256-CBC
        cipher = Cipher(
            algorithms.AES(cipher_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()

        # 5. Remover padding PKCS7
        padding_length = decrypted_data[-1]
        decrypted_data = decrypted_data[:-padding_length]

        logger.info(f"✅ Descriptografia concluída: {len(decrypted_data)} bytes")

        return decrypted_data

    except Exception as e:
        logger.error(f"❌ Erro na descriptografia: {e}")
        raise


def expand_key(media_key: bytes, info: bytes) -> tuple:
    """
    Expande a mediaKey usando HKDF para gerar IV, cipher_key e mac_key

    Args:
        media_key: Chave de mídia (32 bytes)
        info: String de informação (ex: b"WhatsApp Audio Keys")

    Returns:
        tuple: (iv, cipher_key, mac_key)
    """
    # HKDF-Expand conforme WhatsApp Protocol
    # 112 bytes total: 16 (IV) + 32 (cipher) + 32 (mac) + 32 (reserva)
    expanded = hkdf_expand(media_key, info, 112)

    iv = expanded[:16]           # 16 bytes para IV
    cipher_key = expanded[16:48] # 32 bytes para AES-256
    mac_key = expanded[48:80]    # 32 bytes para HMAC

    return iv, cipher_key, mac_key


def hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """
    HKDF-Expand (RFC 5869)

    Args:
        prk: Pseudo-random key (mediaKey)
        info: Context info
        length: Tamanho desejado em bytes

    Returns:
        bytes: Chave expandida
    """
    import hmac

    hash_len = 32  # SHA-256 = 32 bytes
    n = (length + hash_len - 1) // hash_len

    okm = b""
    previous = b""

    for i in range(n):
        previous = hmac.new(
            prk,
            previous + info + bytes([i + 1]),
            hashlib.sha256
        ).digest()
        okm += previous

    return okm[:length]


def hmac_sha256(key: bytes, data: bytes) -> bytes:
    """
    Calcula HMAC-SHA256

    Args:
        key: Chave HMAC
        data: Dados para calcular HMAC

    Returns:
        bytes: HMAC-SHA256
    """
    import hmac
    return hmac.new(key, data, hashlib.sha256).digest()
