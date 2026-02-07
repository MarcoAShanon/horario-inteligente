"""
Endpoints de onboarding: criar, aprovar e rejeitar clientes.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import asyncio

from app.database import get_db
from app.api.admin import get_current_admin
from app.services.telegram_service import alerta_novo_cliente
from app.services.email_service import get_email_service
from app.services.admin_clientes_service import (
    executar_onboarding_cliente, executar_aprovacao_cliente
)
from app.api.admin_clientes.schemas import (
    ClienteCreate, AprovacaoClienteRequest, RejeicaoClienteRequest
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/clientes")
async def criar_cliente(
    dados: ClienteCreate,
    request: Request,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Cria nova clínica completa com médico principal.

    Fluxo:
    1. Validar dados
    2. Gerar subdomain único
    3. Criar cliente
    4. Criar configurações padrão
    5. Criar médico principal (admin)
    6. Criar assinatura
    7. Retornar credenciais
    """
    try:
        result = executar_onboarding_cliente(db, dados, admin.get("id"))

        # Side-effects: Telegram
        try:
            asyncio.create_task(alerta_novo_cliente(
                nome_cliente=dados.nome_fantasia,
                plano=result["plano"][2],
                subdomain=result["subdomain"],
                valor_mensal=result["billing"]["valor_final"],
                periodo=result["assinatura_dados"].periodo_cobranca
            ))
        except Exception as e:
            logger.warning(f"[Telegram] Erro ao enviar notificação: {e}")

        # Side-effects: Email de ativação
        link_ativacao = f"https://horariointeligente.com.br/static/ativar-conta.html?token={result['token_ativacao']}"
        try:
            email_service = get_email_service()
            email_service.send_ativacao_conta(dados.email, dados.nome_fantasia, result["token_ativacao"])
            logger.info(f"[Onboarding] Email de ativação enviado para {dados.email}")
        except Exception as e:
            logger.warning(f"[Onboarding] Erro ao enviar email de ativação: {e}")

        # Montar resposta
        plano = result["plano"]
        billing = result["billing"]
        assinatura_dados = result["assinatura_dados"]

        response = {
            "success": True,
            "cliente": {
                "id": result["cliente_id"],
                "nome": dados.nome_fantasia,
                "subdomain": result["subdomain"],
                "plano": plano[1],
                "plano_nome": plano[2],
                "status": "pendente_aceite"
            },
            "ativacao": {
                "status": "pendente_aceite",
                "link_ativacao": link_ativacao,
                "expira_em": result["token_expira_em"].isoformat(),
                "email_enviado": True
            },
            "assinatura": {
                "valor_base_plano": float(plano[3]),
                "profissionais_contratados": 1 + (len(dados.medicos_adicionais) if dados.medicos_adicionais else 0),
                "profissionais_extras": billing["profissionais_extras"],
                "valor_extras_profissionais": billing["valor_extras_profissionais"],
                "linha_dedicada": assinatura_dados.linha_dedicada,
                "valor_linha_dedicada": billing["valor_linha_dedicada"],
                "periodo_cobranca": assinatura_dados.periodo_cobranca,
                "percentual_periodo": billing["percentual_periodo"],
                "valor_original": billing["valor_original"],
                "desconto_percentual": assinatura_dados.desconto_percentual,
                "desconto_valor_fixo": assinatura_dados.desconto_valor_fixo,
                "desconto_duracao_meses": assinatura_dados.desconto_duracao_meses,
                "desconto_motivo": assinatura_dados.desconto_motivo,
                "valor_final": billing["valor_final"],
                "data_fim_desconto": billing["data_fim_desconto"].isoformat() if billing["data_fim_desconto"] else None
            },
            "medico_principal": {
                "id": result["medico_id"],
                "nome": result["medico_principal_nome"],
                "email": result["medico_principal_email"]
            },
            "credenciais": {
                "url_acesso": f"https://{result['subdomain']}.horariointeligente.com.br",
                "email": result["medico_principal_email"],
                "senha_temporaria": result["senha_temporaria"]
            },
            "proximos_passos": [
                "Cliente receberá email para aceitar termos e ativar conta",
                "Após ativação, configurar número WhatsApp na WABA (Meta Business)",
                "Agendar chamada de onboarding para configuração inicial",
                "Gerar primeira cobrança no ASAAS"
            ]
        }

        if result["medicos_adicionais_response"]:
            response["medicos_adicionais"] = result["medicos_adicionais_response"]
        if result["secretaria_response"]:
            response["secretaria"] = result["secretaria_response"]
        if result["comissao_info"]:
            response["comissao"] = result["comissao_info"]

        return response

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Onboarding] Erro ao criar cliente: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar cliente: {str(e)}"
        )


