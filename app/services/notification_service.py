"""
Serviço de Notificações para Médicos
Gerencia o envio de notificações via WhatsApp e Email
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class NotificationService:
    """Gerencia notificações para médicos sobre eventos de agendamento"""

    def __init__(self, db: Session):
        self.db = db
        self.whatsapp_service = WhatsAppService()

    async def notificar_medico(
        self,
        medico_id: int,
        cliente_id: int,
        evento: str,
        dados_agendamento: Dict
    ) -> Dict:
        """
        Notifica médico sobre evento de agendamento

        Args:
            medico_id: ID do médico
            cliente_id: ID do cliente
            evento: Tipo de evento ('novo', 'reagendado', 'cancelado', 'confirmado')
            dados_agendamento: Dados do agendamento

        Returns:
            Dict com status do envio
        """
        try:
            # Buscar configurações de notificação do médico
            config = self._get_config(medico_id, cliente_id)

            if not config:
                logger.info(f"Médico {medico_id} não possui configurações de notificação")
                return {
                    "sucesso": True,
                    "mensagem": "Médico não configurou notificações"
                }

            # Verificar se deve notificar para este evento
            if not self._deve_notificar(config, evento):
                logger.info(f"Médico {medico_id} não quer notificação de {evento}")
                return {
                    "sucesso": True,
                    "mensagem": f"Notificação de {evento} desabilitada"
                }

            # Formatar mensagem
            mensagem = self._formatar_mensagem(evento, dados_agendamento)

            resultados = {
                "whatsapp": None,
                "email": None
            }

            # Enviar via WhatsApp se habilitado
            if config.get('canal_whatsapp') and config.get('whatsapp_numero'):
                resultado_wpp = await self._enviar_whatsapp(
                    config['whatsapp_numero'],
                    mensagem,
                    cliente_id
                )
                resultados["whatsapp"] = resultado_wpp

            # Enviar via Email se habilitado
            if config.get('canal_email') and config.get('email'):
                resultado_email = await self._enviar_email(
                    config['email'],
                    f"Notificação de Agendamento - {evento.title()}",
                    mensagem
                )
                resultados["email"] = resultado_email

            return {
                "sucesso": True,
                "mensagem": "Notificações processadas",
                "detalhes": resultados
            }

        except Exception as e:
            logger.error(f"Erro ao notificar médico: {e}", exc_info=True)
            return {
                "sucesso": False,
                "erro": str(e)
            }

    def _get_config(self, medico_id: int, cliente_id: int) -> Optional[Dict]:
        """Busca configurações de notificação do médico"""
        try:
            result = self.db.execute(text("""
                SELECT
                    notificar_novos,
                    notificar_reagendamentos,
                    notificar_cancelamentos,
                    notificar_confirmacoes,
                    canal_whatsapp,
                    canal_email,
                    whatsapp_numero,
                    email
                FROM notificacoes_medico
                WHERE medico_id = :medico_id
                  AND cliente_id = :cliente_id
            """), {
                "medico_id": medico_id,
                "cliente_id": cliente_id
            }).fetchone()

            if not result:
                return None

            return {
                "notificar_novos": result[0],
                "notificar_reagendamentos": result[1],
                "notificar_cancelamentos": result[2],
                "notificar_confirmacoes": result[3],
                "canal_whatsapp": result[4],
                "canal_email": result[5],
                "whatsapp_numero": result[6],
                "email": result[7]
            }

        except Exception as e:
            logger.error(f"Erro ao buscar config de notificação: {e}", exc_info=True)
            return None

    def _deve_notificar(self, config: Dict, evento: str) -> bool:
        """Verifica se deve notificar baseado no evento e configurações"""
        mapeamento = {
            "novo": config.get("notificar_novos", False),
            "reagendado": config.get("notificar_reagendamentos", False),
            "cancelado": config.get("notificar_cancelamentos", False),
            "confirmado": config.get("notificar_confirmacoes", False)
        }

        return mapeamento.get(evento, False)

    def _formatar_mensagem(self, evento: str, dados: Dict) -> str:
        """Formata mensagem de notificação baseada no evento"""
        paciente_nome = dados.get('paciente_nome', 'Paciente')
        data_hora = dados.get('data_hora', '')

        # Formatar data/hora se for datetime
        if isinstance(data_hora, datetime):
            data_hora_str = data_hora.strftime("%d/%m/%Y às %H:%M")
        else:
            data_hora_str = str(data_hora)

        mensagens = {
            "novo": f"""🔔 *Novo Agendamento*

