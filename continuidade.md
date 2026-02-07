# Documento de Continuidade - Sistema de Agendamento

## Visão Geral
Sistema de agendamento médico multi-tenant (SaaS) chamado **Horário Inteligente**.

- **Stack**: FastAPI (Python) + PostgreSQL + HTML/JS (Tailwind CSS)
- **Serviço**: `horariointeligente.service` (systemd, user `horariointeligente`, 4 workers)
- **Porta**: 8000 (bind 127.0.0.1, atrás de Nginx)
- **Diretório**: `/root/sistema_agendamento`

---

## Estrutura Principal

```
/root/sistema_agendamento/
├── app/
│   ├── api/
│   │   ├── agendamentos.py       # CRUD de agendamentos, listagem de médicos
│   │   ├── conversas.py           # API REST conversas WhatsApp
│   │   ├── dashboard.py           # Métricas e dados financeiros
│   │   ├── auth.py                # Autenticação (login unificado, JWT)
│   │   ├── medico_config.py       # Configurações do médico
│   │   ├── admin.py               # Painel admin
│   │   ├── admin_clientes.py      # CRUD clientes + aprovação/rejeição
│   │   ├── admin_convites.py      # Gestão de convites (admin)
│   │   ├── cliente_registro.py    # API pública de registro via convite
│   │   ├── ativacao.py            # API pública de ativação de conta
│   │   ├── parceiro_auth.py       # Portal do parceiro (login, dashboard, convites)
│   │   ├── webhook_official.py    # Webhook WhatsApp API Oficial Meta (router + endpoints de teste)
│   │   └── websocket.py           # WebSocket para conversas em tempo real
│   ├── models/                    # SQLAlchemy models
│   ├── services/
│   │   ├── webhook/               # Pacote de processamento do webhook WhatsApp
│   │   │   ├── message_processor.py   # Pipeline principal (process_message)
│   │   │   ├── tenant_resolver.py     # Resolução multi-tenant por phone_number_id
│   │   │   ├── agendamento_ia.py      # Criação de agendamentos via IA
│   │   │   └── audio_handler.py       # Transcrição Whisper + resposta TTS
│   │   ├── anthropic_service.py   # IA conversacional (Claude)
│   │   ├── conversa_service.py    # Lógica de negócio de conversas
│   │   ├── lembrete_service.py    # Lembretes inteligentes (24h, 2h)
│   │   ├── button_handler_service.py # Respostas a botões de templates WhatsApp
│   │   ├── whatsapp_official_service.py # Envio via API Oficial Meta
│   │   ├── onboarding_service.py  # Helpers de onboarding (subdomain, senha, billing)
│   │   ├── crypto_service.py      # Criptografia PII (Fernet/LGPD)
│   │   └── websocket_manager.py   # Broadcast WebSocket por tenant
│   ├── middleware/
│   │   ├── tenant_middleware.py    # Multi-tenant por subdomain
│   │   └── billing_middleware.py   # Bloqueio de inadimplentes
│   ├── utils/
│   │   └── auth_middleware.py      # Controle de acesso médico/secretária
│   ├── database.py
│   └── main.py
├── static/
│   ├── calendario-unificado.html  # Tela principal de agendamentos
│   ├── conversas.html             # Painel de conversas WhatsApp
│   ├── dashboard.html             # Painel com métricas e financeiro
│   ├── configuracoes.html         # Configurações do médico
│   ├── perfil.html                # Perfil do usuário
│   ├── registro-cliente.html      # Formulário público de registro via convite
│   ├── ativar-conta.html          # Aceite de termos de uso
│   ├── admin/                     # Páginas do painel admin
│   ├── parceiro/                  # Páginas do portal do parceiro
│   └── js/components/
│       ├── top-nav.js             # HiTopNav — navegação desktop
│       ├── nav-init.js            # HiNavInit — inicializador unificado
│       └── bottom-nav.js          # HiBottomNav — navegação mobile
└── venv/
```

---

## Banco de Dados (PostgreSQL)

**Conexão**: `PGPASSWORD=<ver .env> psql -h localhost -U postgres -d agendamento_saas`

