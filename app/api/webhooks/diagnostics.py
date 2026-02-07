"""
Diagnostic endpoints: test, clear, conversations, status
"""
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
import logging
import os

from app.database import SessionLocal
from app.services.anthropic_service import AnthropicService
from app.services.conversation_manager import conversation_manager

from app.api.webhooks.utils import verify_webhook_auth

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/whatsapp/test")
async def test_webhook(request: Request):
    """Endpoint de teste - usa cliente padrão"""
    if not verify_webhook_auth(request):
        raise HTTPException(status_code=401, detail="Nao autorizado")
    cliente_id_teste = 1  # Cliente padrão para testes

    # Testar conexão com banco
    db = SessionLocal()
    try:
        ai_service = AnthropicService(db=db, cliente_id=cliente_id_teste)
        ai_available = ai_service.use_real_ai
    except:
        ai_available = False
    finally:
        db.close()

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


@router.get("/whatsapp/status")
async def whatsapp_status(request: Request):
    """Retorna status da conexão WhatsApp de todas as instâncias"""
    if not verify_webhook_auth(request):
        raise HTTPException(status_code=401, detail="Nao autorizado")
    try:
        from app.services.whatsapp_monitor import whatsapp_monitor

        stats = await whatsapp_monitor.verificar_todas_instancias()

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        logger.error(f"❌ Erro ao verificar status: {e}")
        return {
            "success": False,
            "error": str(e)
        }