@router.post("/clientes/{cliente_id}/aprovar")
async def aprovar_cliente(
    cliente_id: int,
    dados: AprovacaoClienteRequest,
    request: Request,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Aprova cliente com status 'pendente_aprovacao'.
    Configura billing, gera senhas, cria assinatura e envia email de ativacao.
    """
    try:
        result = executar_aprovacao_cliente(db, cliente_id, dados)

        # Side-effects: Email de ativação
        link_ativacao = f"https://horariointeligente.com.br/static/ativar-conta.html?token={result['token_ativacao']}"
        try:
            email_service = get_email_service()
            email_service.send_ativacao_conta(result["email_cliente"], result["nome_cliente"], result["token_ativacao"])
            logger.info(f"[Aprovacao] Email de ativacao enviado para {result['email_cliente']}")
        except Exception as e:
            logger.warning(f"[Aprovacao] Erro ao enviar email de ativacao: {e}")

        # Side-effects: Telegram
        try:
            asyncio.create_task(alerta_novo_cliente(
                nome_cliente=result["nome_cliente"],
                plano=result["plano"][2],
                subdomain=result["subdomain"],
                valor_mensal=result["billing"]["valor_final"],
                periodo=result["assinatura_dados"].periodo_cobranca
            ))
        except Exception as e:
            logger.warning(f"[Telegram] Erro ao enviar notificacao: {e}")

        # Montar resposta
        plano = result["plano"]
        medico_principal = result["medico_principal"]

        response = {
            "success": True,
            "cliente": {
                "id": cliente_id,
                "nome": result["nome_cliente"],
                "subdomain": result["subdomain"],
                "plano": plano[1],
                "plano_nome": plano[2],
                "status": "pendente_aceite"
            },
            "ativacao": {
                "status": "pendente_aceite",
                "link_ativacao": link_ativacao,
                "expira_em": result["token_expira_em"].isoformat(),
                "email_enviado": True
            },
            "assinatura": {
                "valor_base_plano": float(plano[3]),
                "valor_final": result["billing"]["valor_final"],
                "periodo_cobranca": result["assinatura_dados"].periodo_cobranca
            },
            "medico_principal": {
                "id": medico_principal[0],
                "nome": medico_principal[1],
                "email": medico_principal[2]
            },
            "credenciais": {
                "url_acesso": f"https://{result['subdomain']}.horariointeligente.com.br",
                "email": medico_principal[2],
                "senha_temporaria": result["senha_temporaria"]
            }
        }

        if result["medicos_adicionais_response"]:
            response["medicos_adicionais"] = result["medicos_adicionais_response"]
        if result["secretaria_response"]:
            response["secretaria"] = result["secretaria_response"]
        if result["comissao_info"]:
            response["comissao"] = result["comissao_info"]

        return response

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Aprovacao] Erro ao aprovar cliente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao aprovar cliente: {str(e)}")


@router.post("/clientes/{cliente_id}/rejeitar")
async def rejeitar_cliente(
    cliente_id: int,
    dados: RejeicaoClienteRequest,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Rejeita cliente com status 'pendente_aprovacao'.
    Opcionalmente notifica prospect por email.
    """
    try:
        cliente = db.execute(
            text("SELECT id, nome, email, status FROM clientes WHERE id = :id"),
            {"id": cliente_id}
        ).fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")

        if cliente[3] != 'pendente_aprovacao':
            raise HTTPException(
                status_code=400,
                detail=f"Cliente nao esta pendente de aprovacao (status atual: {cliente[3]})"
            )

        db.execute(
            text("""
                UPDATE clientes
                SET status = 'rejeitado', atualizado_em = :atualizado_em
                WHERE id = :id
            """),
            {"atualizado_em": datetime.now(), "id": cliente_id}
        )
        db.commit()

        logger.info(f"[Aprovacao] Cliente {cliente_id} rejeitado. Motivo: {dados.motivo}")

        # Notificar por email se solicitado
        if dados.notificar_email and cliente[2]:
            try:
                email_service = get_email_service()
                email_service.send_telegram_notification(
                    f"<b>Cliente Rejeitado</b>\n\n"
                    f"<b>Nome:</b> {cliente[1]}\n"
                    f"<b>Motivo:</b> {dados.motivo or 'Nao informado'}\n"
                )
            except Exception as e:
                logger.warning(f"[Aprovacao] Erro ao notificar rejeicao: {e}")

        return {
            "success": True,
            "message": f"Cliente {cliente[1]} rejeitado com sucesso",
            "status": "rejeitado"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Aprovacao] Erro ao rejeitar cliente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao rejeitar cliente: {str(e)}")
