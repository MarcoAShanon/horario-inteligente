# Auditoria de Seguranca - Sistema Horario Inteligente

**Prompt executavel** para auditoria completa do sistema de agendamento medico SaaS.
Cada secao e autocontida: inclui o que verificar, arquivos exatos, comandos bash, criterios de aprovacao/reprovacao e acoes corretivas.

**Base de codigo:** `/root/sistema_agendamento/`
**Stack:** FastAPI + PostgreSQL + Redis + Nginx + Uvicorn
**Dominio:** `horariointeligente.com.br` (multi-tenant via subdominio)

---

## Secao 1 - Gestao de Segredos

### O que verificar
O sistema armazena segredos (API keys, tokens, senhas) em `.env`, scripts shell e codigo Python.
Verificar se ha segredos hardcoded, se `.env` tem permissoes restritivas e se o systemd nao expoe chaves.

### Arquivos e linhas exatas

| Arquivo | Linha | Problema |
|---------|-------|----------|
| `/root/sistema_agendamento/.env` | 8, 25-28, 35, 39, 66, 71-72, 75, 80, 82 | 10+ API keys em texto plano (SECRET_KEY, WhatsApp, Anthropic, OpenAI, SMTP, Telegram, VAPID, Asaas) |
| `/root/sistema_agendamento/app/services/telegram_service.py` | 13-14 | Token Telegram hardcoded no codigo: `TELEGRAM_BOT_TOKEN = "8276546106:..."` |
| `/root/sistema_agendamento/scripts/telegram-alerta.sh` | 9-10 | Token Telegram hardcoded em shell script |
| `/root/sistema_agendamento/scripts/verificar-certificado.sh` | 15-16 | Token Telegram hardcoded em shell script |
| `/etc/systemd/system/horariointeligente.service` | 14 | `ANTHROPIC_API_KEY` exposta diretamente no arquivo de servico |
| `/etc/systemd/system/horariointeligente.service` | 16 | `SECRET_KEY=sua-chave-secreta-super-segura-aqui-123` (placeholder fraco) |

### Comandos bash

```bash
# 1. Verificar permissoes do .env
ls -la /root/sistema_agendamento/.env

# 2. Buscar tokens hardcoded em Python (excluindo venv)
grep -rn "TELEGRAM_BOT_TOKEN\|TELEGRAM_CHAT_ID\|TELEGRAM_ADMIN" /root/sistema_agendamento/app/ --include="*.py"

# 3. Buscar tokens hardcoded em shell scripts
grep -rn "BOT_TOKEN\|CHAT_ID" /root/sistema_agendamento/scripts/ --include="*.sh"

# 4. Verificar segredos no systemd
grep -n "Environment=" /etc/systemd/system/horariointeligente.service

# 5. Buscar API keys hardcoded no codigo (nao devem existir)
grep -rn "sk-ant-\|sk-proj-\|EAAb" /root/sistema_agendamento/app/ --include="*.py"

# 6. Verificar se .env.backup tambem esta exposto
ls -la /root/sistema_agendamento/.env.backup
```

### Criterios de aprovacao/reprovacao

| Criterio | Aprovado | Reprovado |
|----------|----------|-----------|
| `.env` com permissao 600 (owner-only) | `rw-------` | `rw-r--r--` (644) ou mais aberto |
| Zero tokens hardcoded em `.py` e `.sh` | Nenhum resultado nos greps | Qualquer match |
| Systemd sem API keys inline | Zero `Environment=` com chaves | Qualquer chave exposta |
| `.env.backup` com permissao 600 ou inexistente | `rw-------` ou nao existe | Qualquer outro valor |

### Acoes corretivas

```bash
# Restringir permissoes do .env
chmod 600 /root/sistema_agendamento/.env
chmod 600 /root/sistema_agendamento/.env.backup 2>/dev/null

# Mover segredos do telegram_service.py para .env
# Em telegram_service.py, substituir linhas 13-14 por:
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Remover API keys do systemd - usar EnvironmentFile
# No horariointeligente.service, substituir Environment= por:
# EnvironmentFile=/root/sistema_agendamento/.env

# Rotacionar TODAS as chaves expostas (WhatsApp, Anthropic, OpenAI, Telegram, SMTP, Asaas, VAPID)
```

---

## Secao 2 - Autenticacao & JWT

### O que verificar
O sistema usa JWT (HS256) para autenticacao. Multiplos modulos reimplementam a validacao de token com fallback SECRET_KEY inseguros. Verificar se ha refresh token, se a expiracao e adequada e se todos os modulos usam a mesma chave.

### Arquivos e linhas exatas

| Arquivo | Linha | Detalhe |
|---------|-------|---------|
| `/root/sistema_agendamento/app/api/auth.py` | 26-28 | `SECRET_KEY = os.getenv("SECRET_KEY")` - **CORRETO**, levanta RuntimeError se nao definida |
| `/root/sistema_agendamento/app/api/parceiro_auth.py` | 24 | `SECRET_KEY = os.getenv("SECRET_KEY", "parceiro-secret-key-change-in-production")` - **INSEGURO** |
| `/root/sistema_agendamento/app/api/financeiro.py` | 23 | `SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")` - **INSEGURO** |
| `/root/sistema_agendamento/app/api/admin.py` | 27 | `SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")` - **INSEGURO** |
| `/root/sistema_agendamento/app/api/websocket.py` | 19 | `SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")` - **INSEGURO** |
| `/root/sistema_agendamento/app/main.py` | 146 | CSRF secret_key com fallback `"csrf-secret-key-change-in-production"` |
| `/root/sistema_agendamento/app/api/auth.py` | 49 | JWT encode com HS256, expiracao padrao |
| `/root/sistema_agendamento/app/api/websocket.py` | 26 | `jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])` |
| `/root/sistema_agendamento/app/api/websocket.py` | 37 | Token recebido via query string: `token: Optional[str] = Query(None)` |

### Comandos bash

