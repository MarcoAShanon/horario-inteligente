"""
API de Gestao de Convites de Clientes - Painel Admin
Endpoints para gerar, listar e revogar convites de registro
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
import secrets

from app.database import get_db
from app.api.admin import get_current_admin
from app.services.email_service import get_email_service

router = APIRouter(prefix="/api/admin/convites", tags=["Admin - Convites"])
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

class ConviteCreate(BaseModel):
    """Dados para gerar novo convite"""
    email_destino: Optional[EmailStr] = Field(None, description="Email do prospect")
    nome_destino: Optional[str] = Field(None, max_length=255, description="Nome do prospect")
    telefone_destino: Optional[str] = Field(None, max_length=20, description="Telefone do prospect")
    observacoes: Optional[str] = Field(None, max_length=500, description="Observacoes internas")
    parceiro_id: Optional[int] = Field(None, description="ID do parceiro comercial vinculado")
    enviar_email: bool = Field(False, description="Enviar convite por email ao prospect")


# ==================== ENDPOINTS ====================

@router.post("")
async def gerar_convite(
    dados: ConviteCreate,
    request: Request,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Gera novo convite personalizado para registro de cliente.
    Token de 48 bytes, expira em 30 dias.
    """
    try:
        token = secrets.token_urlsafe(48)
        agora = datetime.now()
        expira_em = agora + timedelta(days=30)

        result = db.execute(
            text("""
                INSERT INTO convites_clientes (
                    token, email_destino, nome_destino, telefone_destino,
                    observacoes, criado_por_id, criado_por_tipo, parceiro_id,
                    expira_em, criado_em
                ) VALUES (
                    :token, :email_destino, :nome_destino, :telefone_destino,
                    :observacoes, :criado_por_id, 'admin', :parceiro_id,
                    :expira_em, :criado_em
                )
                RETURNING id
            """),
            {
                "token": token,
                "email_destino": dados.email_destino,
                "nome_destino": dados.nome_destino,
                "telefone_destino": dados.telefone_destino,
                "observacoes": dados.observacoes,
                "criado_por_id": admin.get("id"),
                "parceiro_id": dados.parceiro_id,
                "expira_em": expira_em,
                "criado_em": agora
            }
        )
        convite_id = result.fetchone()[0]
        db.commit()

        url_convite = f"https://horariointeligente.com.br/static/registro-cliente.html?token={token}"

        logger.info(f"[Convites] Convite gerado: ID={convite_id}, destino={dados.email_destino or 'generico'}")

        # Enviar email se solicitado e email informado
        email_enviado = False
        if dados.enviar_email and dados.email_destino:
            try:
                email_service = get_email_service()
                email_enviado = email_service.send_convite_registro(
                    to_email=dados.email_destino,
                    to_name=dados.nome_destino or "Prezado(a)",
                    url_convite=url_convite
                )
            except Exception as e:
                logger.warning(f"[Convites] Erro ao enviar email de convite: {e}")

        return {
            "success": True,
            "convite": {
                "id": convite_id,
                "token": token,
                "url": url_convite,
                "expira_em": expira_em.isoformat(),
                "email_enviado": email_enviado
            }
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[Convites] Erro ao gerar convite: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar convite: {str(e)}")


@router.get("")
async def listar_convites(
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filtro: pendente, usado, expirado"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Lista convites com paginacao e filtro por status.
    """
    try:
        # Buscar convites
        query = """
            SELECT id, token, email_destino, nome_destino, telefone_destino,
                   observacoes, criado_por_id, parceiro_id,
                   usado, usado_em, cliente_id, expira_em, criado_em
            FROM convites_clientes
        """
        params = {"limit": limit, "skip": skip}

        # Filtrar por status
        agora_utc = datetime.now(timezone.utc)
        if status == 'usado':
            query += " WHERE usado = true"
        elif status == 'expirado':
            query += " WHERE usado = false AND expira_em < :agora"
            params["agora"] = agora_utc
        elif status == 'pendente':
            query += " WHERE usado = false AND expira_em >= :agora"
            params["agora"] = agora_utc

        query += " ORDER BY criado_em DESC LIMIT :limit OFFSET :skip"

        result = db.execute(text(query), params).fetchall()

        convites = []
        for row in result:
            expira_em = row[11]
            if expira_em and expira_em.tzinfo is None:
                expira_em = expira_em.replace(tzinfo=timezone.utc)

            usado = row[8]
            if usado:
                row_status = 'usado'
            elif expira_em and expira_em < agora_utc:
                row_status = 'expirado'
            else:
                row_status = 'pendente'

            convites.append({
                "id": row[0],
                "token": row[1],
                "email_destino": row[2],
                "nome_destino": row[3],
                "telefone_destino": row[4],
                "observacoes": row[5],
                "criado_por_id": row[6],
                "parceiro_id": row[7],
                "usado": usado,
                "usado_em": row[9].isoformat() if row[9] else None,
                "cliente_id": row[10],
                "expira_em": row[11].isoformat() if row[11] else None,
                "criado_em": row[12].isoformat() if row[12] else None,
                "status": row_status,
                "url": f"https://horariointeligente.com.br/static/registro-cliente.html?token={row[1]}"
            })

        # Total para paginacao
        count_query = "SELECT COUNT(*) FROM convites_clientes"
        if status == 'usado':
            count_query += " WHERE usado = true"
        elif status == 'expirado':
            count_query += " WHERE usado = false AND expira_em < :agora"
        elif status == 'pendente':
            count_query += " WHERE usado = false AND expira_em >= :agora"

        count_params = {}
        if status in ('expirado', 'pendente'):
            count_params["agora"] = agora_utc

        total = db.execute(text(count_query), count_params).scalar()

        return {
            "convites": convites,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"[Convites] Erro ao listar convites: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao listar convites: {str(e)}")


@router.delete("/{convite_id}")
async def revogar_convite(
    convite_id: int,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Revoga um convite nao utilizado (deleta do banco).
    """
    try:
        # Verificar se convite existe e nao foi usado
        convite = db.execute(
            text("SELECT id, usado FROM convites_clientes WHERE id = :id"),
            {"id": convite_id}
        ).fetchone()

        if not convite:
            raise HTTPException(status_code=404, detail="Convite nao encontrado")

        if convite[1]:  # usado
            raise HTTPException(status_code=400, detail="Nao e possivel revogar um convite ja utilizado")

        db.execute(
            text("DELETE FROM convites_clientes WHERE id = :id"),
            {"id": convite_id}
        )
        db.commit()

        logger.info(f"[Convites] Convite {convite_id} revogado pelo admin {admin.get('id')}")

        return {"success": True, "message": "Convite revogado com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Convites] Erro ao revogar convite: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao revogar convite: {str(e)}")