📅 Data/Hora: {data_hora_str}
👤 Paciente: {paciente_nome}

Um novo agendamento foi confirmado na sua agenda.""",

            "reagendado": f"""🔄 *Agendamento Reagendado*

📅 Nova Data/Hora: {data_hora_str}
👤 Paciente: {paciente_nome}

Um agendamento foi reagendado.""",

            "cancelado": f"""❌ *Agendamento Cancelado*

📅 Data/Hora: {data_hora_str}
👤 Paciente: {paciente_nome}

Um agendamento foi cancelado.""",

            "confirmado": f"""✅ *Agendamento Confirmado*

📅 Data/Hora: {data_hora_str}
👤 Paciente: {paciente_nome}

O paciente confirmou presença."""
        }

        return mensagens.get(evento, f"Notificação de agendamento: {evento}")

    async def _enviar_whatsapp(
        self,
        numero: str,
        mensagem: str,
        cliente_id: int
    ) -> Dict:
        """Envia notificação via WhatsApp"""
        try:
            # Buscar nome da instância (TODO: buscar do banco baseado em cliente_id)
            instance_name = "ProSaude"

            resultado = await self.whatsapp_service.send_message(
                instance_name=instance_name,
                to_number=numero,
                message=mensagem
            )

            if resultado.get("success"):
                logger.info(f"✅ Notificação WhatsApp enviada para {numero}")
                return {"sucesso": True, "canal": "whatsapp"}
            else:
                logger.warning(f"⚠️ Falha ao enviar WhatsApp: {resultado.get('error')}")
                return {"sucesso": False, "erro": resultado.get('error'), "canal": "whatsapp"}

        except Exception as e:
            logger.error(f"Erro ao enviar WhatsApp: {e}", exc_info=True)
            return {"sucesso": False, "erro": str(e), "canal": "whatsapp"}

    async def _enviar_email(
        self,
        destinatario: str,
        assunto: str,
        mensagem: str
    ) -> Dict:
        """Envia notificação via Email"""
        try:
            # Configurações SMTP do .env
            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            smtp_from = os.getenv("SMTP_FROM", smtp_user)

            if not smtp_user or not smtp_password:
                logger.warning("SMTP não configurado no .env")
                return {
                    "sucesso": False,
                    "erro": "SMTP não configurado",
                    "canal": "email"
                }

            # Criar mensagem
            msg = MIMEMultipart('alternative')
            msg['Subject'] = assunto
            msg['From'] = smtp_from
            msg['To'] = destinatario

            # Converter mensagem de texto para HTML
            html_mensagem = mensagem.replace('\n', '<br>').replace('*', '<strong>').replace('</strong>', '</strong>')

            # Adicionar corpo texto simples
            part_text = MIMEText(mensagem, 'plain', 'utf-8')
            msg.attach(part_text)

            # Adicionar corpo HTML
            html = f"""
            <html>
              <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                  <p>{html_mensagem}</p>
                  <hr>
                  <p style="font-size: 12px; color: #666;">
                    Esta é uma notificação automática do sistema de agendamentos ProSaude.
                  </p>
                </div>
              </body>
            </html>
            """
            part_html = MIMEText(html, 'html', 'utf-8')
            msg.attach(part_html)

            # Enviar email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            logger.info(f"✅ Email enviado para {destinatario}")
            return {"sucesso": True, "canal": "email"}

        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}", exc_info=True)
            return {"sucesso": False, "erro": str(e), "canal": "email"}


# Factory function
def get_notification_service(db: Session) -> NotificationService:
    """Factory para obter instância do serviço"""
    return NotificationService(db)
