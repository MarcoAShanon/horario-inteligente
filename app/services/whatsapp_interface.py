"""
Interface comum para provedores de WhatsApp
Permite trocar entre Evolution API e API Oficial sem mudar o resto do código
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class WhatsAppProvider(Enum):
    """Provedores de WhatsApp disponíveis"""
    EVOLUTION = "evolution"
    OFFICIAL = "official"


@dataclass
class WhatsAppMessage:
    """Estrutura padronizada de mensagem recebida"""
    sender: str                    # Número do remetente (ex: 5521999999999)
    text: str                      # Texto da mensagem (ou transcrição de áudio)
    message_type: str              # text, audio, image, interactive
    push_name: str                 # Nome do contato no WhatsApp
    message_id: str                # ID único da mensagem
    timestamp: int                 # Unix timestamp
    is_from_me: bool               # Se foi enviada pelo bot
    # Campos opcionais
    audio_url: Optional[str] = None
    audio_media_key: Optional[str] = None
    image_url: Optional[str] = None
    button_reply_id: Optional[str] = None      # ID do botão clicado
    list_reply_id: Optional[str] = None        # ID do item de lista selecionado
    raw_data: Optional[Dict] = None            # Dados brutos originais
    # Multi-tenant - identificação do número que recebeu
    phone_number_id: Optional[str] = None         # ID do número da clínica (Meta)
    display_phone_number: Optional[str] = None    # Número formatado da clínica


@dataclass
class InteractiveButton:
    """Botão para mensagens interativas"""
    id: str
    title: str  # Máximo 20 caracteres


@dataclass
class ListRow:
    """Item de lista para mensagens interativas"""
    id: str
    title: str           # Máximo 24 caracteres
    description: str = ""  # Máximo 72 caracteres


@dataclass
class ListSection:
    """Seção de lista para mensagens interativas"""
    title: str
    rows: List[ListRow]


@dataclass
class SendResult:
    """Resultado do envio de mensagem"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


class WhatsAppProviderInterface(ABC):
    """
    Interface abstrata para provedores de WhatsApp.
    Tanto Evolution API quanto API Oficial devem implementar esta interface.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provedor (evolution/official)"""
        pass

    # ==================== ENVIO DE MENSAGENS ====================

    @abstractmethod
    async def send_text(
        self,
        to: str,
        message: str,
        instance: Optional[str] = None
    ) -> SendResult:
        """
        Envia mensagem de texto simples.

        Args:
            to: Número do destinatário (ex: 5521999999999)
            message: Texto da mensagem
            instance: Nome da instância (para multi-tenant)

        Returns:
            SendResult com status do envio
        """
        pass

    @abstractmethod
    async def send_interactive_buttons(
        self,
        to: str,
        text: str,
        buttons: List[InteractiveButton],
        header: Optional[str] = None,
        footer: Optional[str] = None,
        instance: Optional[str] = None
    ) -> SendResult:
        """
        Envia mensagem com botões de resposta rápida (máximo 3).

        Args:
            to: Número do destinatário
            text: Corpo da mensagem
            buttons: Lista de botões (máximo 3)
            header: Cabeçalho opcional
            footer: Rodapé opcional
            instance: Nome da instância

        Returns:
            SendResult com status do envio
        """
        pass

    @abstractmethod
    async def send_interactive_list(
        self,
        to: str,
        text: str,
        button_text: str,
        sections: List[ListSection],
        header: Optional[str] = None,
        footer: Optional[str] = None,
        instance: Optional[str] = None
    ) -> SendResult:
        """
        Envia mensagem com lista de opções (máximo 10 itens total).

        Args:
            to: Número do destinatário
            text: Corpo da mensagem
            button_text: Texto do botão que abre a lista
            sections: Seções com itens da lista
            header: Cabeçalho opcional
            footer: Rodapé opcional
            instance: Nome da instância

        Returns:
            SendResult com status do envio
        """
        pass

    @abstractmethod
    async def send_audio(
        self,
        to: str,
        audio_url: Optional[str] = None,
        audio_base64: Optional[str] = None,
        instance: Optional[str] = None
    ) -> SendResult:
        """
        Envia mensagem de áudio.

        Args:
            to: Número do destinatário
            audio_url: URL do áudio (opcional)
            audio_base64: Áudio em base64 (opcional)
            instance: Nome da instância

        Returns:
            SendResult com status do envio
        """
        pass

    @abstractmethod
    async def send_image(
        self,
        to: str,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        caption: Optional[str] = None,
        instance: Optional[str] = None
    ) -> SendResult:
        """
        Envia imagem.

        Args:
            to: Número do destinatário
            image_url: URL da imagem (opcional)
            image_base64: Imagem em base64 (opcional)
            caption: Legenda opcional
            instance: Nome da instância

        Returns:
            SendResult com status do envio
        """
        pass

    # ==================== PARSING DE WEBHOOK ====================

    @abstractmethod
    def parse_webhook(self, webhook_data: Dict[str, Any]) -> Optional[WhatsAppMessage]:
        """
        Converte dados do webhook para formato padronizado.

        Args:
            webhook_data: Dados brutos recebidos no webhook

        Returns:
            WhatsAppMessage padronizado ou None se não for mensagem válida
        """
        pass

    @abstractmethod
    def is_valid_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Verifica se o webhook contém uma mensagem válida para processar.

        Args:
            webhook_data: Dados brutos do webhook

        Returns:
            True se deve ser processado, False caso contrário
        """
        pass

    # ==================== STATUS E CONEXÃO ====================

    @abstractmethod
    async def get_connection_status(self, instance: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifica status da conexão.

        Args:
            instance: Nome da instância

        Returns:
            Dict com status (connected, disconnected, etc)
        """
        pass

    @abstractmethod
    async def is_connected(self, instance: Optional[str] = None) -> bool:
        """
        Verifica se está conectado.

        Args:
            instance: Nome da instância

        Returns:
            True se conectado
        """
        pass


def get_whatsapp_provider(provider: WhatsAppProvider = None) -> WhatsAppProviderInterface:
    """
    Factory para obter o provedor de WhatsApp configurado.

    Args:
        provider: Provedor específico (opcional, usa config padrão se não informado)

    Returns:
        Instância do provedor de WhatsApp
    """
    import os

    if provider is None:
        # Usar configuração do ambiente
        provider_name = os.getenv("WHATSAPP_PROVIDER", "evolution").lower()
        provider = WhatsAppProvider(provider_name)

    if provider == WhatsAppProvider.OFFICIAL:
        from app.services.whatsapp_official_service import WhatsAppOfficialService
        return WhatsAppOfficialService()
    else:
        from app.services.whatsapp_evolution_service import WhatsAppEvolutionService
        return WhatsAppEvolutionService()