```bash
# 1. Buscar todos os fallbacks de SECRET_KEY
grep -rn 'getenv.*SECRET_KEY.*"' /root/sistema_agendamento/app/ --include="*.py"

# 2. Verificar algoritmo JWT usado
grep -rn "HS256\|RS256\|algorithm" /root/sistema_agendamento/app/api/ --include="*.py"

# 3. Verificar expiracao do token
grep -rn "expires_delta\|timedelta\|exp" /root/sistema_agendamento/app/api/auth.py

# 4. Buscar refresh token (deve existir, provavelmente nao existe)
grep -rn "refresh_token\|refresh" /root/sistema_agendamento/app/api/ --include="*.py"

# 5. Verificar se token JWT e passado via URL (risco de log)
grep -rn "Query.*token\|token.*Query" /root/sistema_agendamento/app/api/websocket.py
```

### Criterios de aprovacao/reprovacao

| Criterio | Aprovado | Reprovado |
|----------|----------|-----------|
| Zero fallbacks de SECRET_KEY | Nenhum `os.getenv("SECRET_KEY", "...")` | Qualquer fallback encontrado |
| Expiracao JWT <= 1 hora | `timedelta(minutes=60)` ou menos | > 1 hora (atual: 8 horas) |
| Refresh token implementado | Endpoint `/refresh` existe | Nao existe |
| Token WebSocket via header, nao URL | Header `Authorization` | Query parameter `?token=` |
| SECRET_KEY unica centralizada | Um unico modulo define a chave | Multiplas redefinicoes |

### Acoes corretivas

```python
# 1. Remover TODOS os fallbacks - em cada arquivo, usar:
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY nao configurada")

# 2. Centralizar JWT em um unico modulo (ex: app/core/security.py)
# Todos os outros importam dele

# 3. Reduzir expiracao para 30-60 minutos e implementar refresh token

# 4. WebSocket: usar subprotocolo para enviar token em vez de query string
# Ou usar cookie HttpOnly com o token
```

---

## Secao 3 - SQL Injection

### O que verificar
O sistema usa SQLAlchemy, mas ha queries construidas com f-strings que podem permitir SQL injection se colunas ou valores vierem de input do usuario.

### Arquivos e linhas exatas

| Arquivo | Linha | Query |
|---------|-------|-------|
| `/root/sistema_agendamento/app/api/parceiros_comerciais.py` | 348 | f-string UPDATE |
| `/root/sistema_agendamento/app/api/admin_clientes.py` | 209 | f-string SELECT |
| `/root/sistema_agendamento/app/api/admin_clientes.py` | 848 | f-string UPDATE |
| `/root/sistema_agendamento/app/api/usuarios_internos.py` | 290 | f-string UPDATE |
| `/root/sistema_agendamento/app/api/user_management.py` | 836 | f-string UPDATE |
| `/root/sistema_agendamento/app/api/user_management.py` | 866 | f-string UPDATE |
| `/root/sistema_agendamento/app/api/financeiro.py` | 852 | f-string UPDATE |
| `/root/sistema_agendamento/app/api/custos_operacionais.py` | 407 | f-string UPDATE |
| `/root/sistema_agendamento/test_pushname_fix.py` | 139 | f-string SELECT com interpolacao direta (arquivo de teste) |

### Comandos bash

```bash
# 1. Buscar todas as queries com f-string (excluindo venv e __pycache__)
grep -rn 'f"SELECT\|f"UPDATE\|f"INSERT\|f"DELETE\|f"ALTER' /root/sistema_agendamento/app/ --include="*.py"

# 2. Verificar se ha text() do SQLAlchemy com f-string
grep -rn 'text(f"' /root/sistema_agendamento/app/ --include="*.py"

# 3. Buscar execute() com strings formatadas
grep -rn 'execute.*f"' /root/sistema_agendamento/app/ --include="*.py"

# 4. Verificar se parametros sao usados corretamente (bind parameters)
grep -rn ':param\|bindparam\|\.params(' /root/sistema_agendamento/app/ --include="*.py"

# 5. Buscar .format() em queries SQL (outra forma de injection)
grep -rn '\.format.*SELECT\|\.format.*UPDATE\|\.format.*INSERT' /root/sistema_agendamento/app/ --include="*.py"
```

### Criterios de aprovacao/reprovacao

| Criterio | Aprovado | Reprovado |
|----------|----------|-----------|
| Zero f-strings em queries SQL | Nenhum `f"SELECT/UPDATE/INSERT/DELETE"` | Qualquer match |
| Todas as queries usam bind parameters | `text("SELECT ... WHERE id = :id")` com `.params(id=x)` | Concatenacao de strings |
| Nomes de colunas vindos de whitelist | Coluna validada contra lista fixa | Coluna vinda diretamente do request |

### Acoes corretivas

```python
# ANTES (vulneravel):
query = f"UPDATE tabela SET {coluna} = :valor WHERE id = :id"

# DEPOIS (seguro):
ALLOWED_COLUMNS = {"nome", "email", "telefone"}
if coluna not in ALLOWED_COLUMNS:
    raise ValueError(f"Coluna invalida: {coluna}")
query = text(f"UPDATE tabela SET {coluna} = :valor WHERE id = :id")
result = await db.execute(query, {"valor": valor, "id": id})
```

---

## Secao 4 - Isolamento Multi-Tenant

### O que verificar
O sistema e SaaS multi-tenant. Cada clinica (cliente) acessa via subdominio. Verificar se ha vazamento de dados entre tenants: middleware, cache, queries sem `cliente_id`, rotas que bypassam verificacao.

### Arquivos e linhas exatas

| Arquivo | Linha | Detalhe |
|---------|-------|---------|
| `/root/sistema_agendamento/app/middleware/tenant_middleware.py` | 90-117 | Extracao de subdomain do header Host |
| `/root/sistema_agendamento/app/middleware/tenant_middleware.py` | 119-162 | Resolucao de cliente_id com cache in-memory (TENANT_CACHE) |
| `/root/sistema_agendamento/app/middleware/tenant_middleware.py` | 32-44 | Rotas JWT que bypassam verificacao de subdomain |
| `/root/sistema_agendamento/app/middleware/tenant_middleware.py` | 45-51 | Rotas admin que pulam extracao de tenant |
| `/root/sistema_agendamento/app/middleware/billing_middleware.py` | 25-66 | Rotas liberadas do billing check |
| `/root/sistema_agendamento/app/services/conversation_manager.py` | 33-42 | Redis sem TTL de cache por tenant, namespace `conversation:cliente_X:telefone` |
| `/root/sistema_agendamento/app/models/paciente.py` | 16 | `cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)` |

### Comandos bash

