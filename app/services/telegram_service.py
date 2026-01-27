"""
Serviço de Notificações via Telegram - Horário Inteligente
Envia alertas para administradores do sistema
"""
import httpx
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Configurações do Bot
TELEGRAM_BOT_TOKEN = "8276546106:AAH3ssg8G7InAUCI_Ixlc8g_m4FF7mPsH-0"
TELEGRAM_ADMIN_CHAT_ID = "8134518132"

# URL base da API do Telegram
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def enviar_mensagem_telegram(
    mensagem: str,
    chat_id: str = TELEGRAM_ADMIN_CHAT_ID,
    parse_mode: str = "HTML"
) -> bool:
    """
    Envia uma mensagem via Telegram

    Args:
        mensagem: Texto da mensagem (suporta HTML)
        chat_id: ID do chat de destino
        parse_mode: Formato da mensagem (HTML ou Markdown)

    Returns:
        True se enviou com sucesso, False caso contrário
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": mensagem,
                    "parse_mode": parse_mode
                }
            )

            if response.status_code == 200:
                logger.info(f"[Telegram] Mensagem enviada com sucesso para {chat_id}")
                return True
            else:
                logger.error(f"[Telegram] Erro ao enviar: {response.text}")
                return False

    except Exception as e:
        logger.error(f"[Telegram] Erro ao enviar mensagem: {e}")
        return False


def enviar_mensagem_telegram_sync(
    mensagem: str,
    chat_id: str = TELEGRAM_ADMIN_CHAT_ID,
    parse_mode: str = "HTML"
) -> bool:
    """
    Versão síncrona para uso em scripts
    """
    import requests

    try:
        response = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": mensagem,
                "parse_mode": parse_mode
            },
            timeout=30
        )

        if response.status_code == 200:
            return True
        else:
            logger.error(f"[Telegram] Erro ao enviar: {response.text}")
            return False

    except Exception as e:
        logger.error(f"[Telegram] Erro ao enviar mensagem: {e}")
        return False


# ==================== ALERTAS ESPECÍFICOS ====================

async def alerta_certificado_ssl(dias_restantes: int, data_expiracao: str):
    """Alerta sobre expiração do certificado SSL"""

    if dias_restantes <= 0:
        emoji = "🚨"
        nivel = "EXPIRADO"
    elif dias_restantes <= 7:
        emoji = "⚠️"
        nivel = "CRÍTICO"
    elif dias_restantes <= 14:
        emoji = "⚡"
        nivel = "URGENTE"
    else:
        emoji = "📢"
        nivel = "AVISO"

    mensagem = f"""
{emoji} <b>ALERTA SSL - {nivel}</b>

O certificado SSL wildcard do Horário Inteligente {"<b>EXPIROU!</b>" if dias_restantes <= 0 else f"expira em <b>{dias_restantes} dias</b>."}

📅 Data de expiração: {data_expiracao}
🌐 Domínio: *.horariointeligente.com.br

<b>Ação necessária:</b>
<code>sudo /root/sistema_agendamento/scripts/renovar-certificado-wildcard.sh</code>

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

    return await enviar_mensagem_telegram(mensagem.strip())


async def alerta_novo_cliente(
    nome_cliente: str,
    plano: str,
    subdomain: str,
    valor_mensal: Optional[float] = None,
    periodo: Optional[str] = None
):
    """Notifica quando um novo cliente é cadastrado"""

    # Formatar período
    periodos_label = {
        "mensal": "Mensal",
        "trimestral": "Trimestral",
        "semestral": "Semestral",
        "anual": "Anual"
    }
    periodo_texto = periodos_label.get(periodo, "Mensal") if periodo else "Mensal"

    # Formatar valor
    valor_texto = f"R$ {valor_mensal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor_mensal else "A definir"

    mensagem = f"""
🎉 <b>NOVO CLIENTE CADASTRADO</b>

🏥 <b>{nome_cliente}</b>
📋 Plano: {plano}
💰 Valor: {valor_texto}/mês
📆 Período: {periodo_texto}
🌐 URL: https://{subdomain}.horariointeligente.com.br

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

    return await enviar_mensagem_telegram(mensagem.strip())


async def alerta_cliente_inativo(nome_cliente: str, motivo: str = ""):
    """Notifica quando um cliente é desativado"""

    mensagem = f"""
⚠️ <b>CLIENTE DESATIVADO</b>

🏥 <b>{nome_cliente}</b>
{f"📝 Motivo: {motivo}" if motivo else ""}

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

    return await enviar_mensagem_telegram(mensagem.strip())


async def alerta_erro_sistema(erro: str, contexto: str = ""):
    """Notifica sobre erros críticos do sistema"""

    mensagem = f"""
🔴 <b>ERRO NO SISTEMA</b>

{f"📍 Contexto: {contexto}" if contexto else ""}
❌ Erro: <code>{erro[:500]}</code>

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

    return await enviar_mensagem_telegram(mensagem.strip())


async def alerta_backup(status: str, detalhes: str = ""):
    """Notifica sobre status de backups"""

    emoji = "✅" if status == "sucesso" else "❌"

    mensagem = f"""
{emoji} <b>BACKUP {status.upper()}</b>

{f"📝 {detalhes}" if detalhes else ""}

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

    return await enviar_mensagem_telegram(mensagem.strip())


async def relatorio_diario(stats: dict):
    """Envia relatório diário de estatísticas"""

    mensagem = f"""
📊 <b>RELATÓRIO DIÁRIO - HORÁRIO INTELIGENTE</b>

👥 Clientes ativos: {stats.get('clientes_ativos', 0)}
👨‍⚕️ Profissionais: {stats.get('total_medicos', 0)}
📅 Agendamentos hoje: {stats.get('agendamentos_hoje', 0)}
📈 Agendamentos mês: {stats.get('agendamentos_mes', 0)}

💰 MRR: R$ {stats.get('mrr', 0):,.2f}

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

    return await enviar_mensagem_telegram(mensagem.strip())


# ==================== TESTE ====================

async def enviar_teste():
    """Envia mensagem de teste"""

    mensagem = """
✅ <b>BOT CONFIGURADO COM SUCESSO!</b>

O sistema de alertas do Horário Inteligente está funcionando.

Você receberá notificações sobre:
• 🔐 Certificado SSL (expiração)
• 🎉 Novos clientes cadastrados
• ⚠️ Clientes desativados
• 🔴 Erros críticos do sistema
• 📊 Relatórios diários (opcional)

🤖 Bot: Horário Inteligente Alertas
"""

    return await enviar_mensagem_telegram(mensagem.strip())
