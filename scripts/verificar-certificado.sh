#!/bin/bash
# =============================================================================
# Script de Verificação do Certificado SSL - Horário Inteligente
# =============================================================================
# Verifica a validade do certificado e envia alertas via Telegram
# Executado diariamente via cron às 9h
# =============================================================================

CERT_PATH="/etc/letsencrypt/live/horariointeligente.com.br-0001/fullchain.pem"
LOG_FILE="/var/log/certificado-ssl.log"
ALERT_DAYS=30  # Dias antes da expiração para alertar
CRITICAL_DAYS=7  # Dias críticos

# Carregar tokens do .env (nunca hardcoded)
if [ -f /root/sistema_agendamento/.env ]; then
    TELEGRAM_BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' /root/sistema_agendamento/.env | cut -d'=' -f2-)
    TELEGRAM_CHAT_ID=$(grep '^TELEGRAM_CHAT_ID=' /root/sistema_agendamento/.env | cut -d'=' -f2-)
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "ERRO: TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID nao encontrados no .env"
    exit 1
fi

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

send_telegram() {
    local message="$1"

    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{
            \"chat_id\": \"${TELEGRAM_CHAT_ID}\",
            \"text\": \"${message}\",
            \"parse_mode\": \"HTML\"
        }" > /dev/null 2>&1
}

# Verificar se o certificado existe
if [ ! -f "$CERT_PATH" ]; then
    log_message "ERRO: Certificado não encontrado em $CERT_PATH"
    send_telegram "🚨 <b>ERRO CRÍTICO</b>%0A%0ACertificado SSL não encontrado!%0ACaminho: $CERT_PATH"
    exit 1
fi

# Obter data de expiração
EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_PATH" | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

# Formatar data para exibição
EXPIRY_FORMATTED=$(date -d "$EXPIRY_DATE" '+%d/%m/%Y')

log_message "Verificação: Certificado expira em $DAYS_LEFT dias ($EXPIRY_DATE)"

# Verificar níveis de alerta
if [ $DAYS_LEFT -le 0 ]; then
    # EXPIRADO
    MESSAGE="🚨 <b>CERTIFICADO SSL EXPIRADO!</b>

O certificado SSL do Horário Inteligente <b>EXPIROU!</b>

📅 Expirou em: ${EXPIRY_FORMATTED}
🌐 Domínio: *.horariointeligente.com.br

<b>Execute URGENTE:</b>
<code>sudo /root/sistema_agendamento/scripts/renovar-certificado-wildcard.sh</code>

⏰ $(date '+%d/%m/%Y %H:%M')"

    log_message "CRITICO: Certificado EXPIRADO!"
    send_telegram "$MESSAGE"

elif [ $DAYS_LEFT -le $CRITICAL_DAYS ]; then
    # CRÍTICO (7 dias ou menos)
    MESSAGE="⚠️ <b>ALERTA CRÍTICO - SSL</b>

O certificado SSL expira em <b>${DAYS_LEFT} dias!</b>

📅 Expira em: ${EXPIRY_FORMATTED}
🌐 Domínio: *.horariointeligente.com.br

<b>Execute a renovação:</b>
<code>sudo /root/sistema_agendamento/scripts/renovar-certificado-wildcard.sh</code>

⏰ $(date '+%d/%m/%Y %H:%M')"

    log_message "CRITICO: Certificado expira em $DAYS_LEFT dias"
    send_telegram "$MESSAGE"

elif [ $DAYS_LEFT -le 14 ]; then
    # URGENTE (14 dias ou menos)
    MESSAGE="⚡ <b>ALERTA SSL - URGENTE</b>

O certificado SSL expira em <b>${DAYS_LEFT} dias</b>.

📅 Expira em: ${EXPIRY_FORMATTED}
🌐 Domínio: *.horariointeligente.com.br

Agende a renovação em breve.

⏰ $(date '+%d/%m/%Y %H:%M')"

    log_message "URGENTE: Certificado expira em $DAYS_LEFT dias"
    send_telegram "$MESSAGE"

elif [ $DAYS_LEFT -le $ALERT_DAYS ]; then
    # AVISO (30 dias ou menos) - apenas log, sem Telegram diário
    log_message "AVISO: Certificado expira em $DAYS_LEFT dias"
fi

# Criar arquivo de status para monitoramento
cat > /var/run/ssl-cert-status.json << EOF
{
    "domain": "horariointeligente.com.br",
    "type": "wildcard",
    "expiry_date": "$EXPIRY_DATE",
    "expiry_formatted": "$EXPIRY_FORMATTED",
    "days_left": $DAYS_LEFT,
    "status": "$([ $DAYS_LEFT -le $CRITICAL_DAYS ] && echo 'critical' || ([ $DAYS_LEFT -le $ALERT_DAYS ] && echo 'warning' || echo 'ok'))",
    "last_check": "$(date -Iseconds)",
    "cert_path": "$CERT_PATH"
}
EOF

exit 0
