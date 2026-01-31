"""
API de Ativacao de Conta do Parceiro - Aceite de Termo de Parceria
Endpoints publicos (sem autenticacao) para ativacao de contas de parceiros
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import logging
import secrets
import bcrypt

from app.database import get_db
from app.services.email_service import get_email_service

router = APIRouter(prefix="/api/parceiro/ativacao", tags=["Ativacao Parceiro"])
logger = logging.getLogger(__name__)

# Versao atual do termo de parceria
VERSAO_TERMO_PARCERIA = "1.0"


# ==================== SCHEMAS ====================

class AceiteParceiroRequest(BaseModel):
    senha: Optional[str] = None
    confirmar_senha: Optional[str] = None
    aceite_termo: bool


class ReenviarParceiroRequest(BaseModel):
    email: str


# ==================== ENDPOINTS ====================
# IMPORTANTE: rotas fixas (/reenviar) devem vir ANTES das rotas com path param (/{token})

@router.post("/reenviar")
async def reenviar_ativacao_parceiro(
    dados: ReenviarParceiroRequest,
    db: Session = Depends(get_db)
):
    """
    Reenvia email de ativacao para parceiro gerando novo token.
    Apenas para parceiros com status pendente_aceite.
    """
    try:
        result = db.execute(
            text("""
                SELECT id, nome, email, status, percentual_comissao, recorrencia_comissao_meses
                FROM parceiros_comerciais
                WHERE email = :email
            """),
            {"email": dados.email}
        ).fetchone()

        if not result:
            return {"sucesso": True, "mensagem": "Se o email estiver cadastrado, um novo link sera enviado."}

        parceiro_id, nome, email, status, percentual, recorrencia = result

        if status != 'pendente_aceite':
            return {"sucesso": True, "mensagem": "Se o email estiver cadastrado, um novo link sera enviado."}

        # Gerar novo token e codigo de ativacao curto
        novo_token = secrets.token_urlsafe(64)
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        novo_codigo = ''.join([chars[secrets.randbelow(len(chars))] for _ in range(8)])
        expira_em = datetime.now() + timedelta(days=7)

        db.execute(
            text("""
                UPDATE parceiros_comerciais SET
                    token_ativacao = :token,
                    codigo_ativacao = :codigo,
                    token_expira_em = :expira_em,
                    atualizado_em = NOW()
                WHERE id = :id
            """),
            {
                "id": parceiro_id,
                "token": novo_token,
                "codigo": novo_codigo,
                "expira_em": expira_em
            }
        )
        db.commit()

        # Enviar email com template limpo
        try:
            email_service = get_email_service()
            email_service.send_ativacao_parceiro(
                email, nome, novo_codigo,
                percentual_comissao=float(percentual) if percentual else 0,
                recorrencia_meses=recorrencia
            )
        except Exception as e:
            logger.warning(f"[AtivacaoParceiro] Erro ao enviar email: {e}")

        logger.info(f"[AtivacaoParceiro] Email de ativacao reenviado para {email}")

        return {
            "sucesso": True,
            "mensagem": "Se o email estiver cadastrado, um novo link sera enviado."
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[AtivacaoParceiro] Erro ao reenviar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao processar reenvio")


@router.get("/{token}")
async def obter_dados_ativacao_parceiro(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Retorna dados do parceiro para exibicao na pagina de ativacao.
    Endpoint publico (sem autenticacao).
    """
    try:
        result = db.execute(
            text("""
                SELECT id, nome, email, cpf_cnpj, telefone, status,
                       token_expira_em, percentual_comissao, tipo_comissao,
                       recorrencia_comissao_meses, recorrencia_renovavel,
                       senha_hash
                FROM parceiros_comerciais
                WHERE codigo_ativacao = :token OR token_ativacao = :token
            """),
            {"token": token}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Token de ativacao invalido")

        (parceiro_id, nome, email, documento, telefone, status,
         token_expira, percentual, tipo_comissao,
         recorrencia_meses, recorrencia_renovavel, senha_hash_existente) = result

        # Verificar se ja ativou
        if status != 'pendente_aceite':
            raise HTTPException(status_code=409, detail="Esta conta ja foi ativada")

        # Verificar se token expirou
        if token_expira and datetime.now(token_expira.tzinfo) > token_expira:
            raise HTTPException(status_code=410, detail="Link de ativacao expirado. Solicite um novo.")

        # Descricao da recorrencia
        if recorrencia_meses is None:
            descricao_recorrencia = "Permanente (enquanto o cliente estiver ativo)"
        elif recorrencia_renovavel:
            descricao_recorrencia = f"{recorrencia_meses} meses por cliente (renovavel)"
        else:
            descricao_recorrencia = f"{recorrencia_meses} meses por cliente"

        return {
            "parceiro": {
                "nome": nome,
                "email": email,
                "documento": documento,
                "telefone": telefone
            },
            "condicoes": {
                "percentual_comissao": float(percentual) if percentual else 0,
                "tipo_comissao": tipo_comissao or "percentual",
                "recorrencia_comissao_meses": recorrencia_meses,
                "recorrencia_renovavel": bool(recorrencia_renovavel),
                "descricao_recorrencia": descricao_recorrencia
            },
            "versao_termo": VERSAO_TERMO_PARCERIA,
            "senha_provisoria": senha_hash_existente is not None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AtivacaoParceiro] Erro ao obter dados: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar ativacao")


@router.post("/{token}")
async def processar_ativacao_parceiro(
    token: str,
    dados: AceiteParceiroRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Processa ativacao do parceiro: define senha + aceita termo de parceria.
    Endpoint publico (sem autenticacao).
    """
    try:
        # Validar aceite
        if not dados.aceite_termo:
            raise HTTPException(
                status_code=400,
                detail="E necessario aceitar o Termo de Parceria Comercial"
            )

        # Buscar parceiro pelo codigo_ativacao ou token_ativacao (compatibilidade)
        result = db.execute(
            text("""
                SELECT id, nome, email, status, token_expira_em, senha_hash
                FROM parceiros_comerciais
                WHERE codigo_ativacao = :token OR token_ativacao = :token
            """),
            {"token": token}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Token de ativacao invalido")

        parceiro_id, nome, email, status, token_expira, senha_hash_existente = result

        # Verificar se ja ativou
        if status != 'pendente_aceite':
            raise HTTPException(status_code=409, detail="Esta conta ja foi ativada")

        # Verificar se token expirou
        if token_expira and datetime.now(token_expira.tzinfo) > token_expira:
            raise HTTPException(status_code=410, detail="Link de ativacao expirado. Solicite um novo.")

        # Validar senha: se ja tem senha_hash (provisoria), pular validacao de senha
        if senha_hash_existente:
            # Senha provisoria ja definida na aprovacao, nao sobrescrever
            senha_hash_final = senha_hash_existente
        else:
            # Fluxo original: exigir e validar senha
            if not dados.senha or not dados.confirmar_senha:
                raise HTTPException(status_code=400, detail="Senha e confirmacao sao obrigatorias")
            if len(dados.senha) < 6:
                raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres")
            if dados.senha != dados.confirmar_senha:
                raise HTTPException(status_code=400, detail="As senhas nao conferem")
            senha_hash_final = bcrypt.hashpw(dados.senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Obter dados do request
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        agora = datetime.now()

        # Atualizar parceiro
        db.execute(
            text("""
                UPDATE parceiros_comerciais SET
                    senha_hash = :senha_hash,
                    status = 'ativo',
                    token_ativacao = NULL,
                    token_expira_em = NULL,
                    codigo_ativacao = NULL,
                    aceite_termo_em = :aceite_em,
                    aceite_termo_ip = :ip,
                    aceite_termo_user_agent = :user_agent,
                    aceite_termo_versao = :versao_termo,
                    atualizado_em = :atualizado_em
                WHERE id = :id
            """),
            {
                "id": parceiro_id,
                "senha_hash": senha_hash_final,
                "aceite_em": agora,
                "ip": client_ip,
                "user_agent": user_agent,
                "versao_termo": VERSAO_TERMO_PARCERIA,
                "atualizado_em": agora
            }
        )

        # Registrar historico de aceite
        db.execute(
            text("""
                INSERT INTO historico_aceites_parceiros (
                    parceiro_id, tipo_aceite, versao_termo,
                    ip_address, user_agent, aceito_em, ativo
                ) VALUES (
                    :parceiro_id, 'ativacao_conta', :versao_termo,
                    :ip, :user_agent, :aceito_em, true
                )
            """),
            {
                "parceiro_id": parceiro_id,
                "versao_termo": VERSAO_TERMO_PARCERIA,
                "ip": client_ip,
                "user_agent": user_agent,
                "aceito_em": agora
            }
        )

        db.commit()

        logger.info(f"[AtivacaoParceiro] Parceiro {parceiro_id} ({nome}) ativado com sucesso")

        return {
            "sucesso": True,
            "mensagem": "Conta de parceiro ativada com sucesso!",
            "parceiro": {
                "nome": nome,
                "email": email
            },
            "login_url": "/static/parceiro/login.html"
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[AtivacaoParceiro] Erro ao processar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar ativacao")
