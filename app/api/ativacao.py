"""
API de Ativação de Conta - Aceite de Termos
Endpoints públicos (sem autenticação) para ativação de contas de clientes
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
import logging
import secrets

from app.database import get_db
from app.services.email_service import get_email_service
from app.services.billing_service import billing_service

router = APIRouter(prefix="/api/ativacao", tags=["Ativação de Conta"])
logger = logging.getLogger(__name__)

# Versões atuais dos termos
VERSAO_TERMOS = "1.0"
VERSAO_PRIVACIDADE = "1.1"


# ==================== SCHEMAS ====================

class AceiteRequest(BaseModel):
    aceite_termos: bool
    aceite_privacidade: bool


class ReenviarRequest(BaseModel):
    email: str


# ==================== ENDPOINTS ====================
# IMPORTANTE: rotas fixas (/reenviar) devem vir ANTES das rotas com path param (/{token})

@router.post("/reenviar")
async def reenviar_ativacao(
    dados: ReenviarRequest,
    db: Session = Depends(get_db)
):
    """
    Reenvia email de ativação gerando novo token.
    Apenas para clientes com status pendente_aceite.
    """
    try:
        # Buscar cliente pelo email
        result = db.execute(
            text("""
                SELECT id, nome, email, status
                FROM clientes
                WHERE email = :email
            """),
            {"email": dados.email}
        ).fetchone()

        if not result:
            # Retornar sucesso mesmo se não encontrar (segurança)
            return {"sucesso": True, "mensagem": "Se o email estiver cadastrado, um novo link será enviado."}

        cliente_id, nome, email, status = result

        if status != 'pendente_aceite':
            return {"sucesso": True, "mensagem": "Se o email estiver cadastrado, um novo link será enviado."}

        # Gerar novo token
        novo_token = secrets.token_urlsafe(64)
        expira_em = datetime.now() + timedelta(days=7)

        db.execute(
            text("""
                UPDATE clientes SET
                    token_ativacao = :token,
                    token_expira_em = :expira_em,
                    atualizado_em = :atualizado_em
                WHERE id = :id
            """),
            {
                "id": cliente_id,
                "token": novo_token,
                "expira_em": expira_em,
                "atualizado_em": datetime.now()
            }
        )
        db.commit()

        # Enviar email
        email_service = get_email_service()
        email_service.send_ativacao_conta(email, nome, novo_token)

        logger.info(f"[Ativação] Email de ativação reenviado para {email}")

        return {
            "sucesso": True,
            "mensagem": "Se o email estiver cadastrado, um novo link será enviado."
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[Ativação] Erro ao reenviar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao processar reenvio")


@router.get("/{token}")
async def obter_dados_ativacao(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Retorna dados do cliente para exibição na página de ativação.
    Endpoint público (sem autenticação).
    """
    try:
        result = db.execute(
            text("""
                SELECT c.id, c.nome, c.email, c.cnpj, c.plano, c.valor_mensalidade,
                       c.status, c.token_expira_em, c.subdomain,
                       a.dia_vencimento, a.periodo_cobranca,
                       a.valor_mensal, a.valor_original, a.percentual_periodo,
                       a.profissionais_contratados, a.linha_dedicada,
                       a.taxa_ativacao, a.ativacao_cortesia,
                       a.desconto_ativacao_percentual,
                       p.nome as plano_nome, p.valor_mensal as plano_valor_base,
                       p.profissionais_inclusos, p.taxa_ativacao as plano_taxa_ativacao
                FROM clientes c
                LEFT JOIN assinaturas a ON a.cliente_id = c.id
                LEFT JOIN planos p ON p.id = a.plano_id
                WHERE c.token_ativacao = :token
                ORDER BY a.criado_em DESC
                LIMIT 1
            """),
            {"token": token}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Token de ativação inválido")

        (cliente_id, nome, email, cnpj, plano, valor, status, token_expira, subdomain,
         dia_vencimento, periodo_cobranca,
         a_valor_mensal, a_valor_original, a_percentual_periodo,
         a_profissionais, a_linha_dedicada,
         a_taxa_ativacao, a_ativacao_cortesia,
         a_desconto_ativacao_pct,
         plano_nome, plano_valor_base, plano_profissionais_inclusos,
         plano_taxa_ativacao) = result

        # Verificar se já ativou
        if status != 'pendente_aceite':
            raise HTTPException(status_code=409, detail="Esta conta já foi ativada")

        # Verificar se token expirou
        if token_expira and datetime.now(token_expira.tzinfo) > token_expira:
            raise HTTPException(status_code=410, detail="Link de ativação expirado. Solicite um novo.")

        # Calcular valor por ciclo de cobranca
        multiplicador_periodo = {"mensal": 1, "trimestral": 3, "semestral": 6, "anual": 12}
        periodo = periodo_cobranca or "mensal"
        valor_mensal_float = float(a_valor_mensal or valor or 0)
        valor_cobranca_periodo = valor_mensal_float * multiplicador_periodo.get(periodo, 1)

        # Taxa de ativacao final
        taxa_ativ = float(a_taxa_ativacao or plano_taxa_ativacao or 150)
        desconto_ativ_pct = float(a_desconto_ativacao_pct or 0)
        taxa_ativacao_final = taxa_ativ * (1 - desconto_ativ_pct / 100)

        return {
            "nome": nome,
            "email": email,
            "cnpj": cnpj,
            "plano": plano,
            "plano_nome": plano_nome or plano,
            "plano_valor_base": float(plano_valor_base) if plano_valor_base else None,
            "profissionais_contratados": a_profissionais or 1,
            "profissionais_inclusos": plano_profissionais_inclusos or 1,
            "periodo_cobranca": periodo,
            "percentual_periodo": float(a_percentual_periodo or 0),
            "linha_dedicada": bool(a_linha_dedicada),
            "valor_linha_dedicada": 40.00 if a_linha_dedicada else 0,
            "valor_original": float(a_valor_original) if a_valor_original else None,
            "valor_mensal": valor_mensal_float,
            "valor_mensalidade": valor,
            "valor_cobranca_periodo": valor_cobranca_periodo,
            "taxa_ativacao": taxa_ativ,
            "taxa_ativacao_final": taxa_ativacao_final,
            "ativacao_cortesia": bool(a_ativacao_cortesia),
            "desconto_ativacao_percentual": desconto_ativ_pct,
            "subdomain": subdomain,
            "dia_vencimento": dia_vencimento,
            "versao_termos": VERSAO_TERMOS,
            "versao_privacidade": VERSAO_PRIVACIDADE
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Ativação] Erro ao obter dados: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar ativação")


@router.post("/{token}")
async def processar_ativacao(
    token: str,
    dados: AceiteRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Processa aceite de termos e ativa a conta.
    Endpoint público (sem autenticação).
    """
    try:
        # Validar aceites
        if not dados.aceite_termos or not dados.aceite_privacidade:
            raise HTTPException(
                status_code=400,
                detail="É necessário aceitar os termos de uso e a política de privacidade"
            )

        # Buscar cliente pelo token
        result = db.execute(
            text("""
                SELECT c.id, c.nome, c.email, c.status, c.token_expira_em,
                       c.subdomain, c.cadastrado_por_id, c.cadastrado_por_tipo
                FROM clientes c
                WHERE c.token_ativacao = :token
            """),
            {"token": token}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Token de ativação inválido")

        cliente_id, nome, email, status, token_expira, subdomain, cadastrado_por_id, cadastrado_por_tipo = result

        # Verificar se já ativou
        if status != 'pendente_aceite':
            raise HTTPException(status_code=409, detail="Esta conta já foi ativada")

        # Verificar se token expirou
        if token_expira and datetime.now(token_expira.tzinfo) > token_expira:
            raise HTTPException(status_code=410, detail="Link de ativação expirado. Solicite um novo.")

        # Obter dados do request
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        agora = datetime.now()

        # Atualizar cliente
        db.execute(
            text("""
                UPDATE clientes SET
                    status = 'ativo',
                    ativo = true,
                    token_ativacao = NULL,
                    token_expira_em = NULL,
                    aceite_termos_em = :aceite_em,
                    aceite_ip = :ip,
                    aceite_user_agent = :user_agent,
                    aceite_versao_termos = :versao_termos,
                    aceite_versao_privacidade = :versao_privacidade,
                    atualizado_em = :atualizado_em
                WHERE id = :id
            """),
            {
                "id": cliente_id,
                "aceite_em": agora,
                "ip": client_ip,
                "user_agent": user_agent,
                "versao_termos": VERSAO_TERMOS,
                "versao_privacidade": VERSAO_PRIVACIDADE,
                "atualizado_em": agora
            }
        )

        # Inserir registro em historico_aceites
        db.execute(
            text("""
                INSERT INTO historico_aceites (
                    cliente_id, tipo_aceite, versao_termos, versao_privacidade,
                    ip_address, user_agent, aceito_em, ativo
                ) VALUES (
                    :cliente_id, 'ativacao', :versao_termos, :versao_privacidade,
                    :ip, :user_agent, :aceito_em, true
                )
            """),
            {
                "cliente_id": cliente_id,
                "versao_termos": VERSAO_TERMOS,
                "versao_privacidade": VERSAO_PRIVACIDADE,
                "ip": client_ip,
                "user_agent": user_agent,
                "aceito_em": agora
            }
        )

        db.commit()

        logger.info(f"[Ativação] Cliente {cliente_id} ({nome}) ativado com sucesso")

        # Iniciar billing automático no ASAAS (não-bloqueante, não afeta resposta)
        billing_result = None
        try:
            billing_result = await billing_service.process_onboarding_billing(db, cliente_id)
            if billing_result.get("success"):
                logger.info(f"[Ativação] Billing automático iniciado para cliente {cliente_id}")
            else:
                logger.warning(f"[Ativação] Billing parcial para cliente {cliente_id}: {billing_result.get('errors')}")
        except Exception as e:
            logger.error(f"[Ativação] Erro no billing automático para cliente {cliente_id}: {e}")

        # Enviar emails (não-bloqueante, não afeta resposta)
        try:
            email_service = get_email_service()

            # Email de boas-vindas
            email_service.send_boas_vindas_ativacao(email, nome, subdomain)

            # Notificar parceiro se aplicável
            if cadastrado_por_tipo == 'parceiro' and cadastrado_por_id:
                parceiro = db.execute(
                    text("SELECT email, nome FROM parceiros_comerciais WHERE id = :id"),
                    {"id": cadastrado_por_id}
                ).fetchone()

                if parceiro and parceiro[0]:
                    email_service.send_notificacao_parceiro_ativacao(
                        parceiro[0], parceiro[1], nome
                    )
        except Exception as e:
            logger.warning(f"[Ativação] Erro ao enviar emails pós-ativação: {e}")

        response_data = {
            "sucesso": True,
            "mensagem": "Conta ativada com sucesso!",
            "nome": nome,
            "subdomain": subdomain,
            "url_acesso": f"https://{subdomain}.horariointeligente.com.br"
        }

        # Incluir info de billing se disponível
        if billing_result:
            response_data["billing"] = {
                "asaas_customer_id": billing_result.get("asaas_customer_id"),
                "asaas_subscription_id": billing_result.get("asaas_subscription_id"),
                "activation_fee": billing_result.get("activation_fee"),
                "billing_success": billing_result.get("success", False)
            }

        return response_data

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Ativação] Erro ao processar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar ativação")
