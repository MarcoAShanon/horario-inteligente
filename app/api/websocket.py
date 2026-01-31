"""
Endpoint WebSocket para notificações em tempo real
Horário Inteligente SaaS

Permite que o painel de atendimento receba atualizações instantâneas.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import logging
import jwt
from app.services.websocket_manager import websocket_manager
import os

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("ERRO CRITICO: SECRET_KEY nao configurada. Defina a variavel de ambiente SECRET_KEY no arquivo .env")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


async def get_user_from_token(token: str):
    """Valida token JWT e retorna dados do usuário"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@router.websocket("/ws/conversas")
async def websocket_conversas(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket para receber atualizações de conversas em tempo real.

    Conexão: ws://dominio/ws/conversas?token=JWT_TOKEN

    Eventos recebidos:
    - nova_mensagem: { tipo, conversa_id, mensagem }
    - conversa_atualizada: { tipo, conversa_id, status }
    - nova_conversa: { tipo, conversa }
    """

    # Validar token
    if not token:
        await websocket.close(code=4001, reason="Token não fornecido")
        return

    user_data = await get_user_from_token(token)
    if not user_data:
        await websocket.close(code=4002, reason="Token inválido ou expirado")
        return

    cliente_id = user_data.get("cliente_id")
    if not cliente_id:
        await websocket.close(code=4003, reason="cliente_id não encontrado no token")
        return

    # Conectar
    await websocket_manager.connect(websocket, cliente_id)

    try:
        # Enviar confirmação de conexão
        await websocket.send_json({
            "tipo": "conectado",
            "cliente_id": cliente_id,
            "message": "Conexão WebSocket estabelecida"
        })

        # Manter conexão aberta e processar mensagens do cliente (se houver)
        while True:
            try:
                # Aguarda mensagens do cliente (ping/pong, etc)
                data = await websocket.receive_text()

                # Processar comandos do cliente se necessário
                try:
                    message = json.loads(data)
                    if message.get("tipo") == "ping":
                        await websocket.send_json({"tipo": "pong"})
                except json.JSONDecodeError:
                    pass

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
    finally:
        websocket_manager.disconnect(websocket, cliente_id)


@router.get("/ws/status")
async def websocket_status():
    """Retorna status das conexões WebSocket (para debug)"""
    return {
        "active_tenants": list(websocket_manager.active_connections.keys()),
        "total_connections": sum(
            len(conns) for conns in websocket_manager.active_connections.values()
        )
    }
