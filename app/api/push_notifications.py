"""
API de Push Notifications
Horário Inteligente SaaS

Endpoints para gerenciar subscriptions de push notifications.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.api.auth import get_current_user
from app.services.push_notification_service import push_service

router = APIRouter(prefix="/api/push", tags=["Push Notifications"])


# ==================== SCHEMAS ====================

class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class SubscriptionRequest(BaseModel):
    endpoint: str
    keys: SubscriptionKeys


class UnsubscribeRequest(BaseModel):
    endpoint: str


# ==================== ENDPOINTS ====================

@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """
    Retorna a chave pública VAPID para o frontend configurar o push.

    Esta chave é necessária para o navegador criar a subscription.
    """
    public_key = push_service.get_public_key()
    if not public_key:
        raise HTTPException(
            status_code=500,
            detail="VAPID keys não configuradas no servidor"
        )
    return {"publicKey": public_key}


@router.post("/subscribe")
async def subscribe(
    subscription: SubscriptionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Registra subscription do usuário para receber push notifications.

    - Médicos e secretárias podem se inscrever
    - Múltiplas subscriptions por usuário são permitidas (diferentes dispositivos)
    """
    user_type = current_user.get("tipo")
    user_id = current_user.get("id")

    # Apenas médicos podem receber notificações de agendamento por enquanto
    # Secretárias podem ser adicionadas futuramente
    if user_type != "medico":
        raise HTTPException(
            status_code=403,
            detail="Apenas médicos podem receber notificações de agendamento"
        )

    # Obter user-agent para identificar dispositivo
    user_agent = request.headers.get("user-agent", "")[:500]

    result = await push_service.save_subscription(
        db=db,
        medico_id=user_id,
        subscription_info={
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.keys.p256dh,
                "auth": subscription.keys.auth
            }
        },
        user_agent=user_agent
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Erro ao salvar subscription"))

    return {"success": True, "message": "Notificações ativadas com sucesso!"}


@router.post("/unsubscribe")
async def unsubscribe(
    data: UnsubscribeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove subscription (desativa notificações).
    """
    result = await push_service.remove_subscription(db, data.endpoint)
    return {"success": result, "message": "Notificações desativadas" if result else "Subscription não encontrada"}


@router.post("/test")
async def test_notification(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Envia notificação de teste para o usuário logado.

    Útil para verificar se as notificações estão funcionando.
    """
    user_type = current_user.get("tipo")
    user_id = current_user.get("id")

    if user_type != "medico":
        raise HTTPException(
            status_code=403,
            detail="Apenas médicos podem testar notificações"
        )

    result = await push_service.send_notification(
        db=db,
        medico_id=user_id,
        title="🔔 Teste de Notificação",
        body="As notificações estão funcionando perfeitamente!",
        url="/static/dashboard.html",
        tag="test"
    )

    if result.get("sent", 0) == 0:
        if result.get("reason") == "no_subscriptions":
            return {
                "success": False,
                "message": "Nenhum dispositivo cadastrado. Ative as notificações primeiro.",
                **result
            }
        return {"success": False, "message": "Erro ao enviar notificação", **result}

    return {"success": True, "message": f"Notificação enviada para {result['sent']} dispositivo(s)!", **result}


@router.get("/status")
async def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retorna status das subscriptions do usuário.
    """
    user_type = current_user.get("tipo")
    user_id = current_user.get("id")

    if user_type != "medico":
        return {"subscriptions": 0, "enabled": False}

    count = push_service.get_subscription_count(db, user_id)
    return {
        "subscriptions": count,
        "enabled": count > 0
    }
