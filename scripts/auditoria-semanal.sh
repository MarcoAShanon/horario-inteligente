#!/bin/bash
# =============================================================================
# Auditoria de Seguranca Semanal - Horario Inteligente
# =============================================================================
# Executa verificacoes automatizadas de seguranca e envia relatorio via Telegram.
# Cron: sabados 03:00 BRT (06:00 UTC)
# =============================================================================

set -u

# --- Configuracao ---
ENV_FILE="/root/sistema_agendamento/.env"
PROJECT_DIR="/root/sistema_agendamento"
LOG_FILE="/var/log/auditoria-semanal.log"
CERT_PATH="/etc/letsencrypt/live/horariointeligente.com.br-0001/fullchain.pem"
SYSTEMD_SERVICE="horariointeligente.service"
NGINX_CONF="/etc/nginx/sites-available/horariointeligente"
NGINX_GLOBAL="/etc/nginx/nginx.conf"
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python3"

# --- Carregar credenciais Telegram do .env ---
if [ ! -f "$ENV_FILE" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERRO: .env nao encontrado" >> "$LOG_FILE"
    exit 1
fi

TELEGRAM_BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d'=' -f2-)
TELEGRAM_CHAT_ID=$(grep '^TELEGRAM_CHAT_ID=' "$ENV_FILE" | cut -d'=' -f2-)

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERRO: credenciais Telegram nao encontradas" >> "$LOG_FILE"
    exit 1
fi

# --- Contadores ---
PASS=0
FAIL=0
WARN=0
REPORT=""
CRITICAL_ITEMS=""

DATA_BRT=$(TZ="America/Sao_Paulo" date '+%d/%m/%Y %H:%M')

add_result() {
    local section="$1"
    local label="$2"
    local status="$3"  # PASS, FAIL, WARN
    local detail="${4:-}"

    case "$status" in
        PASS)
            REPORT="${REPORT}\n✅ ${label}"
            PASS=$((PASS + 1))
            ;;
        FAIL)
            if [ -n "$detail" ]; then
                REPORT="${REPORT}\n❌ ${label}: ${detail}"
                CRITICAL_ITEMS="${CRITICAL_ITEMS}\n• ${label}: ${detail}"
            else
                REPORT="${REPORT}\n❌ ${label}"
                CRITICAL_ITEMS="${CRITICAL_ITEMS}\n• ${label}"
            fi
            FAIL=$((FAIL + 1))
            ;;
        WARN)
            if [ -n "$detail" ]; then
                REPORT="${REPORT}\n⚠️ ${label}: ${detail}"
            else
                REPORT="${REPORT}\n⚠️ ${label}"
            fi
            WARN=$((WARN + 1))
            ;;
    esac
}

add_section() {
    REPORT="${REPORT}\n\n--- ${1} ---"
}

# =============================================================================
# SECAO 1 - SEGREDOS
# =============================================================================
add_section "Secao 1: Segredos"

# .env permissao 600
ENV_PERM=$(stat -c '%a' "$ENV_FILE" 2>/dev/null || echo "000")
if [ "$ENV_PERM" = "600" ]; then
    add_result "1" ".env permissao" "PASS"
else
    add_result "1" ".env permissao" "FAIL" "atual: ${ENV_PERM} (esperado: 600)"
fi

# .env.backup permissao 600 ou inexistente
if [ -f "${PROJECT_DIR}/.env.backup" ]; then
    BACKUP_PERM=$(stat -c '%a' "${PROJECT_DIR}/.env.backup" 2>/dev/null || echo "000")
    if [ "$BACKUP_PERM" = "600" ]; then
        add_result "1" ".env.backup permissao" "PASS"
    else
        add_result "1" ".env.backup permissao" "FAIL" "atual: ${BACKUP_PERM} (esperado: 600)"
    fi
else
    add_result "1" ".env.backup permissao" "PASS"
fi

# Zero tokens hardcoded em .py
PY_TOKENS=$(grep -rn "TELEGRAM_BOT_TOKEN\|TELEGRAM_CHAT_ID\|TELEGRAM_ADMIN\|sk-ant-\|sk-proj-\|EAAb" \
    "${PROJECT_DIR}/app/" --include="*.py" 2>/dev/null \
    | grep -v "os\.getenv\|os\.environ\|\.get(\|__pycache__" \
    | wc -l)
