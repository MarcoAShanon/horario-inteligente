"""
Webhook utilities: constants, cache, auth, client resolution
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging
import os
from sqlalchemy import text

from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Configuração da Evolution API
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_WEBHOOK_TOKEN = os.getenv("EVOLUTION_WEBHOOK_TOKEN", "")

# Rate Limiter para webhooks
limiter = Limiter(key_func=get_remote_address)

# IPs confiáveis (localhost/internal)
TRUSTED_IPS = {"127.0.0.1", "::1", "localhost"}

# Cache de mapeamento instance → cliente_id
INSTANCE_TO_CLIENTE_CACHE = {}


def get_cliente_id_from_instance(instance_name: str) -> int:
    """
    Resolve cliente_id a partir do nome da instância WhatsApp
    Usa cache para performance

    Exemplos:
    - "HorarioInteligente" → 1
    - "DrMarco" → 2
    - "ClinicaX" → 3
    """
    # Verificar cache
    if instance_name in INSTANCE_TO_CLIENTE_CACHE:
        return INSTANCE_TO_CLIENTE_CACHE[instance_name]

    # Buscar no banco
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT id FROM clientes WHERE whatsapp_instance = :inst AND ativo = true"),
            {"inst": instance_name}
        ).fetchone()

        if result:
            cliente_id = result[0]
        else:
            # Fallback: se não encontrar, usa cliente padrão (desenvolvimento)
            logger.warning(f"⚠️ Instância não encontrada: {instance_name}, usando cliente_id=1")
            cliente_id = 1

        # Cachear
        INSTANCE_TO_CLIENTE_CACHE[instance_name] = cliente_id
        logger.info(f"✅ Instância mapeada: {instance_name} → cliente_id={cliente_id}")

        return cliente_id
    finally:
        db.close()


def verify_webhook_auth(request: Request) -> bool:
    """
    Verifica autenticação do webhook.
    Aceita:
    - Requisições de IPs confiáveis (localhost)
    - Requisições com token válido no header X-Webhook-Token
    """
    # Verificar IP de origem
    client_ip = request.client.host if request.client else None
    if client_ip in TRUSTED_IPS:
        return True

    # Verificar token no header
    if EVOLUTION_WEBHOOK_TOKEN:
        token = request.headers.get("X-Webhook-Token", "")
        if token == EVOLUTION_WEBHOOK_TOKEN:
            return True
        # Também aceitar no Authorization header
        auth = request.headers.get("Authorization", "")
        if auth == f"Bearer {EVOLUTION_WEBHOOK_TOKEN}":
            return True

    return False
