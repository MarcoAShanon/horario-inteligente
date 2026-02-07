"""
Diagnostic endpoints: test, clear, conversations
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import os

from app.database import get_db
from app.services.anthropic_service import AnthropicService
from app.services.conversation_manager import conversation_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# IPs confiáveis (localhost/internal)
TRUSTED_IPS = {"127.0.0.1", "::1", "localhost"}
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", os.getenv("EVOLUTION_WEBHOOK_TOKEN", ""))


def verify_webhook_auth(request: Request) -> bool:
    """
    Verifica autenticação do webhook.
    Aceita:
    - Requisições de IPs confiáveis (localhost)
    - Requisições com token válido no header X-Webhook-Token
    """
    client_ip = request.client.host if request.client else None
    if client_ip in TRUSTED_IPS:
        return True

    if WEBHOOK_TOKEN:
        token = request.headers.get("X-Webhook-Token", "")
        if token == WEBHOOK_TOKEN:
            return True
        auth = request.headers.get("Authorization", "")
        if auth == f"Bearer {WEBHOOK_TOKEN}":
            return True

    return False


@router.get("/whatsapp/test")
async def test_webhook(request: Request, db: Session = Depends(get_db)):
    """Endpoint de teste - usa cliente padrão"""
    if not verify_webhook_auth(request):
        raise HTTPException(status_code=401, detail="Nao autorizado")
    cliente_id_teste = 1  # Cliente padrão para testes

    # Testar conexão com banco
    try:
        ai_service = AnthropicService(db=db, cliente_id=cliente_id_teste)
        ai_available = ai_service.use_real_ai
    except:
        ai_available = False

    return {
        "status": "active",
        "multi_tenant": True,
        "ai_configured": bool(os.getenv('ANTHROPIC_API_KEY')),
        "ai_available": ai_available,
        "model": "claude-3.5-sonnet-20241022",
        "cliente_id_teste": cliente_id_teste,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/whatsapp/clear/{phone}")
async def clear_conversation(phone: str, request: Request):
    """Limpa histórico de conversa de um número"""
    if not verify_webhook_auth(request):
        raise HTTPException(status_code=401, detail="Nao autorizado")
    success = conversation_manager.clear_context(phone)
    if success:
        return {"status": "cleared", "phone": phone, "storage": "redis" if conversation_manager.redis_client else "memory"}
    return {"status": "error", "phone": phone}


@router.get("/whatsapp/conversations")
async def list_conversations(request: Request):
    """Lista todas as conversas ativas"""
    if not verify_webhook_auth(request):
        raise HTTPException(status_code=401, detail="Nao autorizado")
    phones = conversation_manager.get_all_active_conversations()
    return {
        "status": "success",
        "count": len(phones),
        "conversations": phones,
        "storage": "redis" if conversation_manager.redis_client else "memory"
    }
