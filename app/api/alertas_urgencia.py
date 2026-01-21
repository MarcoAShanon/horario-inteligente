"""
API de Alertas de Urgência
Horário Inteligente SaaS

Endpoints para gerenciar alertas de urgência em conversas WhatsApp.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.api.auth import get_current_user
from app.services.urgencia_service import get_urgencia_service

router = APIRouter(prefix="/api/alertas", tags=["Alertas de Urgência"])


# ==================== SCHEMAS ====================

class ResolverAlertaRequest(BaseModel):
    nota: Optional[str] = None


class AlertaResponse(BaseModel):
    id: int
    conversa_id: int
    nivel: str
    motivo: str
    mensagem_gatilho: Optional[str]
    paciente_telefone: str
    paciente_nome: Optional[str]
    criado_em: Optional[str]
    visualizado: bool
    conversa_status: Optional[str]


# ==================== ENDPOINTS ====================

@router.get("/pendentes")
async def listar_alertas_pendentes(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lista todos os alertas de urgência pendentes (não resolvidos).

    Ordenados por prioridade: críticos primeiro, depois atenção.
    """
    cliente_id = current_user.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=400, detail="cliente_id não encontrado")

    urgencia_service = get_urgencia_service(db)
    alertas = urgencia_service.listar_alertas_pendentes(cliente_id)

    return {
        "success": True,
        "alertas": alertas,
        "total": len(alertas)
    }


@router.get("/contagem")
async def contar_alertas(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retorna contagem de alertas pendentes por nível.

    Útil para exibir badges de notificação no frontend.
    """
    cliente_id = current_user.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=400, detail="cliente_id não encontrado")

    urgencia_service = get_urgencia_service(db)
    contagem = urgencia_service.contar_alertas_pendentes(cliente_id)

    return {
        "success": True,
        "contagem": contagem
    }


@router.post("/{alerta_id}/visualizar")
async def marcar_visualizado(
    alerta_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Marca um alerta como visualizado.

    Não significa que foi resolvido, apenas que o usuário viu.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id não encontrado")

    urgencia_service = get_urgencia_service(db)
    result = urgencia_service.marcar_alerta_visualizado(alerta_id, user_id)

    if result:
        return {"success": True, "message": "Alerta marcado como visualizado"}
    else:
        raise HTTPException(status_code=500, detail="Erro ao marcar alerta como visualizado")


@router.post("/conversa/{conversa_id}/resolver")
async def resolver_urgencia(
    conversa_id: int,
    dados: ResolverAlertaRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Resolve a urgência de uma conversa.

    Marca todos os alertas pendentes da conversa como resolvidos.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id não encontrado")

    urgencia_service = get_urgencia_service(db)
    result = urgencia_service.resolver_urgencia(
        conversa_id=conversa_id,
        resolvido_por=user_id,
        nota=dados.nota
    )

    if result:
        return {"success": True, "message": "Urgência resolvida com sucesso"}
    else:
        raise HTTPException(status_code=500, detail="Erro ao resolver urgência")


@router.get("/conversas-urgentes")
async def listar_conversas_urgentes(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lista conversas com urgência não resolvida.

    Retorna dados da conversa junto com informações de urgência.
    """
    from sqlalchemy import text

    cliente_id = current_user.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=400, detail="cliente_id não encontrado")

    try:
        result = db.execute(text("""
            SELECT
                c.id,
                c.paciente_telefone,
                c.paciente_nome,
                c.status,
                c.urgencia_nivel,
                c.urgencia_motivo,
                c.urgencia_detectada_em,
                c.ultima_mensagem_at,
                (SELECT COUNT(*) FROM alertas_urgencia au
                 WHERE au.conversa_id = c.id AND au.resolvido = FALSE) as alertas_pendentes
            FROM conversas c
            WHERE c.cliente_id = :cliente_id
              AND c.urgencia_nivel != 'normal'
              AND c.urgencia_resolvida = FALSE
            ORDER BY
                CASE c.urgencia_nivel
                    WHEN 'critica' THEN 1
                    WHEN 'atencao' THEN 2
                    ELSE 3
                END,
                c.urgencia_detectada_em DESC
            LIMIT 50
        """), {"cliente_id": cliente_id})

        conversas = []
        for row in result:
            conversas.append({
                "id": row.id,
                "paciente_telefone": row.paciente_telefone,
                "paciente_nome": row.paciente_nome,
                "status": row.status,
                "urgencia_nivel": row.urgencia_nivel,
                "urgencia_motivo": row.urgencia_motivo,
                "urgencia_detectada_em": row.urgencia_detectada_em.isoformat() if row.urgencia_detectada_em else None,
                "ultima_mensagem_at": row.ultima_mensagem_at.isoformat() if row.ultima_mensagem_at else None,
                "alertas_pendentes": row.alertas_pendentes
            })

        return {
            "success": True,
            "conversas": conversas,
            "total": len(conversas)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar conversas urgentes: {str(e)}")
