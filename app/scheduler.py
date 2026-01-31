# app/scheduler.py
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from app.services.reminder_service import reminder_service
from app.services.status_update_service import status_update_service
from app.services.lembrete_service import lembrete_service
from app.services.billing_service import billing_service

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

            # Monitor Evolution API removido — sistema usa apenas API Oficial Meta
            # (WHATSAPP_PROVIDER=official)

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

            # Adicionar job para processar lembretes inteligentes (API oficial Meta)
            self.scheduler.add_job(
                self._run_lembretes_inteligentes,
                trigger=IntervalTrigger(minutes=10),
                id='lembretes_inteligentes',
                name='Processar lembretes inteligentes (API oficial)',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=300  # 5 minutos de tolerância
            )

            # Adicionar job de billing: verificar descontos expirados diariamente às 06:00
            self.scheduler.add_job(
                self._run_billing_sync,
                trigger=CronTrigger(hour=6, minute=0),
                id='billing_sync',
                name='Sincronizar billing e verificar descontos expirados',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=3600  # 1 hora de tolerância
            )

            # Iniciar o scheduler
            self.scheduler.start()
            self.is_running = True

            logger.info("✅ Scheduler de lembretes iniciado com sucesso")
            logger.info("📅 Lembretes serão verificados a cada 10 minutos")
            logger.info("🔄 Atualização de status a cada 15 minutos")
            logger.info("🔔 Lembretes inteligentes a cada 10 minutos")
            logger.info("💰 Billing sync diário às 06:00")

            # Executar imediatamente no startup (opcional)
            asyncio.create_task(self._run_reminder_processing())
            asyncio.create_task(self._run_status_update())
            asyncio.create_task(self._run_lembretes_inteligentes())

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

    async def _run_lembretes_inteligentes(self):
        """
        Processa lembretes inteligentes usando a API oficial do WhatsApp (Meta).
        Envia lembretes via templates e processa respostas com IA.

        Chamado automaticamente pelo scheduler a cada 10 minutos.
        """
        try:
            start_time = datetime.now()
            logger.info(f"🔔 Iniciando processamento de lembretes inteligentes - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # Processar lembretes pendentes
            stats = await lembrete_service.processar_lembretes_pendentes()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Calcular totais
            total_enviados = (
                stats.get("24h", {}).get("enviados", 0) +
                stats.get("3h", {}).get("enviados", 0) +
                stats.get("1h", {}).get("enviados", 0)
            )
            total_erros = (
                stats.get("24h", {}).get("erros", 0) +
                stats.get("3h", {}).get("erros", 0) +
                stats.get("1h", {}).get("erros", 0)
            )

            logger.info(
                f"✅ Lembretes inteligentes processados em {duration:.2f}s - "
                f"Enviados: {total_enviados}, Erros: {total_erros}"
            )

            if total_enviados > 0:
                logger.info(
                    f"   📊 Detalhes: 24h={stats.get('24h', {})}, "
                    f"3h={stats.get('3h', {})}, 1h={stats.get('1h', {})}"
                )

        except Exception as e:
            logger.error(f"❌ Erro ao processar lembretes inteligentes: {str(e)}")

    async def _run_billing_sync(self):
        """
        Job diário de billing:
        1. Verifica descontos promocionais expirados e atualiza valores
        2. Sincroniza status de assinaturas com ASAAS

        Executado diariamente às 06:00.
        """
        try:
            start_time = datetime.now()
            logger.info(f"💰 Iniciando billing sync - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            from app.database import SessionLocal
            db = SessionLocal()

            try:
                # 1. Verificar descontos expirados
                descontos_atualizados = await billing_service.check_expired_discounts(db)
                logger.info(f"💰 Descontos expirados atualizados: {descontos_atualizados}")

                # 2. Sincronizar assinaturas ativas com ASAAS
                from sqlalchemy import text
                assinaturas = db.execute(
                    text("""
                        SELECT id FROM assinaturas
                        WHERE status = 'ativa'
                        AND asaas_subscription_id IS NOT NULL
                    """)
                ).fetchall()

                sync_count = 0
                sync_errors = 0
                for row in assinaturas:
                    try:
                        status = await billing_service.sync_subscription_status(db, row[0])
                        if status:
                            sync_count += 1
                    except Exception as e:
                        sync_errors += 1
                        logger.warning(f"💰 Erro ao sincronizar assinatura {row[0]}: {e}")

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                logger.info(
                    f"✅ Billing sync concluído em {duration:.2f}s - "
                    f"Descontos: {descontos_atualizados}, "
                    f"Sync: {sync_count}/{len(assinaturas)}, "
                    f"Erros: {sync_errors}"
                )
            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Erro ao executar billing sync: {str(e)}")

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