```bash
# 1. Verificar se todas as queries de dados filtram por cliente_id
grep -rn "cliente_id" /root/sistema_agendamento/app/api/ --include="*.py" | head -50

# 2. Buscar queries SELECT sem filtro de cliente_id (potencial vazamento)
grep -rn "SELECT.*FROM\|\.query(" /root/sistema_agendamento/app/api/ --include="*.py" | grep -v "cliente_id"

# 3. Verificar TENANT_CACHE - se tem TTL ou invalidacao
grep -rn "TENANT_CACHE\|tenant_cache" /root/sistema_agendamento/app/middleware/ --include="*.py"

# 4. Verificar se middleware aplica cliente_id em TODAS as rotas de dados
grep -rn "request.state.cliente_id" /root/sistema_agendamento/app/api/ --include="*.py" | wc -l

# 5. Verificar rotas que nao usam cliente_id
grep -rn "def.*request.*Request" /root/sistema_agendamento/app/api/ --include="*.py" | wc -l

# 6. Verificar Redis keys - se inclui cliente_id
grep -rn "redis.*set\|redis.*get\|\.set(\|\.get(" /root/sistema_agendamento/app/ --include="*.py" | head -20
```

### Criterios de aprovacao/reprovacao

| Criterio | Aprovado | Reprovado |
|----------|----------|-----------|
| 100% das queries de dados filtram por `cliente_id` | Todas incluem WHERE cliente_id | Qualquer query sem filtro |
| TENANT_CACHE tem TTL | TTL <= 300 segundos | Cache permanente (sem invalidacao) |
| Redis keys incluem cliente_id | Namespace `cliente_X:...` | Keys sem isolamento |
| Nenhuma rota de dados bypassa tenant check | Zero rotas de dados sem middleware | Qualquer rota exposta |

### Acoes corretivas

```python
# 1. Adicionar TTL ao TENANT_CACHE
import time
TENANT_CACHE = {}  # {subdomain: (cliente_id, timestamp)}
CACHE_TTL = 300  # 5 minutos

def get_cached_tenant(subdomain):
    if subdomain in TENANT_CACHE:
        cliente_id, ts = TENANT_CACHE[subdomain]
        if time.time() - ts < CACHE_TTL:
            return cliente_id
    return None

# 2. Criar decorator para garantir cliente_id em todas as queries
# 3. Auditar CADA endpoint de dados para confirmar filtro por cliente_id
```

---

## Secao 5 - Protecao de Dados / LGPD

### O que verificar
O sistema armazena dados de saude (pacientes, agendamentos medicos). A LGPD (Lei 13.709/2018) exige criptografia de PII, consentimento explicito, direito a exclusao e politica de retencao. Verificar se dados sensiveis estao protegidos em repouso e em transito.

### Arquivos e linhas exatas

| Arquivo | Linha | Detalhe |
|---------|-------|---------|
| `/root/sistema_agendamento/app/models/paciente.py` | 19-33 | Campos PII em texto plano: nome, telefone, email, cpf, data_nascimento, endereco, observacoes |
| `/root/sistema_agendamento/app/main.py` | 79-84 | Cache-Control `no-store` para APIs (bom) |
| `/root/sistema_agendamento/app/main.py` | 92-93 | HSTS apenas em producao |
| `/root/sistema_agendamento/logs/sistema.log` | - | 83MB de logs que podem conter dados de pacientes |
| `/root/sistema_agendamento/logs/webhook.log` | - | Permissao 666 (world-writable) |
| `/root/sistema_agendamento/static/politica-privacidade.html` | - | Politica de privacidade publica |

### Comandos bash

```bash
# 1. Verificar se CPF esta criptografado no banco
grep -rn "cpf\|CPF" /root/sistema_agendamento/app/models/ --include="*.py"

# 2. Buscar logging de dados sensiveis
grep -rn "logger.*cpf\|logger.*telefone\|logger.*email\|logger.*nome.*paciente" /root/sistema_agendamento/app/ --include="*.py" | head -20

# 3. Verificar se ha endpoint de exclusao de dados (right-to-deletion)
grep -rn "exclu\|delet\|apagar\|remover.*paciente\|right.*delet" /root/sistema_agendamento/app/api/ --include="*.py"

# 4. Verificar tamanho e permissoes dos logs
ls -lh /root/sistema_agendamento/logs/

# 5. Verificar se logs contem dados de pacientes
grep -c "cpf\|telefone.*[0-9]\{11\}" /root/sistema_agendamento/logs/sistema.log 2>/dev/null | head -5

# 6. Verificar se ha politica de retencao de dados
grep -rn "retencao\|retention\|purge\|cleanup\|expir" /root/sistema_agendamento/app/ --include="*.py"

# 7. Verificar criptografia em repouso (campos criptografados no modelo)
grep -rn "encrypt\|criptograf\|fernet\|AES\|cipher" /root/sistema_agendamento/app/models/ --include="*.py"

# 8. Verificar se existe endpoint de exportacao de dados (portabilidade LGPD)
grep -rn "export\|portab\|download.*dados" /root/sistema_agendamento/app/api/ --include="*.py"
```

### Criterios de aprovacao/reprovacao

| Criterio | Aprovado | Reprovado |
|----------|----------|-----------|
| CPF criptografado em repouso | Campo usa `EncryptedType` ou similar | `Column(String(14))` em texto plano |
| Logs sem PII | Zero CPF/telefone nos logs | Dados pessoais nos logs |
| Endpoint de exclusao de dados existe | `DELETE /pacientes/{id}` com cascade | Nao existe |
| Politica de retencao implementada | Job automatico de limpeza | Sem retencao definida |
| Logs com permissao restritiva | 640 ou 600 | 644 ou 666 |
| Log rotation configurado | logrotate ativo | Logs de 80MB+ |

### Acoes corretivas

```python
# 1. Criptografar CPF em repouso
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

cpf = Column(EncryptedType(String(14), KEY, AesEngine, 'pkcs5'), nullable=True)

# 2. Implementar endpoint de exclusao (LGPD Art. 18)
@router.delete("/pacientes/{paciente_id}")
async def excluir_dados_paciente(paciente_id: int, ...):
    # Excluir paciente e todos os dados relacionados
    # Gerar log de auditoria da exclusao

# 3. Configurar logrotate
# /etc/logrotate.d/sistema_agendamento
# /root/sistema_agendamento/logs/*.log {
#     daily
#     rotate 30
#     compress
#     missingok
#     notifempty
# }

# 4. Corrigir permissoes de logs
# chmod 640 /root/sistema_agendamento/logs/*.log
```

