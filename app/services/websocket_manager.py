"""
Gerenciador de WebSocket para notificações em tempo real
Horário Inteligente SaaS

Permite notificar painéis de atendimento sobre novas mensagens e atualizações.
"""

from fastapi import WebSocket
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Gerenciador de conexões WebSocket por tenant (cliente)"""

    def __init__(self):
        # Dict de cliente_id -> Set de WebSockets conectados
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, cliente_id: int):
        """Aceita conexão e adiciona à lista do tenant"""
        await websocket.accept()
        if cliente_id not in self.active_connections:
            self.active_connections[cliente_id] = set()
        self.active_connections[cliente_id].add(websocket)
        logger.info(f"WebSocket conectado para cliente {cliente_id}. Total: {len(self.active_connections[cliente_id])}")

    def disconnect(self, websocket: WebSocket, cliente_id: int):
        """Remove conexão da lista"""
        if cliente_id in self.active_connections:
            self.active_connections[cliente_id].discard(websocket)
            if not self.active_connections[cliente_id]:
                del self.active_connections[cliente_id]
        logger.info(f"WebSocket desconectado para cliente {cliente_id}")

    async def broadcast_to_tenant(self, cliente_id: int, message: dict):
        """Envia mensagem para todos os WebSockets de um tenant"""
        if cliente_id not in self.active_connections:
            logger.debug(f"[WebSocket] Cliente {cliente_id} não tem conexões ativas")
            return

        logger.debug(f"[WebSocket] Broadcast para {len(self.active_connections[cliente_id])} conexões do cliente {cliente_id}")

        dead_connections = set()
        message_json = json.dumps(message, default=str)

        for websocket in self.active_connections[cliente_id]:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Erro ao enviar WebSocket: {e}")
                dead_connections.add(websocket)

        # Remover conexões mortas
        for dead in dead_connections:
            self.active_connections[cliente_id].discard(dead)

    async def send_nova_mensagem(self, cliente_id: int, conversa_id: int, mensagem: dict):
        """Notifica nova mensagem em uma conversa"""
        connections = self.get_connection_count(cliente_id)
        logger.info(f"[WebSocket] Notificando nova_mensagem para cliente {cliente_id} (conversa {conversa_id}) - {connections} conexões ativas")

        if connections == 0:
            logger.warning(f"[WebSocket] Nenhuma conexão ativa para cliente {cliente_id}. Mensagem não será entregue em tempo real.")
            return

        await self.broadcast_to_tenant(cliente_id, {
            "tipo": "nova_mensagem",
            "conversa_id": conversa_id,
            "mensagem": mensagem
        })
        logger.info(f"[WebSocket] Mensagem broadcast enviada com sucesso")

    async def send_conversa_atualizada(self, cliente_id: int, conversa_id: int, status: str):
        """Notifica mudança de status de uma conversa"""
        await self.broadcast_to_tenant(cliente_id, {
            "tipo": "conversa_atualizada",
            "conversa_id": conversa_id,
            "status": status
        })

    async def send_nova_conversa(self, cliente_id: int, conversa: dict):
        """Notifica nova conversa criada"""
        await self.broadcast_to_tenant(cliente_id, {
            "tipo": "nova_conversa",
            "conversa": conversa
        })

    def get_connection_count(self, cliente_id: int) -> int:
        """Retorna número de conexões ativas para um tenant"""
        return len(self.active_connections.get(cliente_id, set()))


# Instância global (singleton)
websocket_manager = WebSocketManager()