### Tabelas Principais
- `clientes` — Tenants do sistema (multi-tenant). Status: `pendente_aprovacao`, `pendente_aceite`, `ativo`, `rejeitado`, `aguardando_pagamento`, `suspenso`, `cancelado`
- `medicos` — Médicos e secretárias (`is_secretaria=true`). Campo `convenios_aceitos` (JSONB): `[{"nome": "Amil", "valor": 100.00, "codigo": "amil"}, ...]`
- `pacientes` — Cadastro de pacientes. CPF criptografado (Fernet/LGPD)
- `agendamentos` — `forma_pagamento` ('particular' ou 'convenio_0', etc.), `valor_consulta`, `status` (agendado/confirmado/realizado/cancelado/faltou/remarcado), `data_hora` (TIMESTAMP WITH TIME ZONE em BRT)
- `conversas` — Conversas WhatsApp por tenant. Status: `ia_ativa`, `humano_assumiu`, `encerrada`
- `mensagens` — Mensagens de cada conversa. Remetente: `PACIENTE`, `IA`, `ATENDENTE`, `SISTEMA`
- `lembretes` — Lembretes de agendamentos (UNIQUE constraint em `agendamento_id, tipo`)
- `convites_clientes` — Convites de cadastro (admin ou parceiro)
- `historico_aceites` — Registro de aceites de termos (LGPD)

---

## Observações Técnicas

### Fuso Horário
- **Banco de dados**: `America/Sao_Paulo` (BRT, UTC-3)
- **Código Python**: Usar `now_brazil()` de `app.utils.timezone_helper` (nunca `datetime.now()` ou `datetime.utcnow()`)
- **Exibição**: `converter_para_brasil(dt)` em `app/api/conversas.py`

### Forma de Pagamento
- `'particular'` → Consulta particular (valor de `medico.valor_consulta_particular`)
- `'convenio_0'`, `'convenio_1'`, etc. → Índice no array `convenios_aceitos` do médico
- Para obter o nome: `medicos.convenios_aceitos[índice].nome`

### Controle de Acesso (Médico vs Secretária)
- `app/utils/auth_middleware.py` → `get_medico_filter_dependency()`: retorna `None` (secretária, vê tudo) ou `medico_id` (médico, vê só seus dados)
- Usado em: `/agendamentos/calendario`, `/api/conversas`
- Ambos os tipos vêm da tabela `medicos` (secretária tem `is_secretaria=true`)

### Navegação Unificada
- **Desktop (>= 1024px)**: `HiTopNav` — barra superior sticky, 56px
- **Mobile (< 1024px)**: `HiBottomNav` — barra inferior fixa com FAB central
- **Inicialização**: `HiNavInit.init({ activeId: 'pagina' })` — configura ambas automaticamente
- **Perfis**: Itens de menu variam por perfil (médico vs secretária)

### Onboarding / Ativação
- **Token ativação**: `secrets.token_urlsafe(64)`, expiração 7 dias
- **Versões termos**: `VERSAO_TERMOS = "1.1"`, `VERSAO_PRIVACIDADE = "1.1"` (em `app/api/ativacao.py`)
- **Convites**: `secrets.token_urlsafe(48)`, expiração 30 dias

### Scheduler (Lembretes)
- Apenas 1 worker executa o scheduler (file lock em `/tmp/horariointeligente_scheduler.lock`)
- Job único: `lembretes_inteligentes` (API Oficial Meta) a cada 10 minutos
- Locking por registro: `.with_for_update(skip_locked=True)`

---

## Usuários de Teste

### Cliente Real (Testes)
| Email | Senha | Tipo | ID |
|-------|-------|------|-----|
| drjoao@teste.com | teste123 | Médico | 31 |
| ana@teste.com | teste123 | Secretária | 32 |

### Cliente Demo (Demonstração)
| Email | Senha | Tipo | ID |
|-------|-------|------|-----|
| dr.carlos@demo.horariointeligente.com.br | demo123 | Médico | 18 |
| dra.ana@demo.horariointeligente.com.br | demo123 | Médico | 19 |

---

## Comandos Úteis