---

## Secao 6 - Infraestrutura

### O que verificar
Verificar se o servico roda como usuario nao-privilegiado, permissoes de arquivos, Redis com autenticacao, PostgreSQL com SSL, e configuracao segura do systemd.

### Arquivos e linhas exatas

| Arquivo | Linha | Detalhe |
|---------|-------|---------|
| `/etc/systemd/system/horariointeligente.service` | 8-9 | `User=root` / `Group=root` - **CRITICO** |
| `/etc/systemd/system/horariointeligente.service` | 19 | `--reload` em producao (recarrega a cada mudanca de arquivo) |
| `/etc/systemd/system/horariointeligente.service` | 14 | API key Anthropic exposta inline |
| `/etc/redis/redis.conf` | 87 | `bind 127.0.0.1 -::1` (bom, localhost only) |
| `/etc/redis/redis.conf` | 138 | `port 6379` (porta padrao) |
| `/etc/redis/redis.conf` | ~190-207 | TLS desabilitado (todas as linhas comentadas) |
| `/etc/postgresql/16/main/postgresql.conf` | 108 | `ssl = on` (bom) |
| `/etc/postgresql/16/main/postgresql.conf` | - | Certificado snakeoil (auto-assinado) |
| `/etc/postgresql/16/main/pg_hba.conf` | 125 | `scram-sha-256` para conexoes TCP (bom) |

### Comandos bash

```bash
# 1. Verificar usuario do servico
grep "User=" /etc/systemd/system/horariointeligente.service

# 2. Verificar se --reload esta em producao
grep "ExecStart" /etc/systemd/system/horariointeligente.service

# 3. Verificar processo rodando
ps aux | grep uvicorn | grep -v grep

# 4. Verificar Redis sem senha
grep "^requirepass" /etc/redis/redis.conf

# 5. Verificar Redis TLS
grep "^tls-" /etc/redis/redis.conf

# 6. Verificar PostgreSQL SSL
grep "^ssl " /etc/postgresql/16/main/postgresql.conf

# 7. Verificar certificado PostgreSQL
grep "ssl_cert_file\|ssl_key_file" /etc/postgresql/16/main/postgresql.conf

# 8. Verificar permissoes de arquivos criticos
ls -la /root/sistema_agendamento/.env
ls -la /root/sistema_agendamento/logs/
stat -c '%a %U %G %n' /etc/systemd/system/horariointeligente.service

# 9. Verificar se ha portas abertas desnecessarias
ss -tlnp | grep -E "8000|6379|5432"

# 10. Verificar firewall
ufw status 2>/dev/null || iptables -L -n 2>/dev/null | head -20
```

### Criterios de aprovacao/reprovacao

| Criterio | Aprovado | Reprovado |
|----------|----------|-----------|
| Servico roda como usuario dedicado | `User=agendamento` ou similar | `User=root` |
| Sem `--reload` em producao | Sem flag `--reload` | Flag presente |
| Redis com senha | `requirepass` configurado | Sem autenticacao |
| PostgreSQL com certificado valido | Certificado CA emitido | `snakeoil` (auto-assinado) |
| Portas internas nao expostas externamente | 6379/5432 apenas em 127.0.0.1 | Expostas em 0.0.0.0 |
| `.env` permissao 600 | `-rw-------` | Qualquer outro valor |
| `webhook.log` permissao <= 640 | `-rw-r-----` | `-rw-rw-rw-` (666) |

### Acoes corretivas

```bash
# 1. Criar usuario dedicado e migrar servico
useradd -r -s /bin/false -d /opt/sistema_agendamento agendamento
# Atualizar horariointeligente.service:
# User=agendamento
# Group=agendamento

# 2. Remover --reload do ExecStart em producao
# ExecStart=/.../uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 3. Configurar senha no Redis
# Em /etc/redis/redis.conf:
# requirepass <senha-forte-gerada>
# Em .env: REDIS_URL=redis://:senha@localhost:6379/0

# 4. Corrigir permissoes
chmod 600 /root/sistema_agendamento/.env
chmod 640 /root/sistema_agendamento/logs/webhook.log

# 5. Usar EnvironmentFile em vez de Environment= no systemd
# EnvironmentFile=/root/sistema_agendamento/.env
```

---

## Secao 7 - Seguranca HTTP

### O que verificar
Verificar CORS, CSP (Content Security Policy), CSRF, headers de seguranca, HSTS e configuracao do Nginx.

### Arquivos e linhas exatas

| Arquivo | Linha | Detalhe |
|---------|-------|---------|
| `/root/sistema_agendamento/app/main.py` | 34-63 | CSP_POLICY definida no SecurityHeadersMiddleware |
| `/root/sistema_agendamento/app/main.py` | 36 | `script-src 'self' 'unsafe-inline' 'unsafe-eval'` - **RISCO XSS** |
| `/root/sistema_agendamento/app/main.py` | 40 | `style-src 'self' 'unsafe-inline'` |
| `/root/sistema_agendamento/app/main.py` | 70-74 | X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy |
| `/root/sistema_agendamento/app/main.py` | 92-93 | HSTS: `max-age=31536000; includeSubDomains` (apenas producao) |
| `/root/sistema_agendamento/app/main.py` | 144-168 | CSRF configurado mas sem `@CsrfProtect` nos endpoints |
| `/root/sistema_agendamento/app/main.py` | 146 | CSRF secret fallback: `"csrf-secret-key-change-in-production"` |
| `/root/sistema_agendamento/app/main.py` | 170-190 | CORS: origens especificas (bom), allow_credentials=True |
| `/etc/nginx/sites-available/horariointeligente` | 21-23 | Headers duplicados com FastAPI (X-Frame-Options SAMEORIGIN vs DENY) |
| `/etc/nginx/sites-available/horariointeligente` | 6 | server_name sem `server_tokens off` |

### Comandos bash

