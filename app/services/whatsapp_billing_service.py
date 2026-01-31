"""
Serviço de Billing WhatsApp - Logging de mensagens enviadas
Horário Inteligente SaaS

Registra todas as mensagens enviadas via WhatsApp Business API Oficial,
classificando por categoria (marketing, utility, service) e calculando custos
baseados nos preços da Meta (Brasil, julho 2025).

Usa contextvars para passar cliente_id de forma transparente em código async.
"""

import logging
import contextvars
from typing import Optional
from decimal import Decimal

from sqlalchemy import text
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# ==================== CONTEXT VARS ====================

_billing_cliente_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    '_billing_cliente_id', default=None
)


def set_billing_context(cliente_id: int):
    """Define o cliente_id no contexto async para billing."""
    _billing_cliente_id.set(cliente_id)


def get_billing_cliente_id() -> Optional[int]:
    """Lê o cliente_id do contexto async."""
    return _billing_cliente_id.get()


# ==================== PRICING (Meta Brasil, julho 2025) ====================

PRICING_USD = {
    "marketing": Decimal("0.0625"),
    "utility": Decimal("0.0068"),
    "authentication": Decimal("0.0068"),
    "service": Decimal("0.0000"),
}

# ==================== TEMPLATE -> CATEGORY MAPPING ====================

TEMPLATE_CATEGORY = {
    # UTILITY
    "lembrete_24h": "utility",
    "lembrete_2h": "utility",
    "consulta_confirmada": "utility",
    "consulta_cancelada_clinica": "utility",
    "consulta_reagendada_clinica": "utility",
    "necessidade_reagendamento": "utility",
    "retorno_agendado": "utility",
    "pagamento_pendente": "utility",
    "pagamento_vencido": "utility",
    "pagamento_confirmado": "utility",
    "conta_suspensa": "utility",
    # MARKETING
    "boas_vindas_clinica": "marketing",
    "pesquisa_satisfacao": "marketing",
    "paciente_inativo": "marketing",
}


def get_category(template_name: Optional[str], message_type: str) -> str:
    """Retorna a categoria de billing para a mensagem."""
    if template_name and template_name in TEMPLATE_CATEGORY:
        return TEMPLATE_CATEGORY[template_name]
    if message_type == "template":
        # Template desconhecido — assume utility como fallback seguro
        return "utility"
    # text, interactive, audio, image dentro da janela 24h = service (grátis)
    return "service"


def get_cost_usd(category: str) -> Decimal:
    """Retorna o custo em USD para a categoria."""
    return PRICING_USD.get(category, Decimal("0.0000"))


# ==================== LOGGING ====================

def log_whatsapp_message(
    template_name: Optional[str],
    message_type: str,
    phone_to: str,
    success: bool,
    message_id: Optional[str],
):
    """
    Registra mensagem enviada na tabela whatsapp_message_log.
    Fire-and-forget: erros são apenas logados, nunca propagados.
    Usa cliente_id do contextvars.
    """
    try:
        cliente_id = get_billing_cliente_id()
        category = get_category(template_name, message_type)
        cost_usd = get_cost_usd(category)

        db = SessionLocal()
        try:
            db.execute(text("""
                INSERT INTO whatsapp_message_log
                (cliente_id, template_name, message_type, category, phone_to, success, message_id, cost_usd)
                VALUES
                (:cliente_id, :template_name, :message_type, :category, :phone_to, :success, :message_id, :cost_usd)
            """), {
                "cliente_id": cliente_id,
                "template_name": template_name,
                "message_type": message_type,
                "category": category,
                "phone_to": phone_to,
                "success": success,
                "message_id": message_id,
                "cost_usd": float(cost_usd),
            })
            db.commit()
        finally:
            db.close()

    except Exception as e:
        logger.warning(f"[WhatsApp Billing] Erro ao registrar log: {e}")