PY_TOKENS=${PY_TOKENS:-0}
if [ "$PY_TOKENS" -eq 0 ]; then
    add_result "1" "Tokens hardcoded .py" "PASS"
else
    add_result "1" "Tokens hardcoded .py" "FAIL" "${PY_TOKENS} encontrado(s)"
fi

# Zero tokens hardcoded em .sh
SH_TOKENS=$(grep -rn "BOT_TOKEN=\|CHAT_ID=" "${PROJECT_DIR}/scripts/" --include="*.sh" 2>/dev/null \
    | grep -v "grep\|cut -d\|\.env" \
    | wc -l)
SH_TOKENS=${SH_TOKENS:-0}
if [ "$SH_TOKENS" -eq 0 ]; then
    add_result "1" "Tokens hardcoded .sh" "PASS"
else
    add_result "1" "Tokens hardcoded .sh" "FAIL" "${SH_TOKENS} encontrado(s)"
fi

# Systemd sem chaves inline + usa EnvironmentFile
INLINE_KEYS=$(grep "^Environment=" /etc/systemd/system/${SYSTEMD_SERVICE} 2>/dev/null \
    | grep -icE "SECRET_KEY|API_KEY|TOKEN|PASSWORD" || true)
INLINE_KEYS=${INLINE_KEYS:-0}
HAS_ENVFILE=$(grep -c "^EnvironmentFile=" /etc/systemd/system/${SYSTEMD_SERVICE} 2>/dev/null || echo "0")
if [ "$INLINE_KEYS" -eq 0 ] && [ "$HAS_ENVFILE" -gt 0 ]; then
    add_result "1" "Systemd seguro" "PASS"
elif [ "$INLINE_KEYS" -gt 0 ]; then
    add_result "1" "Systemd seguro" "FAIL" "chaves inline encontradas"
else
    add_result "1" "Systemd seguro" "WARN" "sem EnvironmentFile"
fi

# =============================================================================
# SECAO 2 - JWT
# =============================================================================
add_section "Secao 2: JWT"

# Zero fallbacks de SECRET_KEY
JWT_FALLBACKS=$(grep -rn 'getenv.*SECRET_KEY.*"' "${PROJECT_DIR}/app/" --include="*.py" 2>/dev/null \
    | grep -v "__pycache__" \
    | grep -c 'getenv("SECRET_KEY",' || true)
JWT_FALLBACKS=${JWT_FALLBACKS:-0}
if [ "$JWT_FALLBACKS" -eq 0 ]; then
    add_result "2" "Fallbacks SECRET_KEY" "PASS"
else
    add_result "2" "Fallbacks SECRET_KEY" "FAIL" "${JWT_FALLBACKS} fallback(s)"
fi

# =============================================================================
# SECAO 6 - INFRAESTRUTURA
# =============================================================================
add_section "Secao 6: Infraestrutura"

# Servico roda como usuario nao-root
SVC_USER=$(grep "^User=" /etc/systemd/system/${SYSTEMD_SERVICE} 2>/dev/null | cut -d'=' -f2)
SVC_USER=${SVC_USER:-}
if [ -n "$SVC_USER" ] && [ "$SVC_USER" != "root" ]; then
    add_result "6" "Servico nao-root" "PASS"
else
    add_result "6" "Servico nao-root" "FAIL" "usuario: ${SVC_USER:-nao definido}"
fi

# Sem --reload em producao
HAS_RELOAD=$(grep "ExecStart=" /etc/systemd/system/${SYSTEMD_SERVICE} 2>/dev/null | grep -c "\-\-reload" || true)
HAS_RELOAD=${HAS_RELOAD:-0}
if [ "$HAS_RELOAD" -eq 0 ]; then
    add_result "6" "Sem --reload producao" "PASS"
else
    add_result "6" "Sem --reload producao" "FAIL" "--reload presente"
fi

# Redis bind localhost
REDIS_BIND=$(grep "^bind " /etc/redis/redis.conf 2>/dev/null || echo "")
if echo "$REDIS_BIND" | grep -q "127.0.0.1"; then
    add_result "6" "Redis bind localhost" "PASS"
