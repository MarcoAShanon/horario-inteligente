"""
API Admin - Painel de Uso WhatsApp
Endpoints para visualizar uso de mensagens WhatsApp por cliente,
com estimativa de custo baseada nos preços da Meta (Brasil, julho 2025).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date
from typing import Optional
import logging

from app.database import get_db
from app.api.admin import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/whatsapp", tags=["Admin - WhatsApp"])


def _default_period():
    """Retorna primeiro dia do mês corrente e hoje."""
    today = date.today()
    return date(today.year, today.month, 1), today


@router.get("/stats")
async def whatsapp_stats(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Estatísticas globais de uso WhatsApp no período."""
    if not data_inicio or not data_fim:
        data_inicio, data_fim = _default_period()

    result = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE category = 'marketing') AS marketing,
            COUNT(*) FILTER (WHERE category = 'utility') AS utility,
            COUNT(*) FILTER (WHERE category = 'authentication') AS authentication,
            COUNT(*) FILTER (WHERE category = 'service') AS service,
            COALESCE(SUM(cost_usd), 0) AS cost_usd_total,
            COUNT(*) FILTER (WHERE success = true) AS total_success,
            COUNT(*) FILTER (WHERE success = false) AS total_failed
        FROM whatsapp_message_log
        WHERE created_at >= :inicio
          AND created_at < CAST(:fim AS date) + INTERVAL '1 day'
    """), {"inicio": data_inicio, "fim": data_fim})

    row = result.fetchone()

    # Obter cotação
    from app.services.exchange_rate_service import get_usd_brl_rate
    taxa = await get_usd_brl_rate()

    cost_usd = float(row.cost_usd_total)

    return {
        "periodo": {"inicio": str(data_inicio), "fim": str(data_fim)},
        "total_mensagens": row.total,
        "total_sucesso": row.total_success,
        "total_falha": row.total_failed,
        "por_categoria": {
            "marketing": row.marketing,
            "utility": row.utility,
            "authentication": row.authentication,
            "service": row.service,
        },
        "custo_usd": round(cost_usd, 2),
        "custo_brl": round(cost_usd * taxa, 2),
        "taxa_cambio": round(taxa, 4),
    }


@router.get("/uso-por-cliente")
async def uso_por_cliente(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Tabela de uso agregado por cliente."""
    if not data_inicio or not data_fim:
        data_inicio, data_fim = _default_period()

    offset = (page - 1) * per_page

    # Total de clientes com mensagens no período
    count_result = db.execute(text("""
        SELECT COUNT(DISTINCT wml.cliente_id)
        FROM whatsapp_message_log wml
        WHERE wml.created_at >= :inicio
          AND wml.created_at < CAST(:fim AS date) + INTERVAL '1 day'
          AND wml.cliente_id IS NOT NULL
    """), {"inicio": data_inicio, "fim": data_fim})
    total_clientes = count_result.scalar() or 0

    result = db.execute(text("""
        SELECT
            wml.cliente_id,
            c.nome AS cliente_nome,
            c.subdomain,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE wml.category = 'marketing') AS marketing,
            COUNT(*) FILTER (WHERE wml.category = 'utility') AS utility,
            COUNT(*) FILTER (WHERE wml.category = 'service') AS service,
            COALESCE(SUM(wml.cost_usd), 0) AS cost_usd
        FROM whatsapp_message_log wml
        LEFT JOIN clientes c ON c.id = wml.cliente_id
        WHERE wml.created_at >= :inicio
          AND wml.created_at < CAST(:fim AS date) + INTERVAL '1 day'
          AND wml.cliente_id IS NOT NULL
        GROUP BY wml.cliente_id, c.nome, c.subdomain
        ORDER BY cost_usd DESC
        LIMIT :limit OFFSET :offset
    """), {"inicio": data_inicio, "fim": data_fim, "limit": per_page, "offset": offset})

    rows = result.fetchall()

    from app.services.exchange_rate_service import get_usd_brl_rate
    taxa = await get_usd_brl_rate()

    clientes = []
    for row in rows:
        cost_usd = float(row.cost_usd)
        clientes.append({
            "cliente_id": row.cliente_id,
            "cliente_nome": row.cliente_nome or f"Cliente #{row.cliente_id}",
            "subdomain": row.subdomain,
            "total": row.total,
            "marketing": row.marketing,
            "utility": row.utility,
            "service": row.service,
            "custo_usd": round(cost_usd, 4),
            "custo_brl": round(cost_usd * taxa, 2),
        })

    return {
        "periodo": {"inicio": str(data_inicio), "fim": str(data_fim)},
        "total_clientes": total_clientes,
        "page": page,
        "per_page": per_page,
        "taxa_cambio": round(taxa, 4),
        "clientes": clientes,
    }


@router.get("/cliente/{cliente_id}")
async def detalhe_cliente(
    cliente_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Detalhe de mensagens de um cliente específico."""
    if not data_inicio or not data_fim:
        data_inicio, data_fim = _default_period()

    # Info do cliente
    cliente_result = db.execute(text(
        "SELECT nome, subdomain FROM clientes WHERE id = :cid"
    ), {"cid": cliente_id}).fetchone()

    cliente_nome = cliente_result.nome if cliente_result else f"Cliente #{cliente_id}"
    subdomain = cliente_result.subdomain if cliente_result else None

    # Mensagens
    result = db.execute(text("""
        SELECT
            id, template_name, message_type, category,
            phone_to, success, message_id, cost_usd, created_at
        FROM whatsapp_message_log
        WHERE cliente_id = :cid
          AND created_at >= :inicio
          AND created_at < CAST(:fim AS date) + INTERVAL '1 day'
        ORDER BY created_at DESC
        LIMIT 500
    """), {"cid": cliente_id, "inicio": data_inicio, "fim": data_fim})

    rows = result.fetchall()

    from app.services.exchange_rate_service import get_usd_brl_rate
    taxa = await get_usd_brl_rate()

    mensagens = []
    total_usd = 0.0
    for row in rows:
        cost = float(row.cost_usd)
        total_usd += cost
        mensagens.append({
            "id": row.id,
            "template_name": row.template_name,
            "message_type": row.message_type,
            "category": row.category,
            "phone_to": row.phone_to,
            "success": row.success,
            "message_id": row.message_id,
            "cost_usd": round(cost, 6),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })

    return {
        "cliente_id": cliente_id,
        "cliente_nome": cliente_nome,
        "subdomain": subdomain,
        "periodo": {"inicio": str(data_inicio), "fim": str(data_fim)},
        "total_mensagens": len(mensagens),
        "custo_usd": round(total_usd, 4),
        "custo_brl": round(total_usd * taxa, 2),
        "taxa_cambio": round(taxa, 4),
        "mensagens": mensagens,
    }


@router.get("/taxa-cambio")
async def taxa_cambio(admin=Depends(get_current_admin)):
    """Retorna cotação USD→BRL atual."""
    from app.services.exchange_rate_service import get_usd_brl_rate
    taxa = await get_usd_brl_rate()
    return {"usd_brl": round(taxa, 4)}
