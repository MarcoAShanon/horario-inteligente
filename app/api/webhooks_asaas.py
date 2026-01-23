"""
Webhook Handler para ASAAS Payment Gateway
Processa eventos de pagamento do ASAAS

Eventos tratados:
- PAYMENT_CONFIRMED: Pagamento confirmado
- PAYMENT_RECEIVED: Pagamento recebido
- PAYMENT_OVERDUE: Pagamento vencido
- PAYMENT_DELETED: Pagamento cancelado
- PAYMENT_REFUNDED: Pagamento estornado

RÉGUA DE INADIMPLÊNCIA:
- PAYMENT_OVERDUE → marca cliente como inadimplente (ativo=False)
- PAYMENT_CONFIRMED/RECEIVED → reativa cliente (ativo=True)
"""
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import logging
import os
from typing import Optional
from datetime import datetime
from sqlalchemy import text

from app.database import SessionLocal
from app.services.asaas_service import AsaasService

logger = logging.getLogger(__name__)

router = APIRouter()

# Token de validação do webhook
ASAAS_WEBHOOK_TOKEN = os.getenv("ASAAS_WEBHOOK_TOKEN", "")


def get_db():
    """Obtém sessão do banco de dados"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


@router.post("/api/webhooks/asaas")
async def webhook_asaas(
    request: Request,
    asaas_access_token: Optional[str] = Header(None, alias="asaas-access-token")
):
    """
    Recebe notificações do ASAAS sobre eventos de pagamento.

    O ASAAS envia um POST com os dados do evento.
    Documentação: https://docs.asaas.com/reference/webhook
    """
    db = get_db()

    try:
        # 1. Validar token de webhook (se configurado)
        if ASAAS_WEBHOOK_TOKEN:
            asaas_service = AsaasService()
            if asaas_access_token and not asaas_service.validar_webhook_token(asaas_access_token):
                logger.warning(f"Webhook ASAAS com token inválido: {asaas_access_token}")
                raise HTTPException(status_code=401, detail="Token inválido")

        # 2. Extrair dados do evento
        data = await request.json()

        event = data.get("event")
        payment_data = data.get("payment", {})

        logger.info(f"Webhook ASAAS recebido: {event} - Payment ID: {payment_data.get('id')}")

        # 3. Processar evento
        if event in ["PAYMENT_CONFIRMED", "PAYMENT_RECEIVED", "PAYMENT_RECEIVED_IN_CASH"]:
            await processar_pagamento_confirmado(db, payment_data)

        elif event == "PAYMENT_OVERDUE":
            await processar_pagamento_vencido(db, payment_data)

        elif event in ["PAYMENT_DELETED", "PAYMENT_REFUNDED", "PAYMENT_REFUND_IN_PROGRESS"]:
            await processar_pagamento_cancelado(db, payment_data, event)

        elif event == "PAYMENT_CREATED":
            await processar_pagamento_criado(db, payment_data)

        elif event == "PAYMENT_UPDATED":
            await processar_pagamento_atualizado(db, payment_data)

        else:
            logger.info(f"Evento ASAAS não tratado: {event}")

        db.commit()

        return JSONResponse(
            content={"status": "success", "event": event},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar webhook ASAAS: {e}")
        db.rollback()
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )
    finally:
        db.close()


async def processar_pagamento_confirmado(db, payment_data: dict):
    """
    Processa pagamento confirmado/recebido.
    Atualiza status do pagamento e, se for taxa de ativação, marca como paga.
    
    RÉGUA: Reativa o cliente (ativo=True) e assinatura (status='ativa')
    """
    asaas_payment_id = payment_data.get("id")
    valor_pago = payment_data.get("value")
    data_pagamento = payment_data.get("paymentDate") or payment_data.get("confirmedDate")

    logger.info(f"Processando pagamento confirmado: {asaas_payment_id}")

    # Atualizar pagamento no banco
    result = db.execute(
        text("""
            UPDATE pagamentos
            SET status = :status,
                valor_pago = :valor_pago,
                data_pagamento = :data_pagamento,
                atualizado_em = NOW()
            WHERE asaas_payment_id = :asaas_id
            RETURNING id, tipo, assinatura_id, cliente_id
        """),
        {
            "status": "CONFIRMED",
            "valor_pago": valor_pago,
            "data_pagamento": data_pagamento,
            "asaas_id": asaas_payment_id
        }
    ).fetchone()

    if result:
        pagamento_id, tipo, assinatura_id, cliente_id = result

        # Se for taxa de ativação, marcar como paga na assinatura
        if tipo == "ATIVACAO" and assinatura_id:
            db.execute(
                text("UPDATE assinaturas SET taxa_ativacao_paga = true WHERE id = :id"),
                {"id": assinatura_id}
            )
            logger.info(f"Taxa de ativação marcada como paga - Assinatura {assinatura_id}")

        # ============ RÉGUA DE INADIMPLÊNCIA ============
        # Reativar cliente
        db.execute(
            text("UPDATE clientes SET ativo = true WHERE id = :id"),
            {"id": cliente_id}
        )
        logger.info(f"[RÉGUA] Cliente {cliente_id} REATIVADO - pagamento confirmado")

        # Reativar assinatura se estava suspensa por inadimplência
        if assinatura_id:
            db.execute(
                text("""
                    UPDATE assinaturas 
                    SET status = 'ativa', 
                        atualizado_em = NOW()
                    WHERE id = :id AND status = 'suspensa'
                """),
                {"id": assinatura_id}
            )
            logger.info(f"[RÉGUA] Assinatura {assinatura_id} reativada")
        # ================================================

        logger.info(f"Pagamento {pagamento_id} confirmado com sucesso")
    else:
        # Pagamento não encontrado no banco - pode ser de outra origem
        logger.warning(f"Pagamento ASAAS não encontrado no banco: {asaas_payment_id}")


async def processar_pagamento_vencido(db, payment_data: dict):
    """
    Processa pagamento vencido.
    Atualiza status do pagamento para OVERDUE.
    
    RÉGUA DE INADIMPLÊNCIA:
    - Marca cliente como INATIVO (ativo=False)
    - Marca assinatura como SUSPENSA
    - Registra data da suspensão
    """
    asaas_payment_id = payment_data.get("id")
    customer_id = payment_data.get("customer")

    logger.info(f"Processando pagamento vencido: {asaas_payment_id}")

    # Atualizar status do pagamento
    result = db.execute(
        text("""
            UPDATE pagamentos
            SET status = 'OVERDUE',
                atualizado_em = NOW()
            WHERE asaas_payment_id = :asaas_id
            RETURNING cliente_id, assinatura_id
        """),
        {"asaas_id": asaas_payment_id}
    ).fetchone()

    cliente_id = None
    assinatura_id = None

    if result:
        cliente_id, assinatura_id = result
    else:
        # Buscar cliente pelo asaas_customer_id
        cliente = db.execute(
            text("SELECT id FROM clientes WHERE asaas_customer_id = :id"),
            {"id": customer_id}
        ).fetchone()
        if cliente:
            cliente_id = cliente[0]

    # ============ RÉGUA DE INADIMPLÊNCIA ============
    if cliente_id:
        # Suspender cliente
        db.execute(
            text("UPDATE clientes SET ativo = false WHERE id = :id"),
            {"id": cliente_id}
        )
        logger.warning(f"[RÉGUA] Cliente {cliente_id} SUSPENSO por inadimplência - Pagamento vencido")

        # Suspender assinatura
        if assinatura_id:
            db.execute(
                text("""
                    UPDATE assinaturas 
                    SET status = 'suspensa',
                        atualizado_em = NOW()
                    WHERE id = :id
                """),
                {"id": assinatura_id}
            )
            logger.warning(f"[RÉGUA] Assinatura {assinatura_id} SUSPENSA por inadimplência")
        else:
            # Suspender todas as assinaturas ativas do cliente
            db.execute(
                text("""
                    UPDATE assinaturas 
                    SET status = 'suspensa',
                        atualizado_em = NOW()
                    WHERE cliente_id = :cliente_id AND status = 'ativa'
                """),
                {"cliente_id": cliente_id}
            )
            logger.warning(f"[RÉGUA] Todas assinaturas do cliente {cliente_id} SUSPENSAS")

        # Registrar evento de inadimplência (para histórico)
        try:
            db.execute(
                text("""
                    INSERT INTO historico_inadimplencia (
                        cliente_id, asaas_payment_id, evento, data_evento
                    ) VALUES (
                        :cliente_id, :asaas_payment_id, 'SUSPENSAO', NOW()
                    )
                """),
                {"cliente_id": cliente_id, "asaas_payment_id": asaas_payment_id}
            )
        except Exception as e:
            # Tabela pode não existir ainda - apenas log
            logger.debug(f"Tabela historico_inadimplencia não existe: {e}")
    # ================================================

    logger.info(f"Pagamento {asaas_payment_id} marcado como vencido")


async def processar_pagamento_cancelado(db, payment_data: dict, event: str):
    """
    Processa pagamento cancelado/estornado.
    Atualiza status do pagamento.
    
    RÉGUA: Se for estorno, pode suspender o cliente
    """
    asaas_payment_id = payment_data.get("id")
    customer_id = payment_data.get("customer")

    status = "REFUNDED" if "REFUND" in event else "DELETED"

    logger.info(f"Processando pagamento cancelado/estornado: {asaas_payment_id} - Status: {status}")

    result = db.execute(
        text("""
            UPDATE pagamentos
            SET status = :status,
                atualizado_em = NOW()
            WHERE asaas_payment_id = :asaas_id
            RETURNING cliente_id
        """),
        {"status": status, "asaas_id": asaas_payment_id}
    ).fetchone()

    # ============ RÉGUA DE INADIMPLÊNCIA ============
    # Se for estorno (REFUNDED), suspender cliente
    if status == "REFUNDED":
        cliente_id = None
        if result:
            cliente_id = result[0]
        else:
            cliente = db.execute(
                text("SELECT id FROM clientes WHERE asaas_customer_id = :id"),
                {"id": customer_id}
            ).fetchone()
            if cliente:
                cliente_id = cliente[0]

        if cliente_id:
            db.execute(
                text("UPDATE clientes SET ativo = false WHERE id = :id"),
                {"id": cliente_id}
            )
            logger.warning(f"[RÉGUA] Cliente {cliente_id} SUSPENSO - pagamento estornado")
    # ================================================

    logger.info(f"Pagamento {asaas_payment_id} marcado como {status}")


async def processar_pagamento_criado(db, payment_data: dict):
    """
    Processa evento de pagamento criado (para pagamentos criados diretamente no ASAAS).
    Útil para sincronização.
    """
    asaas_payment_id = payment_data.get("id")
    customer_id = payment_data.get("customer")

    logger.info(f"Pagamento criado no ASAAS: {asaas_payment_id} - Customer: {customer_id}")

    # Verificar se já existe no banco
    result = db.execute(
        text("SELECT id FROM pagamentos WHERE asaas_payment_id = :id"),
        {"id": asaas_payment_id}
    ).fetchone()

    if result:
        logger.info(f"Pagamento {asaas_payment_id} já existe no banco local")
        return

    # Buscar cliente pelo asaas_customer_id
    cliente = db.execute(
        text("SELECT id FROM clientes WHERE asaas_customer_id = :id"),
        {"id": customer_id}
    ).fetchone()

    if not cliente:
        logger.warning(f"Cliente ASAAS não encontrado no banco: {customer_id}")
        return

    # Inserir pagamento no banco
    db.execute(
        text("""
            INSERT INTO pagamentos (
                cliente_id, asaas_payment_id, asaas_invoice_url,
                valor, data_vencimento, forma_pagamento, status,
                descricao, tipo
            ) VALUES (
                :cliente_id, :asaas_payment_id, :invoice_url,
                :valor, :data_vencimento, :forma_pagamento, :status,
                :descricao, 'AVULSO'
            )
        """),
        {
            "cliente_id": cliente[0],
            "asaas_payment_id": asaas_payment_id,
            "invoice_url": payment_data.get("invoiceUrl"),
            "valor": payment_data.get("value"),
            "data_vencimento": payment_data.get("dueDate"),
            "forma_pagamento": payment_data.get("billingType"),
            "status": payment_data.get("status", "PENDING"),
            "descricao": payment_data.get("description", "Cobrança ASAAS")
        }
    )

    logger.info(f"Pagamento {asaas_payment_id} sincronizado do ASAAS")


async def processar_pagamento_atualizado(db, payment_data: dict):
    """
    Processa evento de pagamento atualizado.
    Sincroniza dados do pagamento.
    """
    asaas_payment_id = payment_data.get("id")

    logger.info(f"Pagamento atualizado no ASAAS: {asaas_payment_id}")

    # Mapear status
    asaas_service = AsaasService()
    status = asaas_service.mapear_status_pagamento(payment_data.get("status", "PENDING"))

    db.execute(
        text("""
            UPDATE pagamentos
            SET status = :status,
                valor = :valor,
                data_vencimento = :data_vencimento,
                forma_pagamento = :forma_pagamento,
                atualizado_em = NOW()
            WHERE asaas_payment_id = :asaas_id
        """),
        {
            "status": status,
            "valor": payment_data.get("value"),
            "data_vencimento": payment_data.get("dueDate"),
            "forma_pagamento": payment_data.get("billingType"),
            "asaas_id": asaas_payment_id
        }
    )

    logger.info(f"Pagamento {asaas_payment_id} atualizado no banco local")


# ============ ENDPOINT DE STATUS ============

@router.get("/api/webhooks/asaas/status")
async def webhook_asaas_status():
    """
    Verifica status do webhook ASAAS.
    Útil para validar configuração.
    """
    return {
        "status": "online",
        "webhook_url": "/api/webhooks/asaas",
        "token_configured": bool(ASAAS_WEBHOOK_TOKEN),
        "environment": os.getenv("ASAAS_ENVIRONMENT", "sandbox"),
        "regua_inadimplencia": "ativa",
        "timestamp": datetime.now().isoformat()
    }