```bash
# 1. Verificar CSP policy
grep -n "unsafe-inline\|unsafe-eval" /root/sistema_agendamento/app/main.py

# 2. Verificar se CSRF esta sendo usado em endpoints (nao apenas configurado)
grep -rn "CsrfProtect\|csrf_protect\|@csrf" /root/sistema_agendamento/app/api/ --include="*.py"

# 3. Verificar CORS origins
grep -A 15 "ALLOWED_ORIGINS" /root/sistema_agendamento/app/main.py

# 4. Verificar headers no Nginx
grep -n "add_header\|server_tokens\|ssl_protocols\|ssl_ciphers" /etc/nginx/sites-available/horariointeligente

# 5. Verificar HSTS no Nginx (deve estar no nginx tambem)
grep -n "Strict-Transport-Security" /etc/nginx/sites-available/horariointeligente

# 6. Testar headers reais (se o servico estiver rodando)
curl -sI https://horariointeligente.com.br 2>/dev/null | grep -iE "strict|x-frame|x-content|csp|server"

# 7. Verificar se server_tokens esta desabilitado globalmente
grep "server_tokens" /etc/nginx/nginx.conf

# 8. Verificar SSL config do Nginx
cat /etc/letsencrypt/options-ssl-nginx.conf 2>/dev/null
```

### Criterios de aprovacao/reprovacao

| Criterio | Aprovado | Reprovado |
|----------|----------|-----------|
| CSP sem `unsafe-inline` em script-src | Usa nonce ou hash | `unsafe-inline` presente |
| CSP sem `unsafe-eval` | Removido | `unsafe-eval` presente |
| CSRF aplicado em endpoints mutativos | `@CsrfProtect` em POST/PUT/DELETE | Apenas configurado, nao aplicado |
| HSTS no Nginx com includeSubDomains | Header presente | Ausente no nginx |
| `server_tokens off` no Nginx | Configurado | Nao configurado (expoe versao) |
| CORS sem `localhost` em producao | Apenas dominios de producao | `localhost` incluso |
| Headers consistentes Nginx/FastAPI | Mesmo valor de X-Frame-Options | `SAMEORIGIN` vs `DENY` conflitante |

### Acoes corretivas

```python
# 1. Remover unsafe-inline/unsafe-eval - usar nonces
# Em main.py, substituir:
# "script-src 'self' 'unsafe-inline' 'unsafe-eval' ..."
# Por:
# "script-src 'self' 'nonce-{RANDOM}' cdn.jsdelivr.net ..."

# 2. Aplicar CSRF em endpoints mutativos
from fastapi_csrf_protect import CsrfProtect
@router.post("/endpoint")
async def create_item(request: Request, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    ...
```

```nginx
# 3. Nginx - adicionar ao bloco server:
server_tokens off;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# 4. Remover headers duplicados do Nginx (deixar apenas no FastAPI)
# Remover linhas 21-23 do nginx config
```

---

## Secao 8 - Rate Limiting

### O que verificar
Verificar quais endpoints tem rate limiting e quais estao expostos. Endpoints de webhook, dados de pacientes e APIs de IA devem ter protecao.

### Arquivos e linhas exatas

**Endpoints COM rate limiting:**

| Arquivo | Linha | Endpoint | Limite |
|---------|-------|----------|--------|
| `/root/sistema_agendamento/app/api/auth.py` | 137 | `POST /login` | 5/minuto |
| `/root/sistema_agendamento/app/api/admin.py` | 163 | `POST /auth/login` | 5/minuto |
| `/root/sistema_agendamento/app/api/user_management.py` | 521 | Verificacao de email | 3/minuto |
| `/root/sistema_agendamento/app/api/parceiro_registro.py` | 65 | Registro de parceiro | 5/minuto |
| `/root/sistema_agendamento/app/api/usuarios_internos.py` | 406 | Usuarios internos | 5/minuto |
| `/root/sistema_agendamento/app/api/pre_cadastro.py` | 153 | Pre-cadastro | 5/minuto |
| `/root/sistema_agendamento/app/api/analytics.py` | 118 | Eventos analytics | 60/minuto |

**Endpoints SEM rate limiting (CRITICO):**

| Arquivo | Linha | Endpoint |
|---------|-------|----------|
| `/root/sistema_agendamento/app/api/webhooks.py` | 112 | `POST /whatsapp/{instance_name}` |
| `/root/sistema_agendamento/app/api/webhooks.py` | 1287 | `POST /whatsapp` |
| `/root/sistema_agendamento/app/api/webhooks.py` | 1295 | `GET /whatsapp/test` |
| `/root/sistema_agendamento/app/api/webhook_official.py` | 73 | `GET /webhook/whatsapp-official` |
| `/root/sistema_agendamento/app/api/webhook_official.py` | 103 | `POST /webhook/whatsapp-official` |
| Todos os endpoints de `/api/pacientes/` | - | CRUD de pacientes |
| Todos os endpoints de `/api/agendamentos/` | - | CRUD de agendamentos |
| Todos os endpoints de `/api/conversas/` | - | Listagem de conversas |

### Comandos bash

```bash
# 1. Listar TODOS os endpoints com rate limiting
grep -rn "@limiter.limit\|@app.state.limiter" /root/sistema_agendamento/app/ --include="*.py"

# 2. Listar TODOS os endpoints de API (para comparar)
grep -rn "@router\.\(get\|post\|put\|delete\|patch\)" /root/sistema_agendamento/app/api/ --include="*.py" | wc -l

# 3. Verificar se webhooks tem alguma protecao
grep -n "limiter\|rate" /root/sistema_agendamento/app/api/webhooks.py
grep -n "limiter\|rate" /root/sistema_agendamento/app/api/webhook_official.py

# 4. Verificar se ha rate limiting global no Nginx
grep -n "limit_req\|limit_conn" /etc/nginx/sites-available/horariointeligente
grep -n "limit_req\|limit_conn" /etc/nginx/nginx.conf

# 5. Verificar configuracao do slowapi
grep -n "Limiter\|default_limits" /root/sistema_agendamento/app/main.py
```

### Criterios de aprovacao/reprovacao

| Criterio | Aprovado | Reprovado |
|----------|----------|-----------|
| Webhooks com rate limiting | >= 100/minuto por IP | Sem limite |
| Endpoints de dados com rate limiting | >= 30/minuto por usuario | Sem limite |
| Rate limiting global no Nginx | `limit_req_zone` configurado | Nao configurado |
| Endpoints de IA com rate limiting | <= 10/minuto por usuario | Sem limite |

