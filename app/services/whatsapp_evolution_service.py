"""
Serviço de integração com Evolution API (adaptado para interface comum)
Mantém compatibilidade com código existente
"""

import os
import re
import httpx
from typing import Dict, Any, List, Optional

from app.services.whatsapp_interface import (
    WhatsAppProviderInterface,
    WhatsAppMessage,
    InteractiveButton,
    ListSection,
    SendResult
)


class WhatsAppEvolutionService(WhatsAppProviderInterface):
    """
    Cliente para Evolution API.
    Implementa a interface comum WhatsAppProviderInterface.

    Configuração necessária no .env:
        EVOLUTION_API_URL=http://localhost:8080
        EVOLUTION_API_KEY=sua_api_key
    """

    def __init__(self):
        self.evolution_url = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
        self.api_key = os.getenv("EVOLUTION_API_KEY", "")
        self.default_instance = os.getenv("EVOLUTION_DEFAULT_INSTANCE", "ProSaude")

        self.headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

    @property
    def provider_name(self) -> str:
        return "evolution"

    def _format_phone(self, phone: str) -> str:
        """Formata número de telefone."""
        # Remove @s.whatsapp.net se existir
        if '@' in phone:
            phone = phone.split('@')[0]

        # Remove caracteres não numéricos
        phone_clean = ''.join(filter(str.isdigit, phone))

        # Adiciona código do país se não tiver
        if len(phone_clean) <= 11 and not phone_clean.startswith('55'):
            phone_clean = '55' + phone_clean

        return phone_clean

    def _get_instance(self, instance: Optional[str]) -> str:
        """Retorna a instância a ser usada."""
        return instance or self.default_instance

    # ==================== ENVIO DE MENSAGENS ====================

    async def send_text(
        self,
        to: str,
        message: str,
        instance: Optional[str] = None
    ) -> SendResult:
        """Envia mensagem de texto simples."""

        inst = self._get_instance(instance)
        url = f"{self.evolution_url}/message/sendText/{inst}"

        payload = {
            "number": self._format_phone(to),
            "text": message,
            "options": {
                "delay": 1200,
                "presence": "composing"
            }
        }

        return await self._send_request(url, payload)

    async def send_interactive_buttons(
        self,
        to: str,
        text: str,
        buttons: List[InteractiveButton],
        header: Optional[str] = None,
        footer: Optional[str] = None,
        instance: Optional[str] = None
    ) -> SendResult:
        """Envia mensagem com botões."""

        inst = self._get_instance(instance)
        url = f"{self.evolution_url}/message/sendButtons/{inst}"

        # Evolution API tem formato diferente para botões
        button_list = [
            {
                "buttonId": btn.id,
                "buttonText": {"displayText": btn.title}
            }
            for btn in buttons[:3]  # Máximo 3 botões
        ]

        payload = {
            "number": self._format_phone(to),
            "title": header or "",
            "description": text,
            "footer": footer or "",
            "buttons": button_list
        }

        return await self._send_request(url, payload)

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
        """Envia mensagem com lista de opções."""

        inst = self._get_instance(instance)
        url = f"{self.evolution_url}/message/sendList/{inst}"

        # Converte para formato Evolution
        section_list = [
            {
                "title": section.title,
                "rows": [
                    {
                        "rowId": row.id,
                        "title": row.title,
                        "description": row.description or ""
                    }
                    for row in section.rows
                ]
            }
            for section in sections
        ]

        payload = {
            "number": self._format_phone(to),
            "title": header or "Opções",
            "description": text,
            "buttonText": button_text,
            "footer": footer or "",
            "sections": section_list
        }

        return await self._send_request(url, payload)

    async def send_audio(
        self,
        to: str,
        audio_url: Optional[str] = None,
        audio_base64: Optional[str] = None,
        instance: Optional[str] = None
    ) -> SendResult:
        """Envia mensagem de áudio."""

        inst = self._get_instance(instance)
        url = f"{self.evolution_url}/message/sendMedia/{inst}"

        if audio_base64:
            payload = {
                "number": self._format_phone(to),
                "mediatype": "audio",
                "media": audio_base64,
                "fileName": "audio.mp3"
            }
        elif audio_url:
            payload = {
                "number": self._format_phone(to),
                "mediatype": "audio",
                "media": audio_url
            }
        else:
            return SendResult(success=False, error="Nenhum áudio fornecido")

        return await self._send_request(url, payload)

    async def send_image(
        self,
        to: str,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        caption: Optional[str] = None,
        instance: Optional[str] = None
    ) -> SendResult:
        """Envia imagem."""

        inst = self._get_instance(instance)
        url = f"{self.evolution_url}/message/sendMedia/{inst}"

        payload = {
            "number": self._format_phone(to),
            "mediatype": "image",
            "caption": caption or ""
        }

        if image_base64:
            payload["media"] = image_base64
        elif image_url:
            payload["media"] = image_url
        else:
            return SendResult(success=False, error="Nenhuma imagem fornecida")

        return await self._send_request(url, payload)

    # ==================== MÉTODOS AUXILIARES ====================

    async def _send_request(self, url: str, payload: Dict) -> SendResult:
        """Envia requisição para a Evolution API."""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)

                data = response.json() if response.text else {}

                if response.status_code in [200, 201]:
                    message_id = data.get("key", {}).get("id") or data.get("messageId")
                    return SendResult(
                        success=True,
                        message_id=message_id,
                        raw_response=data
                    )
                else:
                    error_msg = data.get("message") or data.get("error") or "Erro desconhecido"
                    print(f"[Evolution API] Erro: {error_msg}")
                    return SendResult(
                        success=False,
                        error=error_msg,
                        raw_response=data
                    )

        except Exception as e:
            print(f"[Evolution API] Exceção: {e}")
            return SendResult(success=False, error=str(e))

    # ==================== PARSING DE WEBHOOK ====================

    def parse_webhook(self, webhook_data: Dict[str, Any]) -> Optional[WhatsAppMessage]:
        """
        Converte webhook da Evolution API para formato padronizado.

        Formato de entrada (Evolution API v2):
        {
            "event": "messages.upsert",
            "instance": "ProSaude",
            "data": {
                "key": {
                    "remoteJid": "5521999999999@s.whatsapp.net",
                    "fromMe": false,
                    "id": "ABC123"
                },
                "message": {
                    "conversation": "texto da mensagem"
                },
                "messageType": "text",
                "pushName": "Nome do Usuário"
            }
        }
        """

        try:
            event = webhook_data.get("event", "")
            data = webhook_data.get("data", {})

            # Ignora eventos que não são mensagens
            if event != "messages.upsert":
                return None

            key = data.get("key", {})
            message_content = data.get("message", {})

            # Extrai informações básicas
            remote_jid = key.get("remoteJid", "")
            sender = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
            message_id = key.get("id", "")
            is_from_me = key.get("fromMe", False)
            push_name = data.get("pushName", "")
            msg_type = data.get("messageType", "text")

            # Ignora mensagens enviadas por nós
            if is_from_me:
                return None

            # Extrai texto baseado no tipo
            text = ""
            audio_url = None
            audio_media_key = None
            image_url = None
            button_reply_id = None
            list_reply_id = None

            if msg_type == "conversation" or msg_type == "text":
                text = message_content.get("conversation", "") or \
                       message_content.get("extendedTextMessage", {}).get("text", "")

            elif msg_type == "extendedTextMessage":
                text = message_content.get("extendedTextMessage", {}).get("text", "")

            elif msg_type in ["audioMessage", "ptt"]:
                audio_msg = message_content.get("audioMessage", {})
                audio_url = audio_msg.get("url", "")
                audio_media_key = audio_msg.get("mediaKey", "")
                text = "[Áudio recebido]"

            elif msg_type == "imageMessage":
                image_msg = message_content.get("imageMessage", {})
                image_url = image_msg.get("url", "")
                text = image_msg.get("caption", "[Imagem recebida]")

            elif msg_type == "buttonsResponseMessage":
                btn_response = message_content.get("buttonsResponseMessage", {})
                button_reply_id = btn_response.get("selectedButtonId", "")
                text = btn_response.get("selectedDisplayText", "")

            elif msg_type == "listResponseMessage":
                list_response = message_content.get("listResponseMessage", {})
                list_reply_id = list_response.get("singleSelectReply", {}).get("selectedRowId", "")
                text = list_response.get("title", "")

            # Se não conseguiu extrair texto, tenta outros campos
            if not text:
                for possible_field in ["conversation", "text", "caption"]:
                    if possible_field in message_content:
                        text = message_content[possible_field]
                        break

            return WhatsAppMessage(
                sender=sender,
                text=text,
                message_type=msg_type,
                push_name=push_name,
                message_id=message_id,
                timestamp=int(data.get("messageTimestamp", 0)),
                is_from_me=is_from_me,
                audio_url=audio_url,
                audio_media_key=audio_media_key,
                image_url=image_url,
                button_reply_id=button_reply_id,
                list_reply_id=list_reply_id,
                raw_data=webhook_data
            )

        except Exception as e:
            print(f"[Evolution API] Erro parsing webhook: {e}")
            return None

    def is_valid_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Verifica se o webhook contém mensagem válida."""

        try:
            event = webhook_data.get("event", "")
            data = webhook_data.get("data", {})
            key = data.get("key", {})

            # Deve ser evento de mensagem
            if event != "messages.upsert":
                return False

            # Não deve ser mensagem nossa
            if key.get("fromMe", False):
                return False

            # Deve ter remoteJid
            if not key.get("remoteJid"):
                return False

            # Deve ser de usuário (não grupo)
            remote_jid = key.get("remoteJid", "")
            if "@g.us" in remote_jid:  # Ignora grupos
                return False

            return True

        except Exception:
            return False

    # ==================== STATUS E CONEXÃO ====================

    async def get_connection_status(self, instance: Optional[str] = None) -> Dict[str, Any]:
        """Verifica status da conexão."""

        inst = self._get_instance(instance)
        url = f"{self.evolution_url}/instance/connectionState/{inst}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 200:
                    data = response.json()
                    state = data.get("instance", {}).get("state", "unknown")
                    return {
                        "status": "connected" if state == "open" else state,
                        "instance": inst,
                        "raw": data
                    }
                else:
                    return {
                        "status": "error",
                        "error": response.text
                    }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def is_connected(self, instance: Optional[str] = None) -> bool:
        """Verifica se está conectado."""
        status = await self.get_connection_status(instance)
        return status.get("status") == "connected"

    # ==================== MÉTODOS ESPECÍFICOS EVOLUTION ====================

    async def get_qr_code(self, instance: Optional[str] = None) -> Optional[str]:
        """Obtém QR Code para conexão."""

        inst = self._get_instance(instance)
        url = f"{self.evolution_url}/instance/connect/{inst}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 200:
                    data = response.json()
                    return data.get("base64") or data.get("qrcode", {}).get("base64")

        except Exception as e:
            print(f"[Evolution API] Erro ao obter QR: {e}")

        return None

    async def create_instance(
        self,
        instance_name: str,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cria nova instância."""

        url = f"{self.evolution_url}/instance/create"

        payload = {
            "instanceName": instance_name,
            "integration": "WHATSAPP-BAILEYS"
        }

        if webhook_url:
            payload["webhook_wa_business"] = {
                "url": webhook_url,
                "enabled": True,
                "events": ["MESSAGE_RECEIVED", "MESSAGE_SENT", "CONNECTION_UPDATE"]
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                return response.json()

        except Exception as e:
            return {"error": str(e)}

    async def download_media_base64(
        self,
        instance: str,
        message_data: Dict
    ) -> Optional[str]:
        """Baixa mídia e retorna em base64."""

        url = f"{self.evolution_url}/chat/getBase64FromMediaMessage/{instance}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=self.headers, json={"message": message_data})

                if response.status_code == 200:
                    data = response.json()
                    return data.get("base64")

        except Exception as e:
            print(f"[Evolution API] Erro ao baixar mídia: {e}")

        return None