```bash
# Reiniciar serviço
systemctl restart horariointeligente.service

# Ver status
systemctl status horariointeligente.service

# Logs em tempo real
journalctl -u horariointeligente.service -f

# Ativar venv
source /root/sistema_agendamento/venv/bin/activate
```

---

## Histórico Consolidado de Correções (27-29/01/2026)

Itens #1 a #41 — todos resolvidos. Resumo por área:

### IA Conversacional (anthropic_service.py)
| # | Correção |
|---|----------|
| 12 | IA consulta horários reais do médico (não mais hardcoded 8h-17h) |
| 13 | Verificação de conflito de horário antes de agendar |
| 17 | ID real do médico no prompt (`[ID: X]`) |
| 18 | Médico único: pula pergunta de especialidade |
| 20 | Detecção de "hoje", "amanhã" com timezone correto |
| 25 | 13h reconhecido como disponível (não confundir com almoço) |
| 26 | Lembrete adaptativo (24h vs 2h) na confirmação |
| 27 | "INDISPONÍVEL" ao invés de "OCUPADO (JÁ TEM PACIENTE)" |
| 30 | Filtrar horários passados para hoje (margem de 30min) |
| 32 | Motivo da consulta no fluxo de agendamento |
| 33 | Lembrete de trazer exames na confirmação |
| 34 | Detecção paciente novo vs retorno |
| 37 | Não mencionar lembrete 24h ao confirmar presença |
| 38 | "Médico não atende nesse dia" vs "agenda lotada" |
| 41 | Parser de datas curtas (DD/MM, D/M) |

### Calendário e Dashboard
| # | Correção |
|---|----------|
| 1 | `forma_pagamento` salvo no INSERT de agendamentos |
| 2 | Modal de detalhes exibe forma de pagamento |
| 3 | Endpoint `/api/dashboard/financeiro` criado |
| 5-6 | Gráficos financeiros renderizando com previsto + realizado |
| 7 | Nome dos convênios nos gráficos (extraído do JSON do médico) |
| 8 | Horários populares com fuso BRT (não UTC) |
| 11 | Indicação visual de horários indisponíveis no calendário |
| 21 | Dashboard exclui remarcados/cancelados/faltou |
| 28-29 | Convênio salva `forma_pagamento` corretamente via IA |
| 39 | Modal de cancelamento com motivos + notificação WhatsApp |
| 40 | Horários desaparecem ao trocar data no reagendamento |

### Conversas WhatsApp e WebSocket
| # | Correção |
|---|----------|
| 14 | Cache Redis limpo ao deletar conversa |
| 16 | Lista de conversas atualiza em tempo real (WebSocket) |
| 31 | Chat do painel com horário BRT (não UTC) |

### Outros
| # | Correção |
|---|----------|
| 4 | `/api/medicos` retorna `convenios_aceitos` |
| 10 | Senhas de teste resetadas |
| 15 | Convênios salvam automaticamente (UX) |
| 19 | Timezone do PostgreSQL alterado para BRT |
| 22 | Valor consulta particular do médico (não hardcoded R$300) |
| 23-24 | Fluxo agendado→confirmado + botão "Estou a caminho" |
| 36 | Navegação unificada (HiTopNav + HiBottomNav, -403 linhas) |

---

## Sistema de Onboarding (28/01/2026)

### Fluxo de Ativação de Conta (#35)
```
Admin/Parceiro cadastra → status=pendente_aceite → Email com link
→ Cliente aceita termos → status=ativo
```
- **APIs**: `/api/ativacao/{token}` (GET dados, POST aceite)
- **Portal Parceiro**: `/api/parceiro/` (login, dashboard, CRUD clientes, convites)
- **Página**: `static/ativar-conta.html` (6 estados)
- Registra IP, user-agent, versões de termos em `historico_aceites`

---

## Auditoria de Segurança (30/01/2026)

### Correções Críticas (#48)
- **Permissões**: `.env` chmod 600, logs chmod 640
- **Systemd**: `User=horariointeligente` (não root), bind 127.0.0.1, 4 workers, `EnvironmentFile=.env`
- **SECRET_KEY**: removidos 5 fallbacks hardcoded → `os.getenv("SECRET_KEY")` com `RuntimeError`
- **Telegram tokens**: hardcoded → `os.getenv()`
- **Firewall**: UFW ativo (22, 80, 443/tcp)

