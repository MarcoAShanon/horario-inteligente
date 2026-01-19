# app/services/status_update_service.py
"""
Serviço para atualização automática de status de agendamentos.
Consultas confirmadas/agendadas cujas datas já passaram são
automaticamente marcadas como "realizada" (concluída).
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class StatusUpdateService:
    """
    Serviço que atualiza automaticamente o status de consultas passadas.
    Consultas confirmadas ou agendadas cujas datas já passaram (com margem
    de tolerância) são marcadas como "realizada".
    """

    def __init__(self):
        self.margem_tolerancia_minutos = 60  # 1 hora após o horário da consulta

    async def atualizar_status_consultas_passadas(self) -> dict:
        """
        Atualiza o status de consultas passadas para 'realizada'.

        Critérios:
        - Status atual: confirmado, confirmada, agendado, agendada, pendente
        - Data/hora já passou (com margem de tolerância)
        - Não foi cancelado, remarcado ou marcado como faltou

        Returns:
            Dicionário com estatísticas da atualização
        """
        db = SessionLocal()
        try:
            # Calcula o horário limite (agora - margem de tolerância)
            # Consultas antes deste horário são consideradas concluídas
            limite = datetime.now() - timedelta(minutes=self.margem_tolerancia_minutos)

            # Conta quantas consultas serão atualizadas
            result_count = db.execute(text("""
                SELECT COUNT(*)
                FROM agendamentos
                WHERE status IN ('confirmado', 'confirmada', 'agendado', 'agendada', 'pendente', 'em_atendimento')
                AND data_hora < :limite
            """), {"limite": limite})

            total_pendentes = result_count.scalar() or 0

            if total_pendentes == 0:
                logger.info("✅ Nenhuma consulta passada para atualizar")
                return {
                    "atualizadas": 0,
                    "timestamp": datetime.now().isoformat()
                }

            # Atualiza o status para 'realizada'
            result_update = db.execute(text("""
                UPDATE agendamentos
                SET status = 'realizada'
                WHERE status IN ('confirmado', 'confirmada', 'agendado', 'agendada', 'pendente', 'em_atendimento')
                AND data_hora < :limite
            """), {"limite": limite})

            db.commit()

            atualizadas = result_update.rowcount

            logger.info(f"✅ {atualizadas} consultas atualizadas para status 'realizada'")

            return {
                "atualizadas": atualizadas,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erro ao atualizar status de consultas: {str(e)}")
            raise
        finally:
            db.close()

    async def get_estatisticas(self) -> dict:
        """
        Retorna estatísticas sobre consultas que precisam de atualização.
        """
        db = SessionLocal()
        try:
            limite = datetime.now() - timedelta(minutes=self.margem_tolerancia_minutos)

            result = db.execute(text("""
                SELECT
                    status,
                    COUNT(*) as total
                FROM agendamentos
                WHERE status IN ('confirmado', 'confirmada', 'agendado', 'agendada', 'pendente', 'em_atendimento')
                AND data_hora < :limite
                GROUP BY status
            """), {"limite": limite})

            pendentes = {row[0]: row[1] for row in result.fetchall()}

            return {
                "pendentes_por_status": pendentes,
                "total_pendentes": sum(pendentes.values()),
                "limite_usado": limite.isoformat(),
                "timestamp": datetime.now().isoformat()
            }

        finally:
            db.close()


# Instância global do serviço
status_update_service = StatusUpdateService()
