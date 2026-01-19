# app/scheduler.py
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from app.services.reminder_service import reminder_service
from app.services.whatsapp_monitor import whatsapp_monitor
from app.services.status_update_service import status_update_service

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """
    Gerenciador de tarefas agendadas para lembretes de consultas
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self):
        """
        Inicia o scheduler de lembretes
        Executa verificação a cada 10 minutos
        """
        if self.is_running:
            logger.warning("⚠️ Scheduler já está rodando")
            return

        try:
            # Adicionar job para processar lembretes a cada 10 minutos
            self.scheduler.add_job(
                self._run_reminder_processing,
                trigger=IntervalTrigger(minutes=10),
                id='process_reminders',
                name='Processar lembretes de consultas',
                replace_existing=True,
                max_instances=1,  # Não permitir execuções simultâneas
                misfire_grace_time=300  # 5 minutos de tolerância
            )

            # Adicionar job para monitorar WhatsApp a cada 5 minutos
            self.scheduler.add_job(
                self._run_whatsapp_monitoring,
                trigger=IntervalTrigger(minutes=5),
                id='monitor_whatsapp',
                name='Monitorar conexão WhatsApp',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=180  # 3 minutos de tolerância
            )

            # Adicionar job para atualizar status de consultas passadas a cada 15 minutos
            self.scheduler.add_job(
                self._run_status_update,
                trigger=IntervalTrigger(minutes=15),
                id='update_status',
                name='Atualizar status de consultas passadas',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=300  # 5 minutos de tolerância
            )

            # Iniciar o scheduler
            self.scheduler.start()
            self.is_running = True

            logger.info("✅ Scheduler de lembretes iniciado com sucesso")
            logger.info("📅 Lembretes serão verificados a cada 10 minutos")
            logger.info("📱 Monitoramento WhatsApp a cada 5 minutos")
            logger.info("🔄 Atualização de status a cada 15 minutos")

            # Executar imediatamente no startup (opcional)
            asyncio.create_task(self._run_reminder_processing())
            asyncio.create_task(self._run_whatsapp_monitoring())
            asyncio.create_task(self._run_status_update())

        except Exception as e:
            logger.error(f"❌ Erro ao iniciar scheduler: {str(e)}")
            raise

    def stop(self):
        """
        Para o scheduler
        """
        if not self.is_running:
            logger.warning("⚠️ Scheduler não está rodando")
            return

        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("✅ Scheduler de lembretes parado")

        except Exception as e:
            logger.error(f"❌ Erro ao parar scheduler: {str(e)}")

    async def _run_reminder_processing(self):
        """
        Executa o processamento de todos os lembretes
        Chamado automaticamente pelo scheduler
        """
        try:
            start_time = datetime.now()
            logger.info(f"🔄 Iniciando verificação de lembretes - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # Processar todos os lembretes
            stats = await reminder_service.process_all_reminders()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"✅ Verificação concluída em {duration:.2f}s - "
                f"24h: {stats['lembretes_24h']}, "
                f"3h: {stats['lembretes_3h']}, "
                f"1h: {stats['lembretes_1h']}, "
                f"Erros: {stats['erros']}"
            )

        except Exception as e:
            logger.error(f"❌ Erro ao executar processamento de lembretes: {str(e)}")

    async def _run_whatsapp_monitoring(self):
        """
        Executa o monitoramento de conexão do WhatsApp
        Chamado automaticamente pelo scheduler a cada 5 minutos
        """
        try:
            logger.info(f"📱 Verificando status da conexão WhatsApp...")

            # Verificar todas as instâncias
            stats = await whatsapp_monitor.verificar_todas_instancias()

            # Enviar alertas se houver desconexões
            for instance in stats.get("alertas", []):
                await whatsapp_monitor.enviar_alerta_desconexao(instance)

            logger.info(
                f"✅ Monitoramento WhatsApp concluído - "
                f"Conectadas: {stats['conectadas']}/{stats['total']}"
            )

        except Exception as e:
            logger.error(f"❌ Erro ao executar monitoramento WhatsApp: {str(e)}")

    async def _run_status_update(self):
        """
        Atualiza automaticamente o status de consultas passadas para 'realizada'.
        Chamado automaticamente pelo scheduler a cada 15 minutos.

        Consultas confirmadas/agendadas cujas datas já passaram são
        marcadas como concluídas (status = 'realizada').
        """
        try:
            start_time = datetime.now()
            logger.info(f"🔄 Iniciando atualização de status - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # Atualizar status de consultas passadas
            stats = await status_update_service.atualizar_status_consultas_passadas()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"✅ Atualização de status concluída em {duration:.2f}s - "
                f"Atualizadas: {stats['atualizadas']}"
            )

        except Exception as e:
            logger.error(f"❌ Erro ao executar atualização de status: {str(e)}")

    def get_status(self):
        """
        Retorna o status do scheduler

        Returns:
            Dicionário com informações de status
        """
        try:
            jobs = self.scheduler.get_jobs()

            return {
                "running": self.is_running,
                "jobs_count": len(jobs),
                "jobs": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                    }
                    for job in jobs
                ],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Erro ao obter status: {str(e)}")
            return {
                "running": self.is_running,
                "error": str(e)
            }

    async def run_now(self):
        """
        Executa o processamento de lembretes imediatamente
        Útil para testes
        """
        logger.info("🔄 Execução manual de processamento de lembretes")
        await self._run_reminder_processing()


# Instância global do scheduler
reminder_scheduler = ReminderScheduler()
