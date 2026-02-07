# app/services/reminder_service.py
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Importar do pacote models para garantir ordem correta de carregamento
from app.models import Agendamento, Paciente, Medico, Cliente
from app.services.whatsapp_service import whatsapp_service, MessageTemplates
from app.utils.timezone_helper import now_brazil, format_brazil

logger = logging.getLogger(__name__)


class ReminderService:
    """
    Serviço para gerenciamento de lembretes de consultas
    Envia notificações via WhatsApp em 24h, 3h e 1h antes da consulta
    """

    def __init__(self):
        self.instance_name = "HorarioInteligente"  # Nome da instância Evolution API (legado)

    async def process_all_reminders(self, db: Session) -> Dict[str, Any]:
        """
        Processa todos os lembretes pendentes
        Deve ser executado periodicamente pelo scheduler

        Args:
            db: Sessão do banco de dados

        Returns:
            Estatísticas de processamento
        """
        logger.info("🔔 Iniciando processamento de lembretes...")

        stats = {
            "lembretes_24h": 0,
            "lembretes_3h": 0,
            "lembretes_1h": 0,
            "erros": 0,
            "timestamp": datetime.now().isoformat()
        }

        try:
            # Processar lembretes de 24h
            stats["lembretes_24h"] = await self._process_24h_reminders(db)

            # Processar lembretes de 3h
            stats["lembretes_3h"] = await self._process_3h_reminders(db)

            # Processar lembretes de 1h
            stats["lembretes_1h"] = await self._process_1h_reminders(db)

            logger.info(f"✅ Processamento concluído: {stats}")

        except Exception as e:
            logger.error(f"❌ Erro ao processar lembretes: {str(e)}")
            stats["erros"] += 1

        return stats

    async def _process_24h_reminders(self, db: Session) -> int:
        """
        Processa lembretes de 24 horas antes da consulta

        Args:
            db: Sessão do banco de dados

        Returns:
            Quantidade de lembretes enviados
        """
        try:
            # Buscar consultas que ocorrerão em aproximadamente 24h
            # Usar timezone de Brasília (timezone-aware)
            now = now_brazil()
            target_time_start = now + timedelta(hours=23, minutes=50)
            target_time_end = now + timedelta(hours=24, minutes=10)

            agendamentos = db.query(Agendamento).filter(
                and_(
                    Agendamento.data_hora >= target_time_start,
                    Agendamento.data_hora <= target_time_end,
                    Agendamento.lembrete_24h_enviado == False,
                    Agendamento.status.in_(["agendado", "confirmado"])
                )
            ).all()

            count = 0
            for agendamento in agendamentos:
                success = await self._send_24h_reminder(db, agendamento)
                if success:
                    count += 1

            logger.info(f"📅 Lembretes 24h enviados: {count}")
            return count

        except Exception as e:
            logger.error(f"❌ Erro ao processar lembretes 24h: {str(e)}")
            return 0

    async def _process_3h_reminders(self, db: Session) -> int:
        """
        Processa lembretes de 3 horas antes da consulta

        Args:
            db: Sessão do banco de dados

        Returns:
            Quantidade de lembretes enviados
        """
        try:
            # Buscar consultas que ocorrerão em aproximadamente 3h
            # Usar timezone de Brasília (timezone-aware)
            now = now_brazil()
            target_time_start = now + timedelta(hours=2, minutes=50)
            target_time_end = now + timedelta(hours=3, minutes=10)

            agendamentos = db.query(Agendamento).filter(
                and_(
                    Agendamento.data_hora >= target_time_start,
                    Agendamento.data_hora <= target_time_end,
                    Agendamento.lembrete_3h_enviado == False,
                    Agendamento.status.in_(["agendado", "confirmado"])
                )
            ).all()

            count = 0
            for agendamento in agendamentos:
                success = await self._send_3h_reminder(db, agendamento)
                if success:
                    count += 1

            logger.info(f"🔔 Lembretes 3h enviados: {count}")
            return count

        except Exception as e:
            logger.error(f"❌ Erro ao processar lembretes 3h: {str(e)}")
            return 0

    async def _process_1h_reminders(self, db: Session) -> int:
        """
        Processa lembretes de 1 hora antes da consulta

        Args:
            db: Sessão do banco de dados

        Returns:
            Quantidade de lembretes enviados
        """
        try:
            # Buscar consultas que ocorrerão em aproximadamente 1h
            # Usar timezone de Brasília (timezone-aware)
            now = now_brazil()
            target_time_start = now + timedelta(minutes=50)
            target_time_end = now + timedelta(hours=1, minutes=10)

            agendamentos = db.query(Agendamento).filter(
                and_(
                    Agendamento.data_hora >= target_time_start,
                    Agendamento.data_hora <= target_time_end,
                    Agendamento.lembrete_1h_enviado == False,
                    Agendamento.status.in_(["agendado", "confirmado"])
                )
            ).all()

            count = 0
            for agendamento in agendamentos:
                success = await self._send_1h_reminder(db, agendamento)
                if success:
                    count += 1

            logger.info(f"⏰ Lembretes 1h enviados: {count}")
            return count

        except Exception as e:
            logger.error(f"❌ Erro ao processar lembretes 1h: {str(e)}")
            return 0

    async def _send_24h_reminder(self, db: Session, agendamento: Agendamento) -> bool:
        """
        Envia lembrete de 24 horas para um agendamento específico

        Args:
            db: Sessão do banco
            agendamento: Objeto Agendamento

        Returns:
            True se enviado com sucesso
        """
        try:
            # Carregar dados relacionados
            paciente = db.query(Paciente).filter(Paciente.id == agendamento.paciente_id).first()
            medico = db.query(Medico).filter(Medico.id == agendamento.medico_id).first()
            cliente = db.query(Cliente).filter(Cliente.id == medico.cliente_id).first()

            if not paciente or not medico or not cliente:
                logger.error(f"❌ Dados incompletos para agendamento {agendamento.id}")
                return False

            # Formatar data/hora (timezone-aware)
            data_hora_formatada = format_brazil(agendamento.data_hora)

            # Gerar mensagem
            mensagem = MessageTemplates.appointment_reminder_24h(
                medico_nome=medico.nome,
                data_hora=data_hora_formatada,
                clinic_address=cliente.endereco or ""
            )

            # Enviar via WhatsApp
            resultado = await whatsapp_service.send_message(
                instance_name=self.instance_name,
                to_number=paciente.telefone,
                message=mensagem
            )

            if resultado.get("success"):
                # Marcar como enviado
                agendamento.lembrete_24h_enviado = True
                db.commit()

                logger.info(f"✅ Lembrete 24h enviado para {paciente.nome} ({paciente.telefone})")
                return True
            else:
                logger.error(f"❌ Falha ao enviar lembrete 24h: {resultado.get('error')}")
                return False

        except Exception as e:
            logger.error(f"❌ Exceção ao enviar lembrete 24h: {str(e)}")
            db.rollback()
            return False

    async def _send_3h_reminder(self, db: Session, agendamento: Agendamento) -> bool:
        """
        Envia lembrete de 3 horas para um agendamento específico

        Args:
            db: Sessão do banco
            agendamento: Objeto Agendamento

        Returns:
            True se enviado com sucesso
        """
        try:
            # Carregar dados relacionados
            paciente = db.query(Paciente).filter(Paciente.id == agendamento.paciente_id).first()
            medico = db.query(Medico).filter(Medico.id == agendamento.medico_id).first()
            cliente = db.query(Cliente).filter(Cliente.id == medico.cliente_id).first()

            if not paciente or not medico or not cliente:
                logger.error(f"❌ Dados incompletos para agendamento {agendamento.id}")
                return False

            # Formatar data/hora (timezone-aware)
            data_hora_formatada = format_brazil(agendamento.data_hora)

            # Gerar mensagem
            mensagem = MessageTemplates.appointment_reminder_3h(
                medico_nome=medico.nome,
                data_hora=data_hora_formatada,
                clinic_address=cliente.endereco or ""
            )

            # Enviar via WhatsApp
            resultado = await whatsapp_service.send_message(
                instance_name=self.instance_name,
                to_number=paciente.telefone,
                message=mensagem
            )

            if resultado.get("success"):
                # Marcar como enviado
                agendamento.lembrete_3h_enviado = True
                db.commit()

                logger.info(f"✅ Lembrete 3h enviado para {paciente.nome} ({paciente.telefone})")
                return True
            else:
                logger.error(f"❌ Falha ao enviar lembrete 3h: {resultado.get('error')}")
                return False

        except Exception as e:
            logger.error(f"❌ Exceção ao enviar lembrete 3h: {str(e)}")
            db.rollback()
            return False

    async def _send_1h_reminder(self, db: Session, agendamento: Agendamento) -> bool:
        """
        Envia lembrete de 1 hora para um agendamento específico

        Args:
            db: Sessão do banco
            agendamento: Objeto Agendamento

        Returns:
            True se enviado com sucesso
        """
        try:
            # Carregar dados relacionados
            paciente = db.query(Paciente).filter(Paciente.id == agendamento.paciente_id).first()
            medico = db.query(Medico).filter(Medico.id == agendamento.medico_id).first()

            if not paciente or not medico:
                logger.error(f"❌ Dados incompletos para agendamento {agendamento.id}")
                return False

            # Formatar data/hora (timezone-aware)
            data_hora_formatada = format_brazil(agendamento.data_hora)

            # Gerar mensagem
            mensagem = MessageTemplates.appointment_reminder_1h(
                medico_nome=medico.nome,
                data_hora=data_hora_formatada
            )

            # Enviar via WhatsApp
            resultado = await whatsapp_service.send_message(
                instance_name=self.instance_name,
                to_number=paciente.telefone,
                message=mensagem
            )

            if resultado.get("success"):
                # Marcar como enviado
                agendamento.lembrete_1h_enviado = True
                db.commit()

                logger.info(f"✅ Lembrete 1h enviado para {paciente.nome} ({paciente.telefone})")
                return True
            else:
                logger.error(f"❌ Falha ao enviar lembrete 1h: {resultado.get('error')}")
                return False

        except Exception as e:
            logger.error(f"❌ Exceção ao enviar lembrete 1h: {str(e)}")
            db.rollback()
            return False

    async def send_immediate_reminder(
        self,
        agendamento_id: int,
        reminder_type: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Envia um lembrete imediato (para testes ou reenvio manual)

        Args:
            agendamento_id: ID do agendamento
            reminder_type: Tipo de lembrete (24h, 3h, 1h)
            db: Sessão do banco de dados

        Returns:
            Resultado do envio
        """
        try:
            agendamento = db.query(Agendamento).filter(
                Agendamento.id == agendamento_id
            ).first()

            if not agendamento:
                return {
                    "success": False,
                    "error": f"Agendamento {agendamento_id} não encontrado"
                }

            # Enviar de acordo com o tipo
            if reminder_type == "24h":
                success = await self._send_24h_reminder(db, agendamento)
            elif reminder_type == "3h":
                success = await self._send_3h_reminder(db, agendamento)
            elif reminder_type == "1h":
                success = await self._send_1h_reminder(db, agendamento)
            else:
                return {
                    "success": False,
                    "error": f"Tipo de lembrete inválido: {reminder_type}"
                }

            return {
                "success": success,
                "agendamento_id": agendamento_id,
                "reminder_type": reminder_type
            }

        except Exception as e:
            logger.error(f"❌ Erro ao enviar lembrete imediato: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_pending_reminders_stats(self, db: Session) -> Dict[str, Any]:
        """
        Retorna estatísticas de lembretes pendentes

        Args:
            db: Sessão do banco de dados

        Returns:
            Estatísticas detalhadas
        """
        try:
            # Usar timezone de Brasília (timezone-aware)
            now = now_brazil()

            # Contar lembretes pendentes de 24h
            target_24h_start = now + timedelta(hours=23, minutes=50)
            target_24h_end = now + timedelta(hours=24, minutes=10)
            pending_24h = db.query(Agendamento).filter(
                and_(
                    Agendamento.data_hora >= target_24h_start,
                    Agendamento.data_hora <= target_24h_end,
                    Agendamento.lembrete_24h_enviado == False,
                    Agendamento.status.in_(["agendado", "confirmado"])
                )
            ).count()

            # Contar lembretes pendentes de 3h
            target_3h_start = now + timedelta(hours=2, minutes=50)
            target_3h_end = now + timedelta(hours=3, minutes=10)
            pending_3h = db.query(Agendamento).filter(
                and_(
                    Agendamento.data_hora >= target_3h_start,
                    Agendamento.data_hora <= target_3h_end,
                    Agendamento.lembrete_3h_enviado == False,
                    Agendamento.status.in_(["agendado", "confirmado"])
                )
            ).count()

            # Contar lembretes pendentes de 1h
            target_1h_start = now + timedelta(minutes=50)
            target_1h_end = now + timedelta(hours=1, minutes=10)
            pending_1h = db.query(Agendamento).filter(
                and_(
                    Agendamento.data_hora >= target_1h_start,
                    Agendamento.data_hora <= target_1h_end,
                    Agendamento.lembrete_1h_enviado == False,
                    Agendamento.status.in_(["agendado", "confirmado"])
                )
            ).count()

            return {
                "pending_24h": pending_24h,
                "pending_3h": pending_3h,
                "pending_1h": pending_1h,
                "total_pending": pending_24h + pending_3h + pending_1h,
                "timestamp": now.isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {str(e)}")
            return {
                "error": str(e)
            }


# Instância global do serviço
reminder_service = ReminderService()
