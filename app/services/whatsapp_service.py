# app/services/whatsapp_service.py
import aiohttp
import logging
import base64
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)

class WhatsAppService:
    """
    Serviço para integração com Evolution API WhatsApp
    """
    
    def __init__(self):
        self.evolution_url = "http://localhost:8080"
        self.api_key = "evolution-api-prosaude-123"
        self.headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }
    
    async def send_message(
        self, 
        instance_name: str, 
        to_number: str, 
        message: str
    ) -> Dict[str, Any]:
        """
        Envia mensagem de texto via Evolution API
        
        Args:
            instance_name: Nome da instância (ex: "prosaude-whatsapp")
            to_number: Número destino (ex: "5521999999999")
            message: Texto da mensagem
            
        Returns:
            Dict com resultado do envio
        """
        try:
            # Garantir formato correto do número
            if not to_number.startswith("55"):
                to_number = f"55{to_number}"
            
            # Payload para Evolution API
            payload = {
                "number": to_number,
                "textMessage": {
                    "text": message
                }
            }
            
            # URL do endpoint
            url = f"{self.evolution_url}/message/sendText/{instance_name}"
            
            # Enviar via HTTP
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url,
                    headers=self.headers,
                    json=payload
                ) as response:
                    
                    if response.status == 201:
                        result = await response.json()
                        logger.info(f"Mensagem enviada com sucesso para {to_number}")
                        return {
                            "success": True,
                            "message_id": result.get("key", {}).get("id"),
                            "status": result.get("status", "sent")
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Erro ao enviar mensagem: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
                        
        except Exception as e:
            logger.error(f"Exceção ao enviar mensagem: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_message_with_buttons(
        self,
        instance_name: str,
        to_number: str,
        text: str,
        buttons: list
    ) -> Dict[str, Any]:
        """
        Envia mensagem com botões interativos
        
        Args:
            instance_name: Nome da instância
            to_number: Número destino
            text: Texto principal
            buttons: Lista de botões [{"displayText": "Texto", "id": "id"}]
        """
        try:
            payload = {
                "number": to_number,
                "buttonMessage": {
                    "text": text,
                    "buttons": buttons,
                    "headerType": 1
                }
            }
            
            url = f"{self.evolution_url}/message/sendButtons/{instance_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url,
                    headers=self.headers,
                    json=payload
                ) as response:
                    
                    if response.status == 201:
                        result = await response.json()
                        return {"success": True, "data": result}
                    else:
                        error = await response.text()
                        return {"success": False, "error": error}
                        
        except Exception as e:
            logger.error(f"Erro ao enviar botões: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_instance_status(self, instance_name: str) -> Dict[str, Any]:
        """
        Verifica status da instância WhatsApp
        """
        try:
            url = f"{self.evolution_url}/instance/connectionState/{instance_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url, headers=self.headers) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "status": result.get("instance", {}).get("state", "unknown")
                        }
                    else:
                        return {"success": False, "error": f"HTTP {response.status}"}
                        
        except Exception as e:
            logger.error(f"Erro ao verificar status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_instance(
        self, 
        instance_name: str, 
        clinic_id: int,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria nova instância Evolution API para uma clínica
        """
        try:
            if not webhook_url:
                webhook_url = f"http://72.62.14.175:8000/webhook/whatsapp/{instance_name}"
            
            payload = {
                "instanceName": instance_name,
                "integration": "WHATSAPP-BAILEYS",
                "webhook_wa_business": {
                    "url": webhook_url,
                    "enabled": True,
                    "events": [
                        "MESSAGE_RECEIVED",
                        "MESSAGE_SENT",
                        "CONNECTION_UPDATE"
                    ]
                }
            }
            
            url = f"{self.evolution_url}/instance/create"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url,
                    headers=self.headers,
                    json=payload
                ) as response:
                    
                    if response.status == 201:
                        result = await response.json()
                        logger.info(f"Instância {instance_name} criada para clínica {clinic_id}")
                        return {"success": True, "data": result}
                    else:
                        error = await response.text()
                        logger.error(f"Erro ao criar instância: {error}")
                        return {"success": False, "error": error}
                        
        except Exception as e:
            logger.error(f"Exceção ao criar instância: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_qr_code(self, instance_name: str) -> Dict[str, Any]:
        """
        Obtém QR Code para conectar WhatsApp
        """
        try:
            url = f"{self.evolution_url}/instance/connect/{instance_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url, headers=self.headers) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "qr_code": result.get("base64", ""),
                            "code": result.get("code", "")
                        }
                    else:
                        error = await response.text()
                        return {"success": False, "error": error}
                        
        except Exception as e:
            logger.error(f"Erro ao obter QR: {str(e)}")
            return {"success": False, "error": str(e)}

    async def enviar_audio(
        self,
        instance_name: str,
        to_number: str,
        audio_path: str
    ) -> Dict[str, Any]:
        """
        Envia mensagem de áudio via WhatsApp (Evolution API)

        Args:
            instance_name: Nome da instância Evolution API
            to_number: Número do telefone (sem formatação)
            audio_path: Caminho do arquivo de áudio MP3

        Returns:
            Dict com resultado do envio
        """
        try:
            logger.info(f"🔊 Enviando áudio para {to_number}")

            # Garantir formato correto do número
            if not to_number.startswith("55"):
                to_number = f"55{to_number}"

            # Ler arquivo e converter para base64
            with open(audio_path, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode()

            # Endpoint Evolution API para enviar mídia
            url = f"{self.evolution_url}/message/sendMedia/{instance_name}"

            payload = {
                "number": to_number,
                "mediatype": "audio",
                "media": audio_base64,
                "fileName": "resposta.mp3"
            }

            # Enviar via HTTP
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url,
                    headers=self.headers,
                    json=payload
                ) as response:

                    if response.status == 201:
                        result = await response.json()
                        logger.info(f"✅ Áudio enviado com sucesso para {to_number}")
                        return {
                            "success": True,
                            "message_id": result.get("key", {}).get("id"),
                            "status": result.get("status", "sent")
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Erro ao enviar áudio: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}"
                        }

        except Exception as e:
            logger.error(f"❌ Exceção ao enviar áudio: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Instância global do serviço
whatsapp_service = WhatsAppService()


# Funções auxiliares para templates de mensagens
class MessageTemplates:
    """
    Templates de mensagens padronizadas
    """
    
    @staticmethod
    def welcome_message(clinic_name: str) -> str:
        return f"""🏥 Olá! Bem-vindo(a) à {clinic_name}!

Sou o assistente virtual e posso ajudar você com:
• 📅 Agendamento de consultas
• ℹ️ Informações sobre especialidades
• 📋 Cancelamento ou reagendamento

Como posso ajudar hoje?"""
    
    @staticmethod
    def appointment_options(available_slots: list) -> str:
        if not available_slots:
            return """😔 No momento não temos horários disponíveis nos próximos 7 dias.

Por favor, entre em contato pelo telefone ou tente novamente em alguns dias."""
        
        message = "📅 **Horários disponíveis:**\n\n"
        
        for i, slot in enumerate(available_slots[:5], 1):
            message += f"{i}. **{slot['medico_nome']}** ({slot['especialidade']})\n"
            message += f"   📅 {slot['formatted_datetime']}\n\n"
        
        message += "Digite o **número** da opção desejada para confirmar o agendamento."
        return message
    
    @staticmethod
    def appointment_confirmed(medico_nome: str, data_hora: str) -> str:
        return f"""✅ **Agendamento confirmado!**

👨‍⚕️ **Médico:** Dr(a). {medico_nome}
📅 **Data:** {data_hora}

📱 Você receberá lembretes automáticos:
• 24 horas antes
• 2 horas antes

Se precisar cancelar ou reagendar, é só me avisar! 😊"""
    
    @staticmethod
    def appointment_reminder_24h(medico_nome: str, data_hora: str, clinic_address: str = "") -> str:
        message = f"""⏰ **Lembrete: Consulta amanhã!**

👨‍⚕️ **Médico:** Dr(a). {medico_nome}
📅 **Data/Hora:** {data_hora}"""
        
        if clinic_address:
            message += f"\n📍 **Local:** {clinic_address}"
        
        message += f"""

Por favor, confirme sua presença respondendo:
• ✅ **SIM** - para confirmar
• ❌ **NÃO** - para cancelar"""
        
        return message
    
    @staticmethod
    def appointment_reminder_3h(medico_nome: str, data_hora: str, clinic_address: str = "") -> str:
        message = f"""🔔 **Lembrete: Consulta em 3 horas!**

👨‍⚕️ **Médico:** Dr(a). {medico_nome}
📅 **Horário:** {data_hora}"""

        if clinic_address:
            message += f"\n📍 **Local:** {clinic_address}"

        message += """

Já está a caminho? 😊

Se houver algum imprevisto, avise o quanto antes."""

        return message

    @staticmethod
    def appointment_reminder_1h(medico_nome: str, data_hora: str) -> str:
        return f"""⏰ **Lembrete URGENTE: Consulta em 1 hora!**

👨‍⚕️ **Médico:** Dr(a). {medico_nome}
📅 **Horário:** {data_hora}

⚠️ Não se atrase! Estamos te esperando! 😊"""
    
    @staticmethod
    def error_message() -> str:
        return """😔 Desculpe, tivemos um problema técnico.

Por favor:
• Tente novamente em alguns minutos
• Ou entre em contato pelo telefone

Obrigado pela compreensão!"""
