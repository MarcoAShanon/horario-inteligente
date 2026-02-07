# app/api/reminders.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.database import get_db
from app.services.lembrete_service import lembrete_service
from app.scheduler import reminder_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/reminders",
    tags=["Lembretes"]
)


@router.get("/stats")
async def get_reminder_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retorna estatísticas de lembretes pendentes

    Returns:
        Estatísticas detalhadas
    """
    try:
        stats = lembrete_service.get_estatisticas(db)
        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """
    Retorna o status do scheduler de lembretes

    Returns:
        Status e informações dos jobs
    """
    try:
        status = reminder_scheduler.get_status()
        return {
            "success": True,
            "data": status
        }

    except Exception as e:
        logger.error(f"Erro ao obter status do scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/run-now")
async def run_scheduler_now() -> Dict[str, Any]:
    """
    Executa o processamento de lembretes imediatamente
    Útil para testes ou execução manual

    Returns:
        Resultado do processamento
    """
    try:
        await reminder_scheduler.run_now()
        return {
            "success": True,
            "message": "Processamento de lembretes executado com sucesso"
        }

    except Exception as e:
        logger.error(f"Erro ao executar processamento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Verifica se o sistema de lembretes está funcionando

    Returns:
        Status de saúde do sistema
    """
    try:
        scheduler_status = reminder_scheduler.get_status()
        stats = lembrete_service.get_estatisticas(db)

        return {
            "success": True,
            "status": "healthy",
            "scheduler_running": scheduler_status.get("running", False),
            "pending_reminders": stats.get("pendentes", 0)
        }

    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }
