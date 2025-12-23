"""
Gerenciador de Contexto de Conversas
Sistema de agendamento médico SaaS - Pro-Saúde
Desenvolvido por Marco
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class ConversationManager:
    """Gerencia contexto de conversas com persistência em Redis ou memória."""

    def __init__(self):
        """Inicializa o gerenciador de conversas."""
        self.redis_client = None
        self.memory_storage: Dict[str, List[Dict]] = {}

        # Tentar conectar ao Redis
        if REDIS_AVAILABLE:
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Testar conexão
                self.redis_client.ping()
                logger.info("✅ ConversationManager conectado ao Redis")
            except Exception as e:
                logger.warning(f"⚠️ Redis indisponível, usando memória local: {e}")
                self.redis_client = None
        else:
            logger.warning("⚠️ Redis não instalado, usando memória local")

    def _get_key(self, phone: str, cliente_id: Optional[int] = None) -> str:
        """
        Gera chave para armazenamento com namespace por cliente (MULTI-TENANT)

        Args:
            phone: Telefone do usuário
            cliente_id: ID do cliente (tenant)

        Returns:
            Chave formatada: conversation:cliente_X:5511999999999
        """
        if cliente_id:
            return f"conversation:cliente_{cliente_id}:{phone}"
        # Fallback para clientes antigos sem tenant
        return f"conversation:{phone}"

    def get_context(self, phone: str, limit: int = 10, cliente_id: Optional[int] = None) -> List[Dict]:
        """
        Obtém contexto da conversa (MULTI-TENANT)

        Args:
            phone: Telefone do usuário
            limit: Número máximo de mensagens a retornar
            cliente_id: ID do cliente (tenant) - NOVO

        Returns:
            Lista com histórico de mensagens
        """
        if self.redis_client:
            try:
                key = self._get_key(phone, cliente_id)
                data = self.redis_client.get(key)

                if data:
                    messages = json.loads(data)
                    tenant_info = f" (cliente_{cliente_id})" if cliente_id else ""
                    logger.info(f"📥 Contexto carregado do Redis para {phone}{tenant_info}: {len(messages)} mensagens")
                    return messages[-limit:]  # Retorna últimas N mensagens

                logger.info(f"📝 Novo contexto criado para {phone}")
                return []

            except Exception as e:
                logger.error(f"❌ Erro ao ler do Redis: {e}")
                # Fallback para memória
                return self.memory_storage.get(phone, [])[-limit:]
        else:
            # Usar memória local
            return self.memory_storage.get(phone, [])[-limit:]

    def add_message(self, phone: str, message_type: str, text: str,
                    intencao: Optional[str] = None, dados_coletados: Optional[Dict] = None,
                    cliente_id: Optional[int] = None):
        """
        Adiciona mensagem ao contexto.

        Args:
            phone: Telefone do usuário
            message_type: Tipo da mensagem ('user' ou 'assistant')
            text: Texto da mensagem
            intencao: Intenção detectada (opcional)
            dados_coletados: Dados coletados na conversa (opcional)
        """
        message = {
            "tipo": message_type,
            "texto": text,
            "timestamp": datetime.now().isoformat()
        }

        if intencao:
            message["intencao"] = intencao

        if dados_coletados:
            message["dados_coletados"] = dados_coletados

        if self.redis_client:
            try:
                key = self._get_key(phone, cliente_id)

                # Obter contexto atual
                data = self.redis_client.get(key)
                messages = json.loads(data) if data else []

                # Adicionar nova mensagem
                messages.append(message)

                # Limitar a 20 mensagens (últimas 10 trocas)
                if len(messages) > 20:
                    messages = messages[-20:]

                # Salvar no Redis com expiração de 24 horas
                self.redis_client.setex(
                    key,
                    timedelta(hours=24),
                    json.dumps(messages, ensure_ascii=False)
                )

                tenant_info = f" (cliente_{cliente_id})" if cliente_id else ""
                logger.info(f"💾 Mensagem salva no Redis para {phone}{tenant_info} (total: {len(messages)})")

            except Exception as e:
                logger.error(f"❌ Erro ao salvar no Redis: {e}")
                # Fallback para memória
                if phone not in self.memory_storage:
                    self.memory_storage[phone] = []
                self.memory_storage[phone].append(message)
                if len(self.memory_storage[phone]) > 20:
                    self.memory_storage[phone] = self.memory_storage[phone][-20:]
        else:
            # Usar memória local
            if phone not in self.memory_storage:
                self.memory_storage[phone] = []
            self.memory_storage[phone].append(message)
            if len(self.memory_storage[phone]) > 20:
                self.memory_storage[phone] = self.memory_storage[phone][-20:]

            logger.info(f"💾 Mensagem salva em memória para {phone}")

    def clear_context(self, phone: str, cliente_id: Optional[int] = None) -> bool:
        """
        Limpa contexto de conversa (MULTI-TENANT)

        Args:
            phone: Telefone do usuário
            cliente_id: ID do cliente (tenant) - NOVO

        Returns:
            True se limpou com sucesso
        """
        if self.redis_client:
            try:
                key = self._get_key(phone, cliente_id)
                self.redis_client.delete(key)
                tenant_info = f" (cliente_{cliente_id})" if cliente_id else ""
                logger.info(f"🗑️ Contexto limpo do Redis para {phone}{tenant_info}")
                return True
            except Exception as e:
                logger.error(f"❌ Erro ao limpar Redis: {e}")
                if phone in self.memory_storage:
                    del self.memory_storage[phone]
                return False
        else:
            if phone in self.memory_storage:
                del self.memory_storage[phone]
                logger.info(f"🗑️ Contexto limpo da memória para {phone}")
            return True

    def get_all_active_conversations(self) -> List[str]:
        """
        Retorna lista de telefones com conversas ativas.

        Returns:
            Lista de telefones
        """
        if self.redis_client:
            try:
                keys = self.redis_client.keys("conversation:*")
                phones = [k.replace("conversation:", "") for k in keys]
                return phones
            except Exception as e:
                logger.error(f"❌ Erro ao listar conversas: {e}")
                return list(self.memory_storage.keys())
        else:
            return list(self.memory_storage.keys())


# Instância global do gerenciador
conversation_manager = ConversationManager()