### Acoes corretivas

```python
# 1. Adicionar rate limiting aos webhooks
@router.post("/whatsapp/{instance_name}")
@limiter.limit("100/minute")
async def webhook_whatsapp(request: Request, ...):
    ...

# 2. Adicionar rate limiting global por IP no Nginx
# Em /etc/nginx/nginx.conf (bloco http):
limit_req_zone $binary_remote_addr zone=global:10m rate=50r/s;

# Em /etc/nginx/sites-available/horariointeligente (bloco location /):
limit_req zone=global burst=100 nodelay;
```

---

## Secao 9 - WebSocket

### O que verificar
O sistema usa WebSocket para notificacoes em tempo real. Verificar autenticacao, isolamento entre tenants, e se o token e passado de forma segura.

### Arquivos e linhas exatas

| Arquivo | Linha | Detalhe |
|---------|-------|---------|
| `/root/sistema_agendamento/app/api/websocket.py` | 19 | `SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")` - fallback inseguro |
| `/root/sistema_agendamento/app/api/websocket.py` | 23-31 | `get_user_from_token()` - valida JWT, retorna None se invalido |
| `/root/sistema_agendamento/app/api/websocket.py` | 34-37 | Endpoint `/ws/conversas` recebe token via `Query(None)` |
| `/root/sistema_agendamento/app/api/websocket.py` | 42 | `ws://dominio/ws/conversas?token=JWT_TOKEN` - token na URL |
| `/root/sistema_agendamento/app/services/websocket_manager.py` | - | Manager com conexoes por tenant |
| `/root/sistema_agendamento/static/conversas.html` | 849-873 | Cliente JS que conecta ao WebSocket |
| `/root/sistema_agendamento/static/calendario-unificado.html` | 3505-3590 | Cliente JS de calendario com WebSocket |

### Comandos bash

```bash
# 1. Verificar como o token e passado ao WebSocket
grep -n "token" /root/sistema_agendamento/app/api/websocket.py

# 2. Verificar se ha validacao de cliente_id no WebSocket
grep -n "cliente_id" /root/sistema_agendamento/app/api/websocket.py

# 3. Verificar isolamento no websocket_manager
grep -n "cliente_id\|tenant\|isolat" /root/sistema_agendamento/app/services/websocket_manager.py

# 4. Verificar se o token aparece nos logs de acesso do Nginx (exposicao)
grep "ws/conversas.*token=" /var/log/nginx/horariointeligente_access.log 2>/dev/null | head -5

# 5. Verificar broadcast - se filtra por tenant
grep -n "broadcast\|send_" /root/sistema_agendamento/app/services/websocket_manager.py

# 6. Verificar se ha rate limiting no WebSocket
grep -n "limit\|throttl" /root/sistema_agendamento/app/api/websocket.py
```

### Criterios de aprovacao/reprovacao

| Criterio | Aprovado | Reprovado |
|----------|----------|-----------|
| Token via header ou subprotocolo | `Sec-WebSocket-Protocol: token` | Token na query string (URL) |
| Isolamento por cliente_id no broadcast | Mensagens filtradas por tenant | Broadcast global |
| Sem fallback SECRET_KEY | Erro se chave nao definida | Fallback `"your-secret-key"` |
| Token nao aparece em logs | Nginx nao loga query params de WS | Token visivel em access.log |
| Rate limiting de conexoes | Max conexoes por IP/usuario | Sem limite |

### Acoes corretivas

```python
# 1. Remover fallback SECRET_KEY
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY nao configurada")

# 2. Usar subprotocolo para enviar token (em vez de query string)
@router.websocket("/ws/conversas")
async def websocket_conversas(websocket: WebSocket):
    # Token via subprotocol
    protocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
    token = protocols[0].strip() if protocols else None
    ...

# 3. No Nginx, nao logar query params de WebSocket
# location /ws/ {
#     access_log off;
#     ...
# }
```

---

## Secao 10 - Dependencias

### O que verificar
Verificar versoes de pacotes, CVEs conhecidas, pacotes sem pin de versao e bibliotecas desatualizadas.

### Arquivos e linhas exatas

| Arquivo | Linha | Pacote | Observacao |
|---------|-------|--------|------------|
| `/root/sistema_agendamento/requirements.txt` | 22 | `fastapi==0.116.2` | Verificar CVEs |
| `/root/sistema_agendamento/requirements.txt` | 7 | `anthropic==0.68.0` | SDK de IA |
| `/root/sistema_agendamento/requirements.txt` | 74 | `openai==1.54.0` | SDK de IA |
| `/root/sistema_agendamento/requirements.txt` | 75 | `cryptography` | **SEM PIN de versao** |
| `/root/sistema_agendamento/requirements.txt` | 79 | `pywebpush>=2.2.0` | **SEM PIN exato** (>=) |
| `/root/sistema_agendamento/requirements.txt` | 53 | `redis==6.4.0` | Verificar CVEs |
| `/root/sistema_agendamento/requirements.txt` | 59 | `SQLAlchemy==2.0.43` | Verificar CVEs |
| `/root/sistema_agendamento/requirements.txt` | 29 | `httpx==0.27.2` | Verificar CVEs |
| `/root/sistema_agendamento/requirements.txt` | 77 | `bcrypt==4.2.0` | Hash de senhas |
| `/root/sistema_agendamento/requirements.txt` | 76 | `slowapi==0.1.9` | Rate limiting |
| `/root/sistema_agendamento/requirements.txt` | 78 | `fastapi-csrf-protect==0.3.4` | CSRF |

### Comandos bash