else
    add_result "6" "Redis bind localhost" "FAIL" "bind: ${REDIS_BIND:-nao configurado}"
fi

# Firewall ufw ativo
UFW_STATUS=$(ufw status 2>/dev/null | head -1 || echo "inactive")
if echo "$UFW_STATUS" | grep -qi "active"; then
    add_result "6" "Firewall ufw" "PASS"
else
    add_result "6" "Firewall ufw" "WARN" "ufw inativo"
fi

# =============================================================================
# SECAO 7 - HTTP
# =============================================================================
add_section "Secao 7: HTTP"

# Nginx server_tokens off
TOKENS_OFF=$(grep -c "server_tokens off" "$NGINX_GLOBAL" 2>/dev/null || echo "0")
if [ "$TOKENS_OFF" -gt 0 ]; then
    add_result "7" "Nginx server_tokens off" "PASS"
else
    add_result "7" "Nginx server_tokens off" "FAIL" "nao configurado"
fi

# HSTS configurado no Nginx
HAS_HSTS=$(grep -c "Strict-Transport-Security" "$NGINX_CONF" 2>/dev/null || echo "0")
if [ "$HAS_HSTS" -gt 0 ]; then
    add_result "7" "HSTS no Nginx" "PASS"
else
    add_result "7" "HSTS no Nginx" "FAIL" "ausente"
fi

# =============================================================================
# SECAO 8 - RATE LIMITING
# =============================================================================
add_section "Secao 8: Rate Limiting"

# Decoradores @limiter presentes (minimo 5 endpoints)
LIMITER_COUNT=$(grep -rn "@limiter.limit" "${PROJECT_DIR}/app/" --include="*.py" 2>/dev/null \
    | grep -vc "__pycache__" || true)
LIMITER_COUNT=${LIMITER_COUNT:-0}
if [ "$LIMITER_COUNT" -ge 5 ]; then
    add_result "8" "Rate limiting (${LIMITER_COUNT} endpoints)" "PASS"
elif [ "$LIMITER_COUNT" -ge 1 ]; then
    add_result "8" "Rate limiting (${LIMITER_COUNT} endpoints)" "WARN" "minimo recomendado: 5"
else
    add_result "8" "Rate limiting" "FAIL" "nenhum @limiter encontrado"
fi

# =============================================================================
# SECAO 10 - DEPENDENCIAS
# =============================================================================
add_section "Secao 10: Dependencias"

# pip-audit para CVEs
if [ -x "${PROJECT_DIR}/venv/bin/pip-audit" ]; then
    CVE_OUTPUT=$("${PROJECT_DIR}/venv/bin/pip-audit" --require-hashes=false -r "${PROJECT_DIR}/requirements.txt" 2>&1 || true)
    CVE_COUNT=$(echo "$CVE_OUTPUT" | grep -cE "^[a-zA-Z].*PYSEC-|^[a-zA-Z].*CVE-" || true)
    CVE_COUNT=${CVE_COUNT:-0}
    if [ "$CVE_COUNT" -eq 0 ]; then
        add_result "10" "CVEs (pip-audit)" "PASS"
    else
        add_result "10" "CVEs (pip-audit)" "FAIL" "${CVE_COUNT} vulnerabilidade(s)"
    fi
else
    add_result "10" "CVEs (pip-audit)" "WARN" "pip-audit nao instalado"
fi

# Dependencias sem pin de versao
UNPIN=$(grep -vE '==|^#|^$|^-' "${PROJECT_DIR}/requirements.txt" 2>/dev/null | wc -l)
UNPIN=${UNPIN:-0}
if [ "$UNPIN" -eq 0 ]; then
    add_result "10" "Deps pinadas" "PASS"
else
    add_result "10" "Deps pinadas" "WARN" "${UNPIN} sem pin exato"
fi

# =============================================================================
# SSL - CERTIFICADO
# =============================================================================
add_section "SSL"

