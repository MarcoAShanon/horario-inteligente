# app/api/reminders.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from app.services.reminder_service import reminder_service
from app.scheduler import reminder_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/reminders",
    tags=["Lembretes"]
)


@router.get("/stats")
async def get_reminder_stats() -> Dict[str, Any]:
    """
    Retorna estatísticas de lembretes pendentes

    Returns:
        Estatísticas detalhadas
    """
    try:
        stats = reminder_service.get_pending_reminders_stats()
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


@router.post("/send/{agendamento_id}/{reminder_type}")
async def send_immediate_reminder(
    agendamento_id: int,
    reminder_type: str
) -> Dict[str, Any]:
    """
    Envia um lembrete específico imediatamente

    Args:
        agendamento_id: ID do agendamento
        reminder_type: Tipo de lembrete (24h, 3h, 1h)

    Returns:
        Resultado do envio
    """
    # Validar tipo de lembrete
    if reminder_type not in ["24h", "3h", "1h"]:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de lembrete inválido: {reminder_type}. Use: 24h, 3h ou 1h"
        )

    try:
        resultado = await reminder_service.send_immediate_reminder(
            agendamento_id=agendamento_id,
            reminder_type=reminder_type
        )

        if resultado.get("success"):
            return {
                "success": True,
                "message": f"Lembrete {reminder_type} enviado com sucesso",
                "data": resultado
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=resultado.get("error", "Erro ao enviar lembrete")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar lembrete: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Verifica se o sistema de lembretes está funcionando

    Returns:
        Status de saúde do sistema
    """
    try:
        scheduler_status = reminder_scheduler.get_status()
        pending_stats = reminder_service.get_pending_reminders_stats()

        return {
            "success": True,
            "status": "healthy",
            "scheduler_running": scheduler_status.get("running", False),
            "pending_reminders": pending_stats.get("total_pending", 0)
        }

    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }
