"""
Serviço de integração com WhatsApp Business API Oficial (Meta Cloud API)
Desenvolvido para migração do Evolution API
"""

import os
import json
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.whatsapp_interface import (
    WhatsAppProviderInterface,
    WhatsAppMessage,
    InteractiveButton,
    ListSection,
    SendResult
)


class WhatsAppOfficialService(WhatsAppProviderInterface):
    """
    Cliente para WhatsApp Business Cloud API (Meta).

    Documentação: https://developers.facebook.com/docs/whatsapp/cloud-api

    Configuração necessária no .env:
        WHATSAPP_ACCESS_TOKEN=EAAG...
        WHATSAPP_PHONE_ID=123456789012345
        WHATSAPP_BUSINESS_ACCOUNT_ID=987654321098765
        WHATSAPP_WEBHOOK_VERIFY_TOKEN=seu_token_secreto
        WHATSAPP_API_VERSION=v21.0
    """

    def __init__(self):
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_id = os.getenv("WHATSAPP_PHONE_ID")
        self.business_account_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
        self.verify_token = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN")
        self.api_version = os.getenv("WHATSAPP_API_VERSION", "v21.0")

        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.messages_url = f"{self.base_url}/{self.phone_id}/messages"

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    @property
    def provider_name(self) -> str:
        return "official"

    def _format_phone(self, phone: str) -> str:
        """
        Formata número de telefone para o padrão da API.
        Remove caracteres especiais, mantém apenas números.
        """
        # Remove tudo que não é número
        phone_clean = ''.join(filter(str.isdigit, phone))

        # Remove @s.whatsapp.net se existir
        if '@' in phone:
            phone_clean = phone.split('@')[0]
            phone_clean = ''.join(filter(str.isdigit, phone_clean))

        # Adiciona código do país se não tiver
        if len(phone_clean) <= 11 and not phone_clean.startswith('55'):
            phone_clean = '55' + phone_clean

        return phone_clean

    # ==================== ENVIO DE MENSAGENS ====================

    async def send_text(
        self,
        to: str,
        message: str,
        instance: Optional[str] = None,  # Ignorado na API oficial
        phone_number_id: Optional[str] = None  # Multi-tenant: ID do número WhatsApp do cliente
    ) -> SendResult:
        """Envia mensagem de texto simples."""

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._format_phone(to),
            "type": "text",
            "text": {
                "preview_url": True,
                "body": message
            }
        }

        return await self._send_request(payload, phone_number_id)

    async def send_interactive_buttons(
        self,
        to: str,
        text: str,
        buttons: List[InteractiveButton],
        header: Optional[str] = None,
        footer: Optional[str] = None,
        instance: Optional[str] = None,
        phone_number_id: Optional[str] = None  # Multi-tenant: ID do número WhatsApp do cliente
    ) -> SendResult:
        """
        Envia mensagem com botões de resposta rápida.
        Máximo de 3 botões.
        """

        if len(buttons) > 3:
            buttons = buttons[:3]  # API permite máximo 3 botões

        interactive = {
            "type": "button",
            "body": {
                "text": text
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": btn.id,
                            "title": btn.title[:20]  # Máximo 20 caracteres
                        }
                    }
                    for btn in buttons
                ]
            }
        }

        # Adiciona header se fornecido
        if header:
            interactive["header"] = {
                "type": "text",
                "text": header
            }

        # Adiciona footer se fornecido
        if footer:
            interactive["footer"] = {
                "text": footer
            }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._format_phone(to),
            "type": "interactive",
            "interactive": interactive
        }

        return await self._send_request(payload, phone_number_id)

    async def send_interactive_list(
        self,
        to: str,
        text: str,
        button_text: str,
        sections: List[ListSection],
        header: Optional[str] = None,
        footer: Optional[str] = None,
        instance: Optional[str] = None,
        phone_number_id: Optional[str] = None  # Multi-tenant: ID do número WhatsApp do cliente
    ) -> SendResult:
        """
        Envia mensagem com lista de opções.
        Máximo de 10 itens total e 10 seções.
        """

        interactive = {
            "type": "list",
            "body": {
                "text": text
            },
            "action": {
                "button": button_text[:20],  # Máximo 20 caracteres
                "sections": [
                    {
                        "title": section.title[:24],  # Máximo 24 caracteres
                        "rows": [
                            {
                                "id": row.id,
                                "title": row.title[:24],
                                "description": row.description[:72] if row.description else ""
                            }
                            for row in section.rows
                        ]
                    }
                    for section in sections
                ]
            }
        }

        if header:
            interactive["header"] = {
                "type": "text",
                "text": header
            }

        if footer:
            interactive["footer"] = {
                "text": footer
            }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._format_phone(to),
            "type": "interactive",
            "interactive": interactive
        }

        return await self._send_request(payload, phone_number_id)

    async def send_audio(
        self,
        to: str,
        audio_url: Optional[str] = None,
        audio_base64: Optional[str] = None,
        instance: Optional[str] = None,
        phone_number_id: Optional[str] = None  # Multi-tenant: ID do número WhatsApp do cliente
    ) -> SendResult:
        """Envia mensagem de áudio."""

        if audio_url:
            # Enviar por URL
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self._format_phone(to),
                "type": "audio",
                "audio": {
                    "link": audio_url
                }
            }
        elif audio_base64:
            # Para base64, primeiro precisa fazer upload para obter media_id
            media_id = await self._upload_media(audio_base64, "audio/mpeg", phone_number_id)
            if not media_id:
                return SendResult(success=False, error="Falha ao fazer upload do áudio")

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self._format_phone(to),
                "type": "audio",
                "audio": {
                    "id": media_id
                }
            }
        else:
            return SendResult(success=False, error="Nenhum áudio fornecido")

        return await self._send_request(payload, phone_number_id)

    async def send_image(
        self,
        to: str,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        caption: Optional[str] = None,
        instance: Optional[str] = None,
        phone_number_id: Optional[str] = None  # Multi-tenant: ID do número WhatsApp do cliente
    ) -> SendResult:
        """Envia imagem."""

        if image_url:
            image_data = {"link": image_url}
        elif image_base64:
            media_id = await self._upload_media(image_base64, "image/jpeg", phone_number_id)
            if not media_id:
                return SendResult(success=False, error="Falha ao fazer upload da imagem")
            image_data = {"id": media_id}
        else:
            return SendResult(success=False, error="Nenhuma imagem fornecida")

        if caption:
            image_data["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._format_phone(to),
            "type": "image",
            "image": image_data
        }

        return await self._send_request(payload, phone_number_id)

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "pt_BR",
        components: Optional[List[Dict]] = None,
        instance: Optional[str] = None,
        phone_number_id: Optional[str] = None  # Multi-tenant: ID do número WhatsApp do cliente
    ) -> SendResult:
        """
        Envia mensagem usando template pré-aprovado.
        Templates são necessários para iniciar conversas (fora da janela de 24h).
        """

        template = {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }

        if components:
            template["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._format_phone(to),
            "type": "template",
            "template": template
        }

        return await self._send_request(payload, phone_number_id)

    # ==================== MÉTODOS AUXILIARES ====================

    async def _send_request(self, payload: Dict, phone_number_id: Optional[str] = None) -> SendResult:
        """Envia requisição para a API do WhatsApp."""

        # Usar phone_number_id específico ou o padrão do .env
        target_phone_id = phone_number_id or self.phone_id
        messages_url = f"{self.base_url}/{target_phone_id}/messages"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    messages_url,
                    headers=self.headers,
                    json=payload
                )

                data = response.json()

                if response.status_code == 200:
                    message_id = data.get("messages", [{}])[0].get("id")

                    # Log billing (fire-and-forget)
                    try:
                        from app.services.whatsapp_billing_service import log_whatsapp_message
                        template_name = payload.get("template", {}).get("name") if payload.get("type") == "template" else None
                        log_whatsapp_message(
                            template_name=template_name,
                            message_type=payload.get("type", "text"),
                            phone_to=payload.get("to", ""),
                            success=True,
                            message_id=message_id,
                        )
                    except Exception:
                        pass

                    return SendResult(
                        success=True,
                        message_id=message_id,
                        raw_response=data
                    )
                else:
                    error_msg = data.get("error", {}).get("message", "Erro desconhecido")
                    print(f"[WhatsApp Official] Erro: {error_msg}")

                    # Log billing para falhas também
                    try:
                        from app.services.whatsapp_billing_service import log_whatsapp_message
                        template_name = payload.get("template", {}).get("name") if payload.get("type") == "template" else None
                        log_whatsapp_message(
                            template_name=template_name,
                            message_type=payload.get("type", "text"),
                            phone_to=payload.get("to", ""),
                            success=False,
                            message_id=None,
                        )
                    except Exception:
                        pass

                    return SendResult(
                        success=False,
                        error=error_msg,
                        raw_response=data
                    )

        except Exception as e:
            print(f"[WhatsApp Official] Exceção: {e}")
            return SendResult(success=False, error=str(e))

    async def _upload_media(self, base64_data: str, mime_type: str, phone_number_id: Optional[str] = None) -> Optional[str]:
        """
        Faz upload de mídia para obter media_id.
        Retorna o media_id ou None em caso de erro.
        """

        import base64

        # Usar phone_number_id específico ou o padrão do .env
        target_phone_id = phone_number_id or self.phone_id
        upload_url = f"{self.base_url}/{target_phone_id}/media"

        try:
            # Decodifica base64
            media_bytes = base64.b64decode(base64_data)

            async with httpx.AsyncClient(timeout=60.0) as client:
                # Upload multipart
                files = {
                    "file": ("media", media_bytes, mime_type)
                }
                data = {
                    "messaging_product": "whatsapp",
                    "type": mime_type
                }

                response = await client.post(
                    upload_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    files=files,
                    data=data
                )

                if response.status_code == 200:
                    return response.json().get("id")
                else:
                    print(f"[WhatsApp Official] Erro upload: {response.text}")
                    return None

        except Exception as e:
            print(f"[WhatsApp Official] Exceção upload: {e}")
            return None

    # ==================== PARSING DE WEBHOOK ====================

    def parse_webhook(self, webhook_data: Dict[str, Any]) -> Optional[WhatsAppMessage]:
        """
        Converte webhook da Meta para formato padronizado.

        Formato de entrada (Meta Cloud API):
        {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "BUSINESS_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "PHONE_NUMBER",
                            "phone_number_id": "PHONE_NUMBER_ID"
                        },
                        "contacts": [{
                            "profile": {"name": "CONTACT_NAME"},
                            "wa_id": "WHATSAPP_ID"
                        }],
                        "messages": [{
                            "from": "SENDER_PHONE",
                            "id": "MESSAGE_ID",
                            "timestamp": "UNIX_TIMESTAMP",
                            "type": "text|audio|image|interactive",
                            "text": {"body": "MESSAGE_TEXT"},
                            ...
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        """

        try:
            # Navega até a mensagem
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})

            # Extrair metadata para multi-tenant
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id", "")
            display_phone_number = metadata.get("display_phone_number", "")

            messages = value.get("messages", [])
            if not messages:
                return None

            message = messages[0]
            contacts = value.get("contacts", [{}])[0]

            # Extrai informações básicas
            sender = message.get("from", "")
            message_id = message.get("id", "")
            timestamp = int(message.get("timestamp", 0))
            msg_type = message.get("type", "text")
            push_name = contacts.get("profile", {}).get("name", "")

            # Extrai texto baseado no tipo
            text = ""
            audio_url = None
            image_url = None
            button_reply_id = None
            list_reply_id = None

            if msg_type == "text":
                text = message.get("text", {}).get("body", "")

            elif msg_type == "audio":
                audio_data = message.get("audio", {})
                audio_url = audio_data.get("id")  # Na API oficial, recebemos media_id
                text = "[Áudio recebido]"

            elif msg_type == "image":
                image_data = message.get("image", {})
                image_url = image_data.get("id")
                text = image_data.get("caption", "[Imagem recebida]")

            elif msg_type == "interactive":
                interactive = message.get("interactive", {})
                interactive_type = interactive.get("type", "")

                if interactive_type == "button_reply":
                    button_data = interactive.get("button_reply", {})
                    button_reply_id = button_data.get("id", "")
                    text = button_data.get("title", "")

                elif interactive_type == "list_reply":
                    list_data = interactive.get("list_reply", {})
                    list_reply_id = list_data.get("id", "")
                    text = list_data.get("title", "")

            elif msg_type == "button":
                # Resposta de botão de template
                text = message.get("button", {}).get("text", "")

            return WhatsAppMessage(
                sender=sender,
                text=text,
                message_type=msg_type,
                push_name=push_name,
                message_id=message_id,
                timestamp=timestamp,
                is_from_me=False,
                audio_url=audio_url,
                image_url=image_url,
                button_reply_id=button_reply_id,
                list_reply_id=list_reply_id,
                raw_data=webhook_data,
                phone_number_id=phone_number_id,
                display_phone_number=display_phone_number
            )

        except Exception as e:
            print(f"[WhatsApp Official] Erro parsing webhook: {e}")
            return None

    def is_valid_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Verifica se o webhook contém mensagem válida."""

        try:
            # Verifica estrutura básica
            if webhook_data.get("object") != "whatsapp_business_account":
                return False

            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]

            # Verifica se é evento de mensagens
            if changes.get("field") != "messages":
                return False

            # Verifica se tem mensagens
            value = changes.get("value", {})
            messages = value.get("messages", [])

            return len(messages) > 0

        except Exception:
            return False

    def verify_webhook_token(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verifica token do webhook (usado na configuração inicial).

        A Meta envia uma requisição GET para verificar o webhook:
        GET /webhook?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=CHALLENGE

        Retorna o challenge se válido, None caso contrário.
        """

        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

    # ==================== STATUS E CONEXÃO ====================

    async def get_connection_status(self, instance: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifica status da conexão.
        Na API oficial, verificamos se as credenciais são válidas.
        """

        try:
            url = f"{self.base_url}/{self.phone_id}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "connected",
                        "phone_id": self.phone_id,
                        "display_phone_number": data.get("display_phone_number"),
                        "verified_name": data.get("verified_name"),
                        "quality_rating": data.get("quality_rating")
                    }
                else:
                    return {
                        "status": "error",
                        "error": response.json().get("error", {}).get("message")
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

    # ==================== DOWNLOAD DE MÍDIA ====================

    async def download_media(self, media_id: str) -> Optional[bytes]:
        """
        Baixa mídia pelo media_id.
        Na API oficial, primeiro obtemos a URL e depois baixamos.
        """

        try:
            # Primeiro, obtém a URL da mídia
            url = f"{self.base_url}/{media_id}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    print(f"[WhatsApp Official] Erro ao obter URL da mídia: {response.text}")
                    return None

                media_url = response.json().get("url")

                if not media_url:
                    return None

                # Agora baixa a mídia
                media_response = await client.get(
                    media_url,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )

                if media_response.status_code == 200:
                    return media_response.content
                else:
                    print(f"[WhatsApp Official] Erro ao baixar mídia: {media_response.status_code}")
                    return None

        except Exception as e:
            print(f"[WhatsApp Official] Exceção ao baixar mídia: {e}")
            return None

    # ==================== TEMPLATES ====================

    async def get_templates(self) -> List[Dict]:
        """Lista templates disponíveis na conta."""

        try:
            url = f"{self.base_url}/{self.business_account_id}/message_templates"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 200:
                    return response.json().get("data", [])
                else:
                    print(f"[WhatsApp Official] Erro ao listar templates: {response.text}")
                    return []

        except Exception as e:
            print(f"[WhatsApp Official] Exceção ao listar templates: {e}")
            return []