### Correções Altas (#49)
- **JWT**: expiração 60min (era 480), refresh token 8h, endpoint `POST /auth/refresh`
- **Rate limiting**: 120/min global, 200/min webhook
- **CORS**: localhost condicional (`ENVIRONMENT != "production"`)
- **Nginx**: `server_tokens off`, HSTS, TLS 1.2+
- **LGPD**: CPF criptografado com Fernet (`EncryptedString` TypeDecorator), 282 registros migrados
- **Logrotate**: rotação diária, 30 dias retenção
- **CVEs**: aiohttp, pyasn1, python-multipart, starlette, urllib3 atualizados

### Rotação de Chaves (#50)
Chaves locais rotacionadas: SECRET_KEY, DATABASE_URL, WHATSAPP_WEBHOOK_VERIFY_TOKEN, ASAAS_WEBHOOK_TOKEN, VAPID keys, ENCRYPTION_KEY.

### Checklist de Chaves Externas
Após rotação, as integrações externas precisam de novos tokens no `.env`:

| Passo | Serviço | Variável no .env | Portal |
|-------|---------|------------------|--------|
| 1 | WhatsApp Meta | `WHATSAPP_ACCESS_TOKEN` | business.facebook.com → WhatsApp → API Setup |
| 2 | Anthropic (Claude) | `ANTHROPIC_API_KEY` | console.anthropic.com/settings/keys |
| 3 | OpenAI (Whisper+TTS) | `OPENAI_API_KEY` | platform.openai.com/api-keys |
| 4 | Email SMTP | `SMTP_PASSWORD` | hpanel.hostinger.com |
| 5 | Telegram Bot | `TELEGRAM_BOT_TOKEN` | @BotFather no Telegram |
| 6 | Asaas (pagamentos) | `ASAAS_API_KEY` | asaas.com/config/api |

Após inserir todas as chaves: `systemctl restart horariointeligente && chmod 600 .env && chown horariointeligente:horariointeligente .env`

---

## Correções — Sessão 31/01/2026

### 51. JWT `sub` claim — InvalidSubjectError
- PyJWT exige `sub` como string (RFC 7519). `create_unified_token()` enviava integer.
- Fix: `str(user_data["id"])` no token + `int()` nos 6 pontos que leem o `sub`
- Arquivos: `auth.py`, `admin.py`, `parceiro_auth.py`, `financeiro.py`

### 52-53. Login admin dedicado + redirects
- Criada `/static/admin/login.html` standalone (tema admin hardcoded)
- 23 referências em 19 arquivos atualizadas para caminhos corretos

### 54. Cache HTML — Nginx e Service Worker
- Nginx: `expires -1; Cache-Control "no-cache, must-revalidate"` para HTML
- Service Worker: versão 1.1.0 → 1.2.0

### 55-56. Rota raiz admin + reset senha parceiro
- Subdomínio `admin.*` → `/static/admin/login.html`
- Parceiro José Maria (id=4): senha `parceiro123`

---

## Correções — Sessão 01/02/2026

### 57. Lembretes quadruplicados (4 workers × 4 schedulers)
- **Causa**: Cada worker Uvicorn iniciava seu próprio `ReminderScheduler`
- **Correções**:
  - File lock (`fcntl.flock`) em `main.py` — apenas 1 worker roda o scheduler
  - Removido job legado `process_reminders` (Evolution API)
  - Removida execução imediata no startup (evita duplicação em restart)
  - `.with_for_update(skip_locked=True)` no processamento de lembretes
  - UNIQUE constraint `(agendamento_id, tipo)` na tabela `lembretes`

### 58. Lembretes não apareciam no painel de conversas
- **Causa**: `RemetenteMensagem.SISTEMA` não existia no enum Python nem no PostgreSQL
- **Fix**: Adicionado `SISTEMA = "sistema"` ao enum Python + `ALTER TYPE remetentemensagem ADD VALUE 'SISTEMA'`
- Frontend: label "Sistema" + estilo roxo/lilás