```bash
# 1. Listar pacotes sem pin de versao exato
grep -vE "==|^#|^$" /root/sistema_agendamento/requirements.txt

# 2. Verificar CVEs com pip-audit (instalar se necessario)
cd /root/sistema_agendamento && source venv/bin/activate && pip-audit 2>/dev/null || echo "pip-audit nao instalado"

# 3. Verificar pacotes desatualizados
cd /root/sistema_agendamento && source venv/bin/activate && pip list --outdated 2>/dev/null | head -20

# 4. Verificar versao do Python
python3 --version

# 5. Verificar se ha pacotes vulneraveis conhecidos
cd /root/sistema_agendamento && source venv/bin/activate && pip install pip-audit 2>/dev/null && pip-audit --format=json 2>/dev/null | python3 -m json.tool | head -50

# 6. Verificar se PyJWT ou python-jose esta instalado (seguranca JWT)
cd /root/sistema_agendamento && source venv/bin/activate && pip show PyJWT python-jose 2>/dev/null

# 7. Verificar Dependabot ou similar configurado
ls /root/sistema_agendamento/.github/dependabot.yml 2>/dev/null || echo "Dependabot nao configurado"

# 8. Gerar SBOM (Software Bill of Materials)
cd /root/sistema_agendamento && source venv/bin/activate && pip freeze > /tmp/sbom_audit.txt && wc -l /tmp/sbom_audit.txt
```

### Criterios de aprovacao/reprovacao

| Criterio | Aprovado | Reprovado |
|----------|----------|-----------|
| Todos os pacotes com versao pinada | 100% com `==X.Y.Z` | Qualquer `>=`, sem versao, ou apenas nome |
| Zero CVEs criticas ou altas | pip-audit sem findings HIGH/CRITICAL | Qualquer CVE HIGH+ |
| PyJWT ou python-jose atualizado | Ultima versao estavel | Versao com CVE conhecida |
| Dependabot ou renovate configurado | `.github/dependabot.yml` existe | Nao configurado |
| Python >= 3.11 | 3.11+ | < 3.11 |

### Acoes corretivas

```bash
# 1. Pinar todas as dependencias
# Substituir:
# cryptography        -> cryptography==44.0.0
# pywebpush>=2.2.0    -> pywebpush==2.2.0

# 2. Instalar e rodar pip-audit regularmente
pip install pip-audit
pip-audit --fix  # Corrige automaticamente quando possivel

# 3. Configurar Dependabot
# Criar .github/dependabot.yml:
# version: 2
# updates:
#   - package-ecosystem: "pip"
#     directory: "/"
#     schedule:
#       interval: "weekly"

# 4. Atualizar pacotes com CVEs conhecidas
pip install --upgrade <pacote>
pip freeze > requirements.txt
```

---

## Checklist Consolidado

Resumo executivo de todos os itens verificados:

| # | Secao | Item Critico | Severidade | Status Esperado |
|---|-------|-------------|------------|-----------------|
| 1.1 | Segredos | `.env` permissao 644 | CRITICO | Mudar para 600 |
| 1.2 | Segredos | Telegram token hardcoded em Python | CRITICO | Mover para .env |
| 1.3 | Segredos | API key no systemd | CRITICO | Usar EnvironmentFile |
| 2.1 | JWT | 4 arquivos com fallback SECRET_KEY | CRITICO | Remover fallbacks |
| 2.2 | JWT | Token expira em 8h | ALTO | Reduzir para 30-60min |
| 2.3 | JWT | Sem refresh token | ALTO | Implementar |
| 3.1 | SQL | f-string em 8+ queries | ALTO | Usar bind parameters + whitelist |
| 4.1 | Tenant | TENANT_CACHE sem TTL | MEDIO | Adicionar TTL 5min |
| 4.2 | Tenant | Rotas JWT bypassam subdomain | MEDIO | Validar cliente_id no JWT |
| 5.1 | LGPD | CPF em texto plano | CRITICO | Criptografar em repouso |
| 5.2 | LGPD | Sem right-to-deletion | ALTO | Implementar endpoint |
| 5.3 | LGPD | Logs 83MB sem rotacao | MEDIO | Configurar logrotate |
| 5.4 | LGPD | webhook.log permissao 666 | ALTO | Mudar para 640 |
| 6.1 | Infra | Servico roda como root | CRITICO | Criar usuario dedicado |
| 6.2 | Infra | `--reload` em producao | MEDIO | Remover flag |
| 6.3 | Infra | Redis sem senha | MEDIO | Configurar requirepass |
| 7.1 | HTTP | CSP com unsafe-inline/unsafe-eval | ALTO | Usar nonces |
| 7.2 | HTTP | CSRF configurado mas nao aplicado | ALTO | Aplicar em POST/PUT/DELETE |
| 7.3 | HTTP | Nginx sem server_tokens off | BAIXO | Adicionar diretiva |
| 7.4 | HTTP | Nginx sem HSTS | MEDIO | Adicionar header |
| 8.1 | Rate | Webhooks sem rate limiting | ALTO | Adicionar 100/min |
| 8.2 | Rate | Endpoints de dados sem rate limiting | MEDIO | Adicionar 30/min |
| 9.1 | WS | Token JWT na URL (query string) | ALTO | Usar subprotocolo |
| 9.2 | WS | Fallback SECRET_KEY no websocket.py | CRITICO | Remover fallback |
| 10.1 | Deps | `cryptography` sem pin | MEDIO | Pinar versao |
| 10.2 | Deps | Sem Dependabot | BAIXO | Configurar |

---

## Como executar esta auditoria

1. **Leia este documento inteiro** para entender o escopo
2. **Execute os comandos bash** de cada secao na ordem (1 a 10)
3. **Compare os resultados** com os criterios de aprovacao/reprovacao
4. **Aplique as acoes corretivas** para itens reprovados, priorizando por severidade:
   - **CRITICO**: Corrigir imediatamente
   - **ALTO**: Corrigir em ate 1 semana
   - **MEDIO**: Corrigir em ate 1 mes
   - **BAIXO**: Corrigir no proximo ciclo de manutencao
5. **Re-execute os comandos** para confirmar que as correcoes foram aplicadas

---

## Secao 11 - Automacao de Auditorias

### Ciclos de auditoria

| Ciclo | Frequencia | Execucao | Escopo |
|-------|-----------|----------|--------|
| Semanal | Todo sabado 03:00 BRT | Automatica (cron) | Verificacoes automatizaveis: permissoes, tokens hardcoded, systemd, JWT fallbacks, infra, HTTP, rate limiting, CVEs, SSL, saude dos 6 servicos |
| Mensal | 1o sabado do mes 09:00 BRT | Lembrete automatico + execucao manual | Revisar logs, backups, acessos de usuarios, uso de disco/memoria, alertas da semana |
| Trimestral | Jan/Abr/Jul/Out (1o sabado) | Lembrete automatico + execucao manual | Auditoria completa secoes 1-10 do documento |
| Semestral | Jan/Jul (1o sabado) | Lembrete automatico + execucao manual | Rotacao de todas as chaves e segredos |

