"""
API de Pre-Cadastro de Parceiro Comercial (Auto-Registro)
Endpoint publico para futuros parceiros se registrarem.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Optional
import logging
import re
from html import escape as html_escape

from app.database import get_db
from app.services.email_service import get_email_service

# Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/parceiro", tags=["Registro Parceiro"])
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

class ParceiroRegistroCreate(BaseModel):
    """Schema para auto-registro de parceiro"""
    nome: str = Field(..., min_length=3, max_length=255, description="Nome completo ou razao social")
    tipo_pessoa: str = Field(..., description="PF ou PJ")
    cpf_cnpj: str = Field(..., min_length=11, max_length=18, description="CPF ou CNPJ")
    email: EmailStr = Field(..., description="Email valido")
    telefone: str = Field(..., min_length=10, max_length=16, description="Telefone com DDD")
    endereco: Optional[str] = Field(None, max_length=500, description="Endereco completo")

    @validator('tipo_pessoa')
    def validar_tipo_pessoa(cls, v):
        if v not in ('PF', 'PJ'):
            raise ValueError('Tipo de pessoa deve ser PF ou PJ')
        return v

    @validator('cpf_cnpj')
    def validar_cpf_cnpj(cls, v, values):
        numeros = re.sub(r'\D', '', v)
        tipo = values.get('tipo_pessoa', 'PF')
        if tipo == 'PF' and len(numeros) != 11:
            raise ValueError('CPF deve ter 11 digitos')
        if tipo == 'PJ' and len(numeros) != 14:
            raise ValueError('CNPJ deve ter 14 digitos')
        return v

    @validator('telefone')
    def validar_telefone(cls, v):
        numeros = re.sub(r'\D', '', v)
        if len(numeros) < 10 or len(numeros) > 11:
            raise ValueError('Telefone deve ter 10 ou 11 digitos')
        return v


# ==================== ENDPOINTS ====================

@router.post("/registro", status_code=201)
@limiter.limit("5/minute")
async def registrar_parceiro(
    request: Request,
    dados: ParceiroRegistroCreate,
    db: Session = Depends(get_db)
):
    """
    Registro publico de parceiro comercial.

    - Rate limit: 5 requisicoes por minuto por IP
    - Email e CPF/CNPJ devem ser unicos
    - Cria parceiro com status 'pendente_aprovacao'
    - Notifica admin via email e Telegram
    """
    try:
        email_lower = dados.email.lower().strip()

        # Verificar unicidade de email
        existente_email = db.execute(
            text("SELECT id FROM parceiros_comerciais WHERE email = :email"),
            {"email": email_lower}
        ).fetchone()
        if existente_email:
            raise HTTPException(
                status_code=409,
                detail="Este email ja esta cadastrado."
            )

        # Verificar unicidade de cpf_cnpj
        existente_doc = db.execute(
            text("SELECT id FROM parceiros_comerciais WHERE cpf_cnpj = :cpf_cnpj"),
            {"cpf_cnpj": dados.cpf_cnpj}
        ).fetchone()
        if existente_doc:
            raise HTTPException(
                status_code=409,
                detail="Este CPF/CNPJ ja esta cadastrado."
            )

        # Sanitizar inputs
        nome_sanitizado = html_escape(dados.nome.strip())
        endereco_sanitizado = html_escape(dados.endereco.strip()) if dados.endereco else None

        agora = datetime.now()

        # INSERT com status pendente_aprovacao, sem token, sem senha, comissao 0
        result = db.execute(
            text("""
                INSERT INTO parceiros_comerciais (
                    nome, tipo_pessoa, cpf_cnpj, email, telefone, endereco,
                    percentual_comissao, tipo_comissao, ativo,
                    status, criado_em, atualizado_em
                ) VALUES (
                    :nome, :tipo_pessoa, :cpf_cnpj, :email, :telefone, :endereco,
                    0, 'percentual', true,
                    'pendente_aprovacao', :criado_em, :atualizado_em
                )
                RETURNING id
            """),
            {
                "nome": nome_sanitizado,
                "tipo_pessoa": dados.tipo_pessoa,
                "cpf_cnpj": dados.cpf_cnpj,
                "email": email_lower,
                "telefone": dados.telefone.strip(),
                "endereco": endereco_sanitizado,
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        parceiro_id = result.fetchone()[0]
        db.commit()

        logger.info(f"[RegistroParceiro] Novo pre-cadastro: ID={parceiro_id}, nome={nome_sanitizado}")

        # Notificar admin via email e Telegram
        try:
            email_service = get_email_service()

            # Notificacao Telegram (escapar caracteres Markdown)
            def escape_md(text: str) -> str:
                """Escapa caracteres especiais do Markdown do Telegram"""
                for ch in ('_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'):
                    text = text.replace(ch, f'\\{ch}')
                return text

            mensagem_telegram = (
                f"🤝 *Novo Parceiro Pré\\-Cadastrado*\n\n"
                f"*Nome:* {escape_md(dados.nome)}\n"
                f"*Tipo:* {escape_md(dados.tipo_pessoa)}\n"
                f"*Email:* {escape_md(email_lower)}\n"
                f"*Telefone:* {escape_md(dados.telefone)}\n"
                f"*Data:* {escape_md(agora.strftime('%d/%m/%Y %H:%M'))}\n\n"
                f"Acesse o painel para revisar e aprovar\\."
            )
            email_service.send_telegram_notification(mensagem_telegram)
        except Exception as e:
            logger.warning(f"[RegistroParceiro] Erro ao notificar admin: {e}")

        return {
            "sucesso": True,
            "mensagem": "Cadastro enviado com sucesso! Aguarde a aprovacao do administrador."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RegistroParceiro] Erro ao registrar parceiro: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar cadastro. Tente novamente."
        )