if [ -f "$CERT_PATH" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_PATH" 2>/dev/null | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || echo "0")
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    if [ "$DAYS_LEFT" -gt 30 ]; then
        add_result "SSL" "Certificado (${DAYS_LEFT} dias)" "PASS"
    elif [ "$DAYS_LEFT" -ge 8 ]; then
        add_result "SSL" "Certificado (${DAYS_LEFT} dias)" "WARN" "renovar em breve"
    else
        add_result "SSL" "Certificado (${DAYS_LEFT} dias)" "FAIL" "expira em ${DAYS_LEFT} dia(s)!"
    fi
else
    add_result "SSL" "Certificado" "FAIL" "arquivo nao encontrado"
fi

# =============================================================================
# SAUDE DOS SERVICOS
# =============================================================================
add_section "Saude dos Servicos"

# 1. App HTTP 200
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8000/docs 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    add_result "SVC" "App HTTP" "PASS"
else
    add_result "SVC" "App HTTP" "FAIL" "HTTP ${HTTP_CODE}"
fi

# 2. SMTP login sem envio (Python smtplib - heredoc single-quoted para evitar escaping)
SMTP_RESULT=$($VENV_PYTHON << 'PYEOF'
import smtplib, ssl
try:
    env = {}
    with open("/root/sistema_agendamento/.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    host = env.get("SMTP_HOST", "")
    port = int(env.get("SMTP_PORT", "465"))
    user = env.get("SMTP_USER", "")
    pwd = env.get("SMTP_PASSWORD", "")
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=ctx, timeout=15) as s:
        s.login(user, pwd)
    print("OK")
except Exception as e:
    print(f"FAIL:{e}")
PYEOF
)
if [ "$SMTP_RESULT" = "OK" ]; then
    add_result "SVC" "Email SMTP" "PASS"
else
    SMTP_ERR=$(echo "$SMTP_RESULT" | sed 's/^FAIL://')
    add_result "SVC" "Email SMTP" "FAIL" "$SMTP_ERR"
fi

# 3. Telegram bot ativo (curl getMe)
TG_RESULT=$(curl -s --max-time 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" 2>/dev/null || echo "")
if echo "$TG_RESULT" | grep -q '"ok":true'; then
    add_result "SVC" "Telegram Bot" "PASS"
else
    add_result "SVC" "Telegram Bot" "FAIL" "getMe falhou"
fi

# 4. ASAAS API key valida (Python urllib - heredoc single-quoted)
ASAAS_RESULT=$($VENV_PYTHON << 'PYEOF'
import urllib.request, urllib.error
try:
    env = {}
    with open("/root/sistema_agendamento/.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    api_key = env.get("ASAAS_API_KEY", "")
    req = urllib.request.Request(
        "https://api.asaas.com/v3/customers?limit=1",
        headers={"access_token": api_key}
    )
    resp = urllib.request.urlopen(req, timeout=15)
    if resp.getcode() == 200:
        print("OK")
    else:
        print(f"FAIL:HTTP {resp.getcode()}")
except Exception as e:
    print(f"FAIL:{e}")
PYEOF
)
if [ "$ASAAS_RESULT" = "OK" ]; then
    add_result "SVC" "ASAAS API" "PASS"
else
    ASAAS_ERR=$(echo "$ASAAS_RESULT" | sed 's/^FAIL://')
    add_result "SVC" "ASAAS API" "FAIL" "$ASAAS_ERR"
fi

# 5. PostgreSQL SELECT 1 (Python psycopg2 - heredoc single-quoted)
PG_RESULT=$($VENV_PYTHON << 'PYEOF'
try:
    env = {}
    with open("/root/sistema_agendamento/.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    import psycopg2
    conn = psycopg2.connect(env.get("DATABASE_URL", ""), connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    cur.close()
    conn.close()
    print("OK")
except Exception as e:
    print(f"FAIL:{e}")
PYEOF
)
if [ "$PG_RESULT" = "OK" ]; then
    add_result "SVC" "PostgreSQL" "PASS"
else
    PG_ERR=$(echo "$PG_RESULT" | sed 's/^FAIL://')
    add_result "SVC" "PostgreSQL" "FAIL" "$PG_ERR"
fi

# 6. Redis PING (Python redis - heredoc single-quoted)
REDIS_RESULT=$($VENV_PYTHON << 'PYEOF'
try:
    env = {}
    with open("/root/sistema_agendamento/.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    import redis
    r = redis.from_url(env.get("REDIS_URL", "redis://localhost:6379/0"), socket_timeout=10)
    if r.ping():
        print("OK")
    else:
        print("FAIL:PING retornou False")
except Exception as e:
    print(f"FAIL:{e}")
PYEOF
)
if [ "$REDIS_RESULT" = "OK" ]; then
    add_result "SVC" "Redis" "PASS"
else
    REDIS_ERR=$(echo "$REDIS_RESULT" | sed 's/^FAIL://')
    add_result "SVC" "Redis" "FAIL" "$REDIS_ERR"
fi

# =============================================================================
# MONTAR E ENVIAR RELATORIO
# =============================================================================
TOTAL=$((PASS + FAIL + WARN))

# Determinar status geral
if [ "$FAIL" -gt 0 ]; then
    HEADER="🔴 AUDITORIA SEMANAL - CRITICO"
elif [ "$WARN" -gt 0 ]; then
    HEADER="⚠️ AUDITORIA SEMANAL - ATENCAO"
else
    HEADER="✅ AUDITORIA SEMANAL - APROVADO"
fi

SUMMARY="${HEADER}\n📅 ${DATA_BRT} (BRT)\n\nResumo: ${PASS}/${TOTAL} aprovados | ${FAIL} falha(s) | ${WARN} aviso(s)"

FULL_REPORT="${SUMMARY}${REPORT}"

# Adicionar itens criticos se houver falhas
if [ "$FAIL" -gt 0 ] && [ -n "$CRITICAL_ITEMS" ]; then
    FULL_REPORT="${FULL_REPORT}\n\n🚨 ITENS CRITICOS:${CRITICAL_ITEMS}"
fi

# Renderizar e truncar a 4000 chars (limite Telegram 4096, reserva para JSON)
FULL_REPORT_RENDERED=$(echo -e "$FULL_REPORT")
if [ ${#FULL_REPORT_RENDERED} -gt 4000 ]; then
    FULL_REPORT_RENDERED="${FULL_REPORT_RENDERED:0:3950}

⚠️ [Relatorio truncado - ver log completo]"
fi

# Log local (antes do envio, para garantir registro mesmo se Telegram falhar)
echo "$(date '+%Y-%m-%d %H:%M:%S') --- AUDITORIA SEMANAL ---" >> "$LOG_FILE"
echo "$FULL_REPORT_RENDERED" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Enviar via Telegram - usar python3 json.dumps para escapar caracteres especiais
$VENV_PYTHON << 'PYEOF'
import json, urllib.request, sys

# Ler relatorio do stdin nao funciona com heredoc, entao ler do log
import subprocess
log_file = "/var/log/auditoria-semanal.log"
env_file = "/root/sistema_agendamento/.env"

# Ler credenciais
env = {}
with open(env_file) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

bot_token = env.get("TELEGRAM_BOT_TOKEN", "")
chat_id = env.get("TELEGRAM_CHAT_ID", "")

# Ler ultimas linhas do log (o relatorio recem adicionado)
with open(log_file) as f:
    content = f.read()

# Extrair o ultimo bloco de auditoria
marker = "--- AUDITORIA SEMANAL ---"
last_idx = content.rfind(marker)
if last_idx >= 0:
    # Pegar a linha com timestamp + todo o conteudo ate o fim
    line_start = content.rfind("\n", 0, last_idx)
    text = content[line_start+1:].strip()
else:
    text = "Erro: relatorio nao encontrado no log"

# Truncar se necessario
if len(text) > 4000:
    text = text[:3950] + "\n\n⚠️ [Relatorio truncado - ver log completo]"

payload = json.dumps({
    "chat_id": chat_id,
    "text": text,
    "parse_mode": ""
})
req = urllib.request.Request(
    f"https://api.telegram.org/bot{bot_token}/sendMessage",
    data=payload.encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req, timeout=30)
    print("Telegram: enviado com sucesso")
except Exception as e:
    print(f"Telegram: erro ao enviar - {e}")
PYEOF

echo "Auditoria semanal concluida: ${PASS} pass / ${FAIL} fail / ${WARN} warn"
