"""
API de Gestão de Comissões - Painel Admin
Endpoints para gerenciar comissões de parceiros comerciais
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel
import logging

from app.database import get_db
from app.api.admin import get_current_admin

router = APIRouter(prefix="/api/admin/comissoes", tags=["Admin - Comissões"])
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

class ComissaoAprovar(BaseModel):
    """Dados para aprovar comissão"""
    observacoes: Optional[str] = None


class ComissaoPagar(BaseModel):
    """Dados para marcar comissão como paga"""
    asaas_transfer_id: Optional[str] = None
    comprovante_url: Optional[str] = None
    observacoes: Optional[str] = None


class ComissaoCancelar(BaseModel):
    """Dados para cancelar comissão"""
    motivo: str


class PagamentoLote(BaseModel):
    """Dados para pagamento em lote"""
    comissao_ids: List[int]
    observacoes: Optional[str] = None


# ==================== ENDPOINTS ====================

@router.get("")
async def listar_comissoes(
    status: Optional[str] = Query(None, description="Filtrar por status: pendente, aprovada, paga, cancelada"),
    parceiro_id: Optional[int] = Query(None, description="Filtrar por parceiro"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    data_inicio: Optional[date] = Query(None, description="Data início do período"),
    data_fim: Optional[date] = Query(None, description="Data fim do período"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lista todas as comissões com filtros opcionais"""
    try:
        # Construir query base
        conditions = []
        params = {}

        if status:
            conditions.append("c.status = :status")
            params["status"] = status

        if parceiro_id:
            conditions.append("c.parceiro_id = :parceiro_id")
            params["parceiro_id"] = parceiro_id

        if cliente_id:
            conditions.append("c.cliente_id = :cliente_id")
            params["cliente_id"] = cliente_id

        if data_inicio:
            conditions.append("c.created_at >= :data_inicio")
            params["data_inicio"] = data_inicio

        if data_fim:
            conditions.append("c.created_at <= :data_fim")
            params["data_fim"] = data_fim

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Contar total
        count_query = text(f"""
            SELECT COUNT(*) FROM comissoes c WHERE {where_clause}
        """)
        total = db.execute(count_query, params).scalar()

        # Buscar registros
        offset = (page - 1) * per_page
        params["limit"] = per_page
        params["offset"] = offset

        query = text(f"""
            SELECT
                c.id, c.parceiro_id, c.cliente_id, c.assinatura_id,
                c.valor_base, c.percentual_aplicado, c.valor_comissao,
                c.mes_referencia, c.data_referencia, c.status,
                c.data_pagamento, c.asaas_transfer_id, c.comprovante_url,
                c.observacoes, c.created_at, c.updated_at,
                p.nome as parceiro_nome,
                cl.nome as cliente_nome
            FROM comissoes c
            LEFT JOIN parceiros_comerciais p ON c.parceiro_id = p.id
            LEFT JOIN clientes cl ON c.cliente_id = cl.id
            WHERE {where_clause}
            ORDER BY c.created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        result = db.execute(query, params).fetchall()

        comissoes = []
        for row in result:
            comissoes.append({
                "id": row[0],
                "parceiro_id": row[1],
                "cliente_id": row[2],
                "assinatura_id": row[3],
                "valor_base": float(row[4]) if row[4] else 0,
                "percentual_aplicado": float(row[5]) if row[5] else 0,
                "valor_comissao": float(row[6]) if row[6] else 0,
                "mes_referencia": row[7],
                "data_referencia": row[8].isoformat() if row[8] else None,
                "status": row[9],
                "data_pagamento": row[10].isoformat() if row[10] else None,
                "asaas_transfer_id": row[11],
                "comprovante_url": row[12],
                "observacoes": row[13],
                "created_at": row[14].isoformat() if row[14] else None,
                "updated_at": row[15].isoformat() if row[15] else None,
                "parceiro_nome": row[16],
                "cliente_nome": row[17]
            })

        return {
            "comissoes": comissoes,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }

    except Exception as e:
        logger.error(f"[Comissões] Erro ao listar comissões: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao listar comissões")


@router.get("/resumo")
async def resumo_comissoes(
    parceiro_id: Optional[int] = Query(None, description="Filtrar por parceiro"),
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Retorna resumo de comissões por status e totais"""
    try:
        params = {}
        where_parceiro = ""
        if parceiro_id:
            where_parceiro = "WHERE parceiro_id = :parceiro_id"
            params["parceiro_id"] = parceiro_id

        # Totais por status
        query_status = text(f"""
            SELECT
                status,
                COUNT(*) as quantidade,
                COALESCE(SUM(valor_comissao), 0) as total
            FROM comissoes
            {where_parceiro}
            GROUP BY status
        """)
        result_status = db.execute(query_status, params).fetchall()

        totais_por_status = {}
        total_geral = 0
        quantidade_total = 0
        for row in result_status:
            totais_por_status[row[0]] = {
                "quantidade": row[1],
                "total": float(row[2])
            }
            total_geral += float(row[2])
            quantidade_total += row[1]

        # Top parceiros (se não filtrado)
        top_parceiros = []
        if not parceiro_id:
            query_top = text("""
                SELECT
                    p.id, p.nome,
                    COUNT(c.id) as total_comissoes,
                    COALESCE(SUM(CASE WHEN c.status = 'pendente' THEN c.valor_comissao ELSE 0 END), 0) as pendente,
                    COALESCE(SUM(CASE WHEN c.status = 'paga' THEN c.valor_comissao ELSE 0 END), 0) as pago
                FROM parceiros_comerciais p
                LEFT JOIN comissoes c ON p.id = c.parceiro_id
                WHERE p.ativo = true
                GROUP BY p.id, p.nome
                ORDER BY pendente DESC
                LIMIT 10
            """)
            result_top = db.execute(query_top).fetchall()
            for row in result_top:
                top_parceiros.append({
                    "id": row[0],
                    "nome": row[1],
                    "total_comissoes": row[2],
                    "valor_pendente": float(row[3]),
                    "valor_pago": float(row[4])
                })

        return {
            "totais_por_status": totais_por_status,
            "total_geral": total_geral,
            "quantidade_total": quantidade_total,
            "top_parceiros": top_parceiros
        }

    except Exception as e:
        logger.error(f"[Comissões] Erro ao gerar resumo: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar resumo")


@router.get("/parceiro/{parceiro_id}")
async def comissoes_parceiro(
    parceiro_id: int,
    status: Optional[str] = None,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lista comissões de um parceiro específico com resumo"""
    try:
        # Verificar se parceiro existe
        parceiro = db.execute(
            text("SELECT id, nome, percentual_comissao FROM parceiros_comerciais WHERE id = :id"),
            {"id": parceiro_id}
        ).fetchone()

        if not parceiro:
            raise HTTPException(status_code=404, detail="Parceiro não encontrado")

        # Buscar comissões
        conditions = ["c.parceiro_id = :parceiro_id"]
        params = {"parceiro_id": parceiro_id}

        if status:
            conditions.append("c.status = :status")
            params["status"] = status

        where_clause = " AND ".join(conditions)

        query = text(f"""
            SELECT
                c.id, c.cliente_id, c.assinatura_id,
                c.valor_base, c.percentual_aplicado, c.valor_comissao,
                c.mes_referencia, c.data_referencia, c.status,
                c.data_pagamento, c.created_at,
                cl.nome as cliente_nome
            FROM comissoes c
            LEFT JOIN clientes cl ON c.cliente_id = cl.id
            WHERE {where_clause}
            ORDER BY c.created_at DESC
        """)

        result = db.execute(query, params).fetchall()

        comissoes = []
        total_pendente = 0
        total_pago = 0
        for row in result:
            comissao = {
                "id": row[0],
                "cliente_id": row[1],
                "assinatura_id": row[2],
                "valor_base": float(row[3]) if row[3] else 0,
                "percentual_aplicado": float(row[4]) if row[4] else 0,
                "valor_comissao": float(row[5]) if row[5] else 0,
                "mes_referencia": row[6],
                "data_referencia": row[7].isoformat() if row[7] else None,
                "status": row[8],
                "data_pagamento": row[9].isoformat() if row[9] else None,
                "created_at": row[10].isoformat() if row[10] else None,
                "cliente_nome": row[11]
            }
            comissoes.append(comissao)

            if row[8] == 'pendente':
                total_pendente += float(row[5]) if row[5] else 0
            elif row[8] == 'paga':
                total_pago += float(row[5]) if row[5] else 0

        return {
            "parceiro": {
                "id": parceiro[0],
                "nome": parceiro[1],
                "percentual_comissao": float(parceiro[2]) if parceiro[2] else 0
            },
            "comissoes": comissoes,
            "total": len(comissoes),
            "resumo": {
                "total_pendente": total_pendente,
                "total_pago": total_pago
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Comissões] Erro ao buscar comissões do parceiro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar comissões do parceiro")


@router.post("/{comissao_id}/aprovar")
async def aprovar_comissao(
    comissao_id: int,
    dados: ComissaoAprovar = None,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Aprova uma comissão pendente"""
    try:
        # Verificar se comissão existe e está pendente
        comissao = db.execute(
            text("SELECT id, status, valor_comissao FROM comissoes WHERE id = :id"),
            {"id": comissao_id}
        ).fetchone()

        if not comissao:
            raise HTTPException(status_code=404, detail="Comissão não encontrada")

        if comissao[1] != 'pendente':
            raise HTTPException(status_code=400, detail=f"Comissão não está pendente (status atual: {comissao[1]})")

        # Atualizar status
        observacoes = dados.observacoes if dados else None
        db.execute(
            text("""
                UPDATE comissoes
                SET status = 'aprovada',
                    observacoes = COALESCE(:obs, observacoes),
                    updated_at = :updated_at
                WHERE id = :id
            """),
            {
                "id": comissao_id,
                "obs": observacoes,
                "updated_at": datetime.now()
            }
        )
        db.commit()

        logger.info(f"[Comissões] Comissão {comissao_id} aprovada por admin {admin.get('id')}")

        return {
            "success": True,
            "message": "Comissão aprovada com sucesso",
            "comissao_id": comissao_id,
            "valor": float(comissao[2])
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Comissões] Erro ao aprovar comissão: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao aprovar comissão")


@router.post("/{comissao_id}/pagar")
async def pagar_comissao(
    comissao_id: int,
    dados: ComissaoPagar = None,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Marca uma comissão como paga"""
    try:
        # Verificar se comissão existe e está aprovada ou pendente
        comissao = db.execute(
            text("SELECT id, status, valor_comissao FROM comissoes WHERE id = :id"),
            {"id": comissao_id}
        ).fetchone()

        if not comissao:
            raise HTTPException(status_code=404, detail="Comissão não encontrada")

        if comissao[1] not in ('pendente', 'aprovada'):
            raise HTTPException(status_code=400, detail=f"Comissão não pode ser paga (status atual: {comissao[1]})")

        # Atualizar status
        agora = datetime.now()
        params = {
            "id": comissao_id,
            "data_pagamento": agora,
            "updated_at": agora,
            "asaas_transfer_id": dados.asaas_transfer_id if dados else None,
            "comprovante_url": dados.comprovante_url if dados else None,
            "obs": dados.observacoes if dados else None
        }

        db.execute(
            text("""
                UPDATE comissoes
                SET status = 'paga',
                    data_pagamento = :data_pagamento,
                    asaas_transfer_id = COALESCE(:asaas_transfer_id, asaas_transfer_id),
                    comprovante_url = COALESCE(:comprovante_url, comprovante_url),
                    observacoes = COALESCE(:obs, observacoes),
                    updated_at = :updated_at
                WHERE id = :id
            """),
            params
        )
        db.commit()

        logger.info(f"[Comissões] Comissão {comissao_id} paga por admin {admin.get('id')}")

        return {
            "success": True,
            "message": "Comissão marcada como paga",
            "comissao_id": comissao_id,
            "valor": float(comissao[2]),
            "data_pagamento": agora.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Comissões] Erro ao pagar comissão: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar pagamento")


@router.post("/{comissao_id}/cancelar")
async def cancelar_comissao(
    comissao_id: int,
    dados: ComissaoCancelar,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cancela uma comissão"""
    try:
        # Verificar se comissão existe e não está paga
        comissao = db.execute(
            text("SELECT id, status FROM comissoes WHERE id = :id"),
            {"id": comissao_id}
        ).fetchone()

        if not comissao:
            raise HTTPException(status_code=404, detail="Comissão não encontrada")

        if comissao[1] == 'paga':
            raise HTTPException(status_code=400, detail="Não é possível cancelar uma comissão já paga")

        if comissao[1] == 'cancelada':
            raise HTTPException(status_code=400, detail="Comissão já está cancelada")

        # Atualizar status
        db.execute(
            text("""
                UPDATE comissoes
                SET status = 'cancelada',
                    observacoes = :obs,
                    updated_at = :updated_at
                WHERE id = :id
            """),
            {
                "id": comissao_id,
                "obs": f"Cancelada: {dados.motivo}",
                "updated_at": datetime.now()
            }
        )
        db.commit()

        logger.info(f"[Comissões] Comissão {comissao_id} cancelada por admin {admin.get('id')}. Motivo: {dados.motivo}")

        return {
            "success": True,
            "message": "Comissão cancelada",
            "comissao_id": comissao_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Comissões] Erro ao cancelar comissão: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao cancelar comissão")


@router.post("/pagar-lote")
async def pagar_comissoes_lote(
    dados: PagamentoLote,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Paga múltiplas comissões de uma vez"""
    try:
        if not dados.comissao_ids:
            raise HTTPException(status_code=400, detail="Nenhuma comissão informada")

        # Verificar comissões
        placeholders = ", ".join([f":id{i}" for i in range(len(dados.comissao_ids))])
        params = {f"id{i}": cid for i, cid in enumerate(dados.comissao_ids)}

        comissoes = db.execute(
            text(f"""
                SELECT id, status, valor_comissao
                FROM comissoes
                WHERE id IN ({placeholders})
            """),
            params
        ).fetchall()

        if len(comissoes) != len(dados.comissao_ids):
            raise HTTPException(status_code=400, detail="Uma ou mais comissões não encontradas")

        # Verificar se todas podem ser pagas
        nao_pagaveis = [c for c in comissoes if c[1] not in ('pendente', 'aprovada')]
        if nao_pagaveis:
            raise HTTPException(
                status_code=400,
                detail=f"Comissões não podem ser pagas: {[c[0] for c in nao_pagaveis]}"
            )

        # Atualizar todas
        agora = datetime.now()
        params["data_pagamento"] = agora
        params["updated_at"] = agora
        params["obs"] = dados.observacoes

        db.execute(
            text(f"""
                UPDATE comissoes
                SET status = 'paga',
                    data_pagamento = :data_pagamento,
                    observacoes = COALESCE(:obs, observacoes),
                    updated_at = :updated_at
                WHERE id IN ({placeholders})
            """),
            params
        )
        db.commit()

        total_pago = sum(float(c[2]) for c in comissoes)
        logger.info(f"[Comissões] {len(comissoes)} comissões pagas em lote por admin {admin.get('id')}. Total: R${total_pago:.2f}")

        return {
            "success": True,
            "message": f"{len(comissoes)} comissões pagas com sucesso",
            "quantidade": len(comissoes),
            "total_pago": total_pago,
            "data_pagamento": agora.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Comissões] Erro ao pagar comissões em lote: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar pagamento em lote")