### Verificacoes automatizadas vs manuais

**Automatizadas (script semanal):**

| # | Verificacao | Secao | Criterio |
|---|------------|-------|----------|
| 1 | `.env` permissao 600 | 1 | `stat -c '%a'` == 600 |
| 2 | `.env.backup` permissao 600 ou inexistente | 1 | `stat -c '%a'` == 600 ou arquivo nao existe |
| 3 | Zero tokens hardcoded em `.py` | 1 | grep sem resultados (excluindo `os.getenv`) |
| 4 | Zero tokens hardcoded em `.sh` | 1 | grep sem resultados (excluindo leitura de .env) |
| 5 | Systemd sem chaves inline + usa EnvironmentFile | 1 | Zero `Environment=` com chaves sensivas |
| 6 | Zero fallbacks de SECRET_KEY | 2 | grep `getenv("SECRET_KEY",` sem resultados |
| 7 | Servico roda como usuario nao-root | 6 | `User=` != root |
| 8 | Sem `--reload` em producao | 6 | `ExecStart` sem flag `--reload` |
| 9 | Redis bind localhost | 6 | `bind 127.0.0.1` no redis.conf |
| 10 | Firewall ufw ativo | 6 | `ufw status` retorna active |
| 11 | Nginx `server_tokens off` | 7 | Diretiva presente no nginx.conf |
| 12 | HSTS configurado no Nginx | 7 | Header `Strict-Transport-Security` presente |
| 13 | Rate limiting (minimo 5 endpoints) | 8 | Contagem de `@limiter.limit` >= 5 |
| 14 | CVEs via pip-audit | 10 | Zero vulnerabilidades HIGH/CRITICAL |
| 15 | Dependencias com pin exato | 10 | Todas com `==X.Y.Z` |
| 16 | Certificado SSL (dias restantes) | SSL | PASS >30, WARN 8-30, FAIL <=7 |
| 17 | App HTTP 200 | Saude | curl localhost:8000/docs retorna 200 |
| 18 | SMTP login | Saude | smtplib.SMTP_SSL login sem envio |
| 19 | Telegram bot ativo | Saude | curl getMe retorna ok:true |
| 20 | ASAAS API key valida | Saude | GET /customers?limit=1 retorna 200 |
| 21 | PostgreSQL SELECT 1 | Saude | psycopg2 connect + SELECT 1 |
| 22 | Redis PING | Saude | redis.ping() retorna True |

**Manuais (mensal/trimestral/semestral):**

- Revisao de logs e backups (mensal)
- Revisao de acessos/usuarios inativos (mensal)
- Auditoria completa secoes 1-10 conforme documento (trimestral)
- Rotacao de chaves e segredos (semestral)

### Rotacao de chaves (semestral - Jan/Jul)

| Chave | Variavel no .env | Procedimento |
|-------|-----------------|-------------|
| JWT Secret | `SECRET_KEY` | Gerar nova chave: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| Encryption Key (LGPD) | `ENCRYPTION_KEY` | Gerar nova Fernet key + re-criptografar dados existentes |
| WhatsApp Token | `WHATSAPP_ACCESS_TOKEN` | Renovar no Meta Business Manager |
| WhatsApp Webhook | `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | Gerar novo token e atualizar no Meta |
| Anthropic API | `ANTHROPIC_API_KEY` | Rotacionar no console Anthropic |
| OpenAI API | `OPENAI_API_KEY` | Rotacionar no dashboard OpenAI |
| SMTP Password | `SMTP_PASSWORD` | Alterar no painel Hostinger |
| ASAAS API | `ASAAS_API_KEY` | Rotacionar no painel ASAAS |
| ASAAS Webhook | `ASAAS_WEBHOOK_TOKEN` | Gerar novo token e atualizar no ASAAS |
| VAPID Keys | `VAPID_PRIVATE_KEY` / `VAPID_PUBLIC_KEY` | Gerar novo par + atualizar service worker |

> **Importante:** Apos rotacao, atualizar `.env`, reiniciar servico (`systemctl restart horariointeligente`) e validar com o script semanal.

### Calendario 2026

Datas dos 1os sabados de cada mes e tipo de auditoria:

| Mes | 1o Sabado | Tipo |
|-----|----------|------|
| Janeiro | 03/01/2026 | Mensal + Trimestral + Semestral |
| Fevereiro | 07/02/2026 | Mensal |
| Marco | 07/03/2026 | Mensal |
| Abril | 04/04/2026 | Mensal + Trimestral |
| Maio | 02/05/2026 | Mensal |
| Junho | 06/06/2026 | Mensal |
| Julho | 04/07/2026 | Mensal + Trimestral + Semestral |
| Agosto | 01/08/2026 | Mensal |
| Setembro | 05/09/2026 | Mensal |
| Outubro | 03/10/2026 | Mensal + Trimestral |
| Novembro | 07/11/2026 | Mensal |
| Dezembro | 05/12/2026 | Mensal |

### Configuracao cron

```bash
# Auditoria semanal automatizada - sabados 03:00 BRT (06:00 UTC)
0 6 * * 6 /root/sistema_agendamento/scripts/auditoria-semanal.sh

# Lembrete calendario de auditorias - sabados 09:00 BRT (12:00 UTC)
0 12 * * 6 /root/sistema_agendamento/scripts/auditoria-calendario.sh

# Verificacao diaria do certificado SSL (existente)
0 9 * * * /root/sistema_agendamento/scripts/verificar-certificado.sh
```

### Scripts de automacao

| Script | Funcao | Execucao | Log |
|--------|--------|----------|-----|
| `scripts/auditoria-semanal.sh` | 22 verificacoes automaticas + saude dos 6 servicos + relatorio Telegram | Cron sabados 06:00 UTC | `/var/log/auditoria-semanal.log` |
| `scripts/auditoria-calendario.sh` | Lembretes de auditoria mensal/trimestral/semestral no 1o sabado | Cron sabados 12:00 UTC | `/var/log/auditoria-semanal.log` |
| `scripts/verificar-certificado.sh` | Verificacao diaria do certificado SSL | Cron diario 09:00 UTC | `/var/log/certificado-ssl.log` |
