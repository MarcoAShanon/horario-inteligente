# app/scheduler.py
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from app.services.status_update_service import status_update_service
from app.services.lembrete_service import lembrete_service
from app.services.billing_service import billing_service
from app.services.conversa_service import ConversaService

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """
    Gerenciador de tarefas agendadas para lembretes de consultas.

    IMPORTANTE: Este scheduler deve rodar em apenas UM worker/processo.
    O main.py usa file lock para garantir instância única.
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
            # Job para atualizar status de consultas passadas a cada 15 minutos
            self.scheduler.add_job(
                self._run_status_update,
                trigger=IntervalTrigger(minutes=15),
                id='update_status',
                name='Atualizar status de consultas passadas',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=300
            )

            # Job único para processar lembretes via API oficial Meta
            # (job legado 'process_reminders' removido — usava Evolution API descontinuada)
            self.scheduler.add_job(
                self._run_lembretes_inteligentes,
                trigger=IntervalTrigger(minutes=10),
                id='lembretes_inteligentes',
                name='Processar lembretes inteligentes (API oficial)',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=300
            )

            # Job de billing: verificar descontos expirados diariamente às 06:00
            self.scheduler.add_job(
                self._run_billing_sync,
                trigger=CronTrigger(hour=6, minute=0),
                id='billing_sync',
                name='Sincronizar billing e verificar descontos expirados',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=3600
            )

            # Job para devolver conversas inativas (humano assumiu mas esqueceu de devolver)
            self.scheduler.add_job(
                self._run_devolver_conversas_inativas,
                trigger=IntervalTrigger(minutes=5),
                id='devolver_conversas_inativas',
                name='Devolver conversas inativas para IA',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=300
            )

            # Iniciar o scheduler
            self.scheduler.start()
            self.is_running = True

            logger.info("✅ Scheduler de lembretes iniciado com sucesso")
            logger.info("🔄 Atualização de status a cada 15 minutos")
            logger.info("🔔 Lembretes inteligentes a cada 10 minutos")
            logger.info("💰 Billing sync diário às 06:00")
            logger.info("🔁 Devolução de conversas inativas a cada 5 minutos")

            # Executar atualização de status imediatamente (idempotente, sem risco de duplicação)
            asyncio.create_task(self._run_status_update())
            # NÃO executar lembretes no startup — aguardar o primeiro ciclo do scheduler
            # para evitar envios duplicados se o serviço reiniciar rapidamente

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

            from app.database import SessionLocal
            db = SessionLocal()
            try:
                # Atualizar status de consultas passadas
                stats = await status_update_service.atualizar_status_consultas_passadas(db)
            finally:
                db.close()

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

            from app.database import SessionLocal
            db = SessionLocal()
            try:
                # Processar lembretes pendentes
                stats = await lembrete_service.processar_lembretes_pendentes(db)
            finally:
                db.close()

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

    async def _run_devolver_conversas_inativas(self):
        """
        Devolve para a IA conversas assumidas por humanos que ficaram inativas por 30+ minutos.
        Chamado automaticamente pelo scheduler a cada 5 minutos.
        """
        try:
            start_time = datetime.now()
            logger.info(f"🔁 Verificando conversas inativas - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            from app.database import SessionLocal
            db = SessionLocal()

            try:
                devolvidas = ConversaService.devolver_conversas_inativas(db)

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                if devolvidas > 0:
                    logger.info(
                        f"✅ {devolvidas} conversa(s) devolvida(s) para IA por inatividade "
                        f"em {duration:.2f}s"
                    )
                else:
                    logger.debug(f"🔁 Nenhuma conversa inativa encontrada ({duration:.2f}s)")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Erro ao devolver conversas inativas: {str(e)}")

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
        await self._run_lembretes_inteligentes()


# Instância global do scheduler
reminder_scheduler = ReminderScheduler()