### 59. Nome duplicado "Dr(a). Dr. João"
- Verificação de prefixo antes de adicionar "Dr(a)." em `lembrete_service.py`

### 60. Template lembrete_24h — texto redundante
- Body diz "Responda OK..." mas template já tem botões interativos
- **Status**: Pendente — requer edição manual no Meta Business Manager

---

## Cadastro Self-Service via Convite — Sessão 02/02/2026

### 61. Feature completa: Cadastro Self-Service de Clientes

#### Fluxo
```
Admin gera convite → Prospect preenche dados → status=pendente_aprovacao
→ Admin configura billing e aprova → status=pendente_aceite → Email ativação
→ Cliente aceita termos → status=ativo
```

#### Componentes criados
| Arquivo | Descrição |
|---------|-----------|
| `app/models/convite_cliente.py` | Model ConviteCliente |
| `app/services/onboarding_service.py` | Helpers extraídos (subdomain, senha, billing) |
| `app/api/cliente_registro.py` | API pública `/api/registro-cliente/{token}` (GET valida, POST registra) |
| `app/api/admin_convites.py` | API admin `/api/admin/convites` (POST gera, GET lista, DELETE revoga) |
| `static/registro-cliente.html` | Formulário público para prospects |
| `static/admin/convites.html` | Gestão de convites (admin) |
| `static/admin/clientes-aprovar.html` | Página de aprovação com config de billing |

#### Endpoints de aprovação/rejeição
- `POST /api/admin/clientes/{id}/aprovar` — cria assinatura, gera senhas, configura médicos, envia email de ativação
- `POST /api/admin/clientes/{id}/rejeitar` — atualiza status

#### Migração
- Tabela `convites_clientes` criada
- Colunas em `clientes`: `tipo_consultorio`, `qtd_medicos_adicionais`, `necessita_secretaria`, `convite_id`
- `plano` alterado para aceitar NULL (definido na aprovação)

---

## Correções — Sessão 03/02/2026

### 62. Botão "Não vou conseguir ir" não oferecia remarcar
- **Causa**: timezone incorreto (`datetime.now()` sem tz), busca muito restritiva, cancelamento automático sem perguntar
- **Fix**: `now_brazil()`, margem de 2h na busca, handler reescrito para perguntar "remarcar ou cancelar?"
- **Arquivo**: `app/services/button_handler_service.py`

### 63. Orientações padrão em confirmações (endereço, documento, exames)
- Toda confirmação agora inclui: endereço da clínica, "traga documento com foto" (+ carteirinha se convênio), "traga exames recentes"
- Aplicado em: confirmação da IA, resposta ao lembrete 24h, resposta ao lembrete 2h
- **Arquivos**: `anthropic_service.py`, `button_handler_service.py`, `lembrete_service.py`

### 64. Máscara de telefone em convites + texto do email
- Máscara `(XX) XXXXX-XXXX` no modal de convites (`admin/convites.html`)
- Texto do email: "sistema de agendamento automatizado mais humanizado"

### 65. Erro "plano NOT NULL" ao registrar via convite
- `ALTER TABLE clientes ALTER COLUMN plano DROP NOT NULL` — plano definido na aprovação

### 66. Tela de sucesso do registro via convite
- Removido botão "Acessar Painel", título "Cadastro Enviado!", passos explicando análise→aprovação→ativação

### 67. Correção do cálculo de comissões de parceiros
- Comissão mensal: percentual sobre (plano base + extras) — **sem** linha dedicada (R$40)
- Comissão de ativação: percentual sobre taxa de ativação (única vez)
- Se ativação cortesia: sem comissão de ativação
- `mes_referencia=0` (ativação), `mes_referencia=1+` (mensalidades)

### 68. Sistema de convites para parceiros comerciais
- Parceiro gera links de convite no seu dashboard
- Endpoints: `POST/GET/DELETE /api/parceiro/convites`
- Email personalizado com nome do parceiro
- Página de registro mostra "Convite de: [Nome do Parceiro]"
- Vínculo cliente-parceiro criado automaticamente

---

## Correções — Sessão 04/02/2026

