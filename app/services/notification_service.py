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

from app.services.whatsapp_official_service import WhatsAppOfficialService
from app.services.push_notification_service import push_service

logger = logging.getLogger(__name__)


class NotificationService:
    """Gerencia notificações para médicos sobre eventos de agendamento"""

    def __init__(self, db: Session):
        self.db = db
        self.whatsapp_service = WhatsAppOfficialService()

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
            resultados = {
                "whatsapp": None,
                "email": None,
                "push": None
            }

            # Enviar via Push Notification (gratuito e instantâneo)
            # Push é enviado SEMPRE que o médico tem subscriptions ativas
            # Não depende de config pois é baseado em subscription
            resultado_push = await self._enviar_push(
                medico_id,
                evento,
                dados_agendamento
            )
            resultados["push"] = resultado_push

            # Buscar configurações de notificação do médico (para WhatsApp/Email)
            config = self._get_config(medico_id, cliente_id)

            if not config:
                logger.info(f"Médico {medico_id} não possui configurações de notificação (WhatsApp/Email)")
                return {
                    "sucesso": True,
                    "mensagem": "Push enviado, sem config de WhatsApp/Email",
                    "detalhes": resultados
                }

            # Verificar se deve notificar para este evento (WhatsApp/Email)
            if not self._deve_notificar(config, evento):
                logger.info(f"Médico {medico_id} não quer notificação de {evento} via WhatsApp/Email")
                return {
                    "sucesso": True,
                    "mensagem": f"Notificação de {evento} desabilitada para WhatsApp/Email",
                    "detalhes": resultados
                }

            # Formatar mensagem para WhatsApp/Email
            mensagem = self._formatar_mensagem(evento, dados_agendamento)

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

    async def _enviar_push(
        self,
        medico_id: int,
        evento: str,
        dados: Dict
    ) -> Dict:
        """Envia notificação via Push Notification (Web Push API)"""
        try:
            paciente_nome = dados.get('paciente_nome', 'Paciente')
            data_hora = dados.get('data_hora', '')

            # Formatar data/hora se for datetime
            if isinstance(data_hora, datetime):
                data_hora_str = data_hora.strftime("%d/%m às %H:%M")
            else:
                data_hora_str = str(data_hora)

            # Definir título e corpo baseado no evento
            titulos = {
                "novo": "Novo Agendamento",
                "reagendado": "Agendamento Reagendado",
                "cancelado": "Agendamento Cancelado",
                "confirmado": "Paciente Confirmou"
            }

            corpos = {
                "novo": f"{paciente_nome} - {data_hora_str}",
                "reagendado": f"{paciente_nome} reagendou para {data_hora_str}",
                "cancelado": f"{paciente_nome} cancelou ({data_hora_str})",
                "confirmado": f"{paciente_nome} confirmou presença - {data_hora_str}"
            }

            titulo = titulos.get(evento, "Notificação de Agendamento")
            corpo = corpos.get(evento, f"{paciente_nome} - {data_hora_str}")

            # Enviar push notification
            resultado = await push_service.send_notification(
                db=self.db,
                medico_id=medico_id,
                title=titulo,
                body=corpo,
                url="/static/calendario-unificado.html",
                tag=f"agendamento-{evento}"
            )

            if resultado.get("sent", 0) > 0:
                logger.info(f"📱 Push notification enviada para médico {medico_id}")
                return {
                    "sucesso": True,
                    "canal": "push",
                    "enviados": resultado.get("sent", 0)
                }
            else:
                reason = resultado.get("reason", "unknown")
                if reason == "no_subscriptions":
                    logger.debug(f"Médico {medico_id} não tem push subscriptions ativas")
                return {
                    "sucesso": False,
                    "canal": "push",
                    "motivo": reason
                }

        except Exception as e:
            logger.error(f"Erro ao enviar push notification: {e}", exc_info=True)
            return {"sucesso": False, "erro": str(e), "canal": "push"}

    async def _enviar_whatsapp(
        self,
        numero: str,
        mensagem: str,
        cliente_id: int
    ) -> Dict:
        """Envia notificação via WhatsApp (API Oficial Meta)"""
        try:
            # Buscar phone_number_id do cliente
            config = self.db.execute(text("""
                SELECT whatsapp_phone_number_id
                FROM configuracoes
                WHERE cliente_id = :cliente_id AND whatsapp_ativo = true
            """), {"cliente_id": cliente_id}).fetchone()

            phone_number_id = config[0] if config else None

            resultado = await self.whatsapp_service.send_text(
                to=numero,
                message=mensagem,
                phone_number_id=phone_number_id
            )

            if resultado.success:
                logger.info(f"Notificação WhatsApp enviada para {numero}")
                return {"sucesso": True, "canal": "whatsapp"}
            else:
                logger.warning(f"Falha ao enviar WhatsApp: {resultado.error}")
                return {"sucesso": False, "erro": resultado.error, "canal": "whatsapp"}

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
                    Esta é uma notificação automática do sistema Horário Inteligente.
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
