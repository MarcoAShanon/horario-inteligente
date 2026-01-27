#!/bin/bash
# =============================================================================
# Utilitário para enviar alertas via Telegram - Horário Inteligente
# =============================================================================
# Uso: ./telegram-alerta.sh "Sua mensagem aqui"
# Ou:  ./telegram-alerta.sh --tipo erro "Descrição do erro"
# =============================================================================

TELEGRAM_BOT_TOKEN="8276546106:AAH3ssg8G7InAUCI_Ixlc8g_m4FF7mPsH-0"
TELEGRAM_CHAT_ID="8134518132"

send_telegram() {
    local message="$1"

    response=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{
            \"chat_id\": \"${TELEGRAM_CHAT_ID}\",
            \"text\": \"${message}\",
            \"parse_mode\": \"HTML\"
        }")

    if echo "$response" | grep -q '"ok":true'; then
        echo "✅ Mensagem enviada com sucesso!"
    else
        echo "❌ Erro ao enviar mensagem:"
        echo "$response"
    fi
}

# Verificar argumentos
if [ $# -eq 0 ]; then
    echo "Uso: $0 [--tipo TIPO] MENSAGEM"
    echo ""
    echo "Tipos disponíveis:"
    echo "  info     - Informação geral"
    echo "  aviso    - Aviso/Warning"
    echo "  erro     - Erro do sistema"
    echo "  sucesso  - Operação bem-sucedida"
    echo ""
    echo "Exemplo: $0 --tipo erro 'Falha no backup do banco'"
    exit 1
fi

TIPO=""
MENSAGEM=""

# Processar argumentos
while [ $# -gt 0 ]; do
    case "$1" in
        --tipo)
            TIPO="$2"
            shift 2
            ;;
        *)
            MENSAGEM="$*"
            break
            ;;
    esac
done

# Formatar mensagem baseado no tipo
case "$TIPO" in
    info)
        FORMATTED="ℹ️ <b>INFORMAÇÃO</b>

${MENSAGEM}

⏰ $(date '+%d/%m/%Y %H:%M')"
        ;;
    aviso)
        FORMATTED="⚠️ <b>AVISO</b>

${MENSAGEM}

⏰ $(date '+%d/%m/%Y %H:%M')"
        ;;
    erro)
        FORMATTED="🔴 <b>ERRO NO SISTEMA</b>

${MENSAGEM}

⏰ $(date '+%d/%m/%Y %H:%M')"
        ;;
    sucesso)
        FORMATTED="✅ <b>SUCESSO</b>

${MENSAGEM}

⏰ $(date '+%d/%m/%Y %H:%M')"
        ;;
    *)
        FORMATTED="📢 <b>HORÁRIO INTELIGENTE</b>

${MENSAGEM}

⏰ $(date '+%d/%m/%Y %H:%M')"
        ;;
esac

send_telegram "$FORMATTED"
