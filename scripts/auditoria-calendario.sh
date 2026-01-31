#!/bin/bash
# =============================================================================
# Calendario de Auditorias - Horario Inteligente
# =============================================================================
# Envia lembretes no 1o sabado do mes sobre auditorias manuais pendentes.
# Cron: sabados 09:00 BRT (12:00 UTC)
# - Mensal: checklist basico (todo 1o sabado)
# - Trimestral: auditoria completa secoes 1-10 (Jan/Abr/Jul/Out)
# - Semestral: rotacao de chaves (Jan/Jul)
# =============================================================================

set -euo pipefail

ENV_FILE="/root/sistema_agendamento/.env"
LOG_FILE="/var/log/auditoria-semanal.log"

# --- Carregar credenciais Telegram ---
if [ ! -f "$ENV_FILE" ]; then
    exit 1
fi

TELEGRAM_BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d'=' -f2-)
TELEGRAM_CHAT_ID=$(grep '^TELEGRAM_CHAT_ID=' "$ENV_FILE" | cut -d'=' -f2-)

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    exit 1
fi

# --- Detectar se hoje e o 1o sabado do mes ---
TODAY=$(date '+%Y-%m-%d')
YEAR=$(date '+%Y')
MONTH=$(date '+%m')

FIRST_SATURDAY=""
for DAY in 1 2 3 4 5 6 7; do
    CHECK_DATE=$(printf '%s-%s-%02d' "$YEAR" "$MONTH" "$DAY")
    DOW=$(date -d "$CHECK_DATE" '+%u' 2>/dev/null || echo "0")
    if [ "$DOW" = "6" ]; then
        FIRST_SATURDAY="$CHECK_DATE"
        break
    fi
done

# Se hoje nao e o 1o sabado, sair silenciosamente
if [ "$TODAY" != "$FIRST_SATURDAY" ]; then
    exit 0
fi

# --- Hoje e o 1o sabado do mes - montar mensagem ---
DATA_BRT=$(TZ="America/Sao_Paulo" date '+%d/%m/%Y')
MES_NUM=$(date '+%-m')

MSG="📋 LEMBRETE DE AUDITORIA - ${DATA_BRT}\n\n"

# --- Auditoria Mensal (todo 1o sabado) ---
MSG="${MSG}📌 AUDITORIA MENSAL\n"
MSG="${MSG}Checklist basico a executar manualmente:\n"
MSG="${MSG}• Revisar logs do sistema (tamanho, erros)\n"
MSG="${MSG}• Verificar backups do banco de dados\n"
MSG="${MSG}• Revisar acessos de usuarios (contas inativas)\n"
MSG="${MSG}• Verificar uso de disco e memoria\n"
MSG="${MSG}• Revisar alertas da semana\n"

# --- Auditoria Trimestral (Jan/Abr/Jul/Out) ---
IS_TRIMESTRAL=false
case $MES_NUM in
    1|4|7|10)
        IS_TRIMESTRAL=true
        ;;
esac

if [ "$IS_TRIMESTRAL" = true ]; then
    MSG="${MSG}\n🔍 AUDITORIA TRIMESTRAL (completa)\n"
    MSG="${MSG}Executar auditoria completa das secoes 1-10:\n"
    MSG="${MSG}• Secao 1: Gestao de Segredos\n"
    MSG="${MSG}• Secao 2: Autenticacao & JWT\n"
    MSG="${MSG}• Secao 3: SQL Injection\n"
    MSG="${MSG}• Secao 4: Isolamento Multi-Tenant\n"
    MSG="${MSG}• Secao 5: Protecao de Dados / LGPD\n"
    MSG="${MSG}• Secao 6: Infraestrutura\n"
    MSG="${MSG}• Secao 7: Seguranca HTTP\n"
    MSG="${MSG}• Secao 8: Rate Limiting\n"
    MSG="${MSG}• Secao 9: WebSocket\n"
    MSG="${MSG}• Secao 10: Dependencias\n"
    MSG="${MSG}📄 Documento: auditoria_seguranca.md\n"
fi

# --- Auditoria Semestral (Jan/Jul) ---
IS_SEMESTRAL=false
case $MES_NUM in
    1|7)
        IS_SEMESTRAL=true
        ;;
esac

if [ "$IS_SEMESTRAL" = true ]; then
    MSG="${MSG}\n🔑 AUDITORIA SEMESTRAL - Rotacao de Chaves\n"
    MSG="${MSG}Chaves a rotacionar:\n"
    MSG="${MSG}• SECRET_KEY (JWT)\n"
    MSG="${MSG}• ENCRYPTION_KEY (LGPD/CPF)\n"
    MSG="${MSG}• WHATSAPP_ACCESS_TOKEN\n"
    MSG="${MSG}• WHATSAPP_WEBHOOK_VERIFY_TOKEN\n"
    MSG="${MSG}• ANTHROPIC_API_KEY\n"
    MSG="${MSG}• OPENAI_API_KEY\n"
    MSG="${MSG}• SMTP_PASSWORD\n"
    MSG="${MSG}• ASAAS_API_KEY\n"
    MSG="${MSG}• ASAAS_WEBHOOK_TOKEN\n"
    MSG="${MSG}• VAPID keys\n"
    MSG="${MSG}⚠️ Atualizar .env e reiniciar servico apos rotacao\n"
fi

# --- Enviar mensagem consolidada via Telegram ---
FULL_MSG=$(echo -e "$MSG")
VENV_PYTHON="/root/sistema_agendamento/venv/bin/python3"

$VENV_PYTHON << PYEOF
import json, urllib.request

text = """${FULL_MSG}"""
payload = json.dumps({
    "chat_id": "${TELEGRAM_CHAT_ID}",
    "text": text,
    "parse_mode": ""
})
req = urllib.request.Request(
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage",
    data=payload.encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req, timeout=30)
    print("Telegram: lembrete enviado")
except Exception as e:
    print(f"Telegram: erro - {e}")
PYEOF

# Log
echo "$(date '+%Y-%m-%d %H:%M:%S') CALENDARIO: lembrete enviado (mensal$([ "$IS_TRIMESTRAL" = true ] && echo '+trimestral')$([ "$IS_SEMESTRAL" = true ] && echo '+semestral'))" >> "$LOG_FILE"