### 69. Filtro de conversas WhatsApp por vínculo médico-paciente
- **Problema**: No painel de conversas, todos os médicos de um cliente multi-profissional viam todas as conversas. Cada médico deve ver apenas conversas de pacientes com agendamento com ele. Secretárias continuam vendo tudo.
- **Cadeia**: `conversa.paciente_telefone → pacientes.telefone → agendamentos.paciente_id + medico_id`
- **Implementação**:
  - `app/services/conversa_service.py`: parâmetro `medico_id` em `listar_conversas()`. Subquery filtra telefones de pacientes com agendamento com o médico
  - `app/api/conversas.py`: dependency `get_medico_filter_dependency` no endpoint `GET /api/conversas`
- **Comportamento**:
  - Secretária → `medico_filter=None` → vê todas as conversas
  - Médico → `medico_filter=ID` → vê apenas pacientes com vínculo via agendamento
  - Paciente de dois médicos → ambos veem
  - Número novo sem paciente/agendamento → só secretária vê

---

## Correções — Sessão 06/02/2026

### 70. Vazamento multi-tenant: dados do demo exibidos em outro cliente
- **Problema**: Conversas do WhatsApp do cliente "Médicos Associados" (id=19) exibiam dados da "Clínica Demonstração" (id=3) — especialidades, nomes de médicos e nome da clínica errados
- **Causa raiz**: Função `get_cliente_id_from_phone_number_id()` em `webhook_official.py` tinha fallback silencioso para `DEFAULT_CLIENTE_ID=3` (demo) quando não encontrava o `phone_number_id`. Agravado por `clientes.ativo=false` no cliente 19 (inconsistência com `status='ativo'`)
- **Correções**:
  - Removido fallback para `DEFAULT_CLIENTE_ID=3` — função agora retorna `None` e a mensagem é ignorada com log de erro
  - Adicionada busca em duas camadas: tabela `configuracoes` + tabela `clientes`
  - Filtro de ativo usa `OR(ativo=true, status='ativo')` para resiliência contra inconsistências
  - `process_message()` rejeita mensagens quando `cliente_id is None`
  - Sincronizado `clientes.whatsapp_phone_number_id` para cliente 19
  - Corrigido `clientes.ativo = true` para cliente 19
  - Encerrada conversa 30 (vinculada ao tenant errado) e limpo cache Redis correspondente
  - Adicionadas UNIQUE constraints parciais em `whatsapp_phone_number_id` nas tabelas `configuracoes` e `clientes`
- **Arquivos**: `app/api/webhook_official.py`
- **Banco**: `clientes` (dados + constraint), `configuracoes` (constraint), `conversas` (conversa 30 encerrada), Redis (cache limpo)

---

## Refatoração — Sessão 07/02/2026

### 71. Refatoração do webhook_official.py
- **Problema**: Arquivo monolítico de 1.246 linhas com 10+ responsabilidades, difícil de manter e testar
- **Solução**: Extraído para pacote `app/services/webhook/` com 4 módulos independentes:
  - `tenant_resolver.py` (50 linhas) — `get_cliente_id_from_phone_number_id()`
  - `agendamento_ia.py` (239 linhas) — `criar_agendamento_from_ia()`
  - `audio_handler.py` (133 linhas) — `transcribe_incoming_audio()`, `handle_audio_response()`
  - `message_processor.py` (459 linhas) — `process_message()`, `converter_para_brasil()`
- **webhook_official.py** reduzido a 415 linhas (router + 10 endpoints de teste)
- **Sem alteração de comportamento**: mesma pipeline, mesmo multi-tenant, mesmos endpoints, mesmas respostas
- **Grafo de dependências**: DAG limpo, sem ciclos. Os 3 módulos-folha não importam uns dos outros

---

## Pendências Abertas

- [ ] Template `lembrete_24h` — remover texto "Responda OK..." redundante com botões (editar no Meta Business Manager)
- [ ] Testar fluxo completo: prospect preenche formulário → admin aprova → cliente aceita termos
- [ ] Testar envio de email ao gerar convite (checkbox "enviar por email")
- [ ] Testar rejeição de prospect

---

*Última atualização: 07/02/2026 — Refatoração do webhook_official.py em pacote modular*
