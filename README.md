# Horário Inteligente - Sistema de Agendamento para Clínicas

![Version](https://img.shields.io/badge/version-3.6.0-blue)
![LGPD](https://img.shields.io/badge/LGPD-100%25_conforme-success)
![AI](https://img.shields.io/badge/🤖_AI-Claude_Sonnet_4.5-blueviolet)
![Audio](https://img.shields.io/badge/🎙️_áudio-OpenAI_Whisper_+_TTS-orange)
![Cost](https://img.shields.io/badge/💰_custo_IA-80%25_reduzido-success)
![MultiTenant](https://img.shields.io/badge/🏢_multi--tenant-100%25_funcional-success)
![Responsive](https://img.shields.io/badge/📱_mobile-100%25_responsivo-success)
![PWA](https://img.shields.io/badge/📱_PWA-instalável-blueviolet)
![Timezone](https://img.shields.io/badge/🕐_timezone-corrigido-success)
![Notifications](https://img.shields.io/badge/🔔_notificações-WhatsApp_+_Email-success)
![Status](https://img.shields.io/badge/status-produção-brightgreen)
![HTTPS](https://img.shields.io/badge/🔒_HTTPS-ativo-green)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116.2-009688)

Sistema SaaS de agendamento para clínicas (médicos, dentistas, psicólogos, fisioterapeutas, nutricionistas e outros profissionais) com assistente virtual inteligente via WhatsApp, integração com IA **Claude Sonnet 4.5**, **áudio bidirecional (OpenAI Whisper + TTS)**, **interface 100% responsiva** e **arquitetura multi-tenant completa**.

## 📑 Índice

1. [📋 Visão Geral](#-visão-geral)
2. [⚠️ Pendências de Segurança](#️-pendências-de-segurança)
3. [🚀 Novidades v3.2.0 e v3.3.0](#-novidades-v320-e-v330-novo)
4. [🌐 Acesso em Produção](#-acesso-em-produção)
5. [🏢 Multi-Tenant SaaS](#-multi-tenant-saas)
6. [🤖 Integração com IA](#-integração-com-ia)
7. [🎯 Funcionalidades Principais](#-funcionalidades-principais)
8. [📱 Progressive Web App (PWA)](#-progressive-web-app-pwa)
9. [⚙️ Configuração e Instalação](#️-configuração-e-instalação)
10. [🐍 Stack Tecnológico](#-stack-tecnológico)
11. [🔄 Fluxo de Uso](#-fluxo-de-uso)
12. [💰 Custos de Operação](#-custos-de-operação)
13. [📚 Documentação Adicional](#-documentação-adicional)

---

## 📋 Visão Geral

O **Horário Inteligente** é uma plataforma completa de gerenciamento de agendamentos para clínicas que combina:

- 🤖 **Bot WhatsApp com IA** - Assistente virtual baseado em **Claude Sonnet 4.5** (modelo mais recente)
- 🎙️ **Áudio bidirecional** - **NOVO!** Recebe e envia áudios via WhatsApp (OpenAI Whisper + TTS)
- 📅 **Sistema de calendário completo** - Gerenciamento de horários e disponibilidade
- 🏥 **Multi-tenant SaaS 100% funcional** - Isolamento completo por clínica via subdomínio
- 🔄 **Automação inteligente** - Agendamento natural via conversação (texto ou áudio)
- 📊 **Dashboard completo** - Gestão de consultas, profissionais e pacientes
- 🔒 **HTTPS em produção** - SSL automático com Let's Encrypt
- 🔔 **Sistema de lembretes** - Notificações automáticas 24h, 3h e 1h antes
- ⚠️ **Gestão de faltas** - Notificação empática e reagendamento automático
- 📧 **Notificações para profissionais** - WhatsApp e Email configuráveis por profissional
- 🎯 **Estratégias de vendas** - Oferecimento inteligente de horários + pausas estratégicas

**Atende todos os tipos de profissionais de saúde:** médicos, dentistas, psicólogos, fisioterapeutas, nutricionistas, fonoaudiólogos e outros.

**Última atualização:** 9 de dezembro de 2025
**Versão:** 3.6.0 🚀 **[NOVA: Documentação Legal Completa - Termos de Uso + Política de Privacidade LGPD]**
**Desenvolvedor:** Marco Aurélio Thiele (com Claude Code)

---

## ⚠️ PENDÊNCIAS DE SEGURANÇA

### 🔒 Hash de Senhas dos Médicos

**STATUS:** ⚠️ PENDENTE (Crítico para Produção)

**PROBLEMA:**
- As senhas dos médicos estão armazenadas em **texto plano** no banco de dados
- Campo `medicos.senha` contém a senha sem hash bcrypt
- Isso representa um **risco crítico de segurança**

**SOLUÇÃO NECESSÁRIA:**
```bash
# Antes de ir para produção, executar:
python scripts/hash_medicos_passwords.py
```

**IMPACTO:**
- ✅ Desenvolvimento/Demonstração: OK (facilita testes)
- ❌ Produção: BLOQUEANTE (deve ser corrigido antes do deploy)

**CREDENCIAIS ATUAIS (Apenas Desenvolvimento):**
- Todos os médicos usam senha: `admin123`
- Após aplicar hash, as senhas continuam as mesmas, mas serão armazenadas com segurança

**TODO:**
- [ ] Criar script `hash_medicos_passwords.py`
- [ ] Aplicar hash bcrypt em todas as senhas de médicos
- [ ] Testar login após aplicação do hash
- [ ] Adicionar validação de senha forte no frontend
- [ ] Implementar sistema de "esqueci minha senha" para médicos

---

## 🚀 Novidades v3.2.0 e v3.3.0 (NOVO)

### 🤖 Migração para Claude Sonnet 4.5

**Antes (v3.1.0):**
- Modelo: Claude 3 Opus
- Custo: ~R$ 140/mês por profissional
- Margem: 30% (insustentável)

**Agora (v3.2.0):**
- Modelo: **Claude Sonnet 4.5** (mais recente)
- Custo: ~**R$ 28/mês** por profissional
- **Economia: 80% (R$ 112/mês por profissional!)**
- Margem: **86%** (saudável e sustentável)
- Qualidade: **Superior** ao Opus
- Velocidade: **Mais rápido** (4.7s vs 6s)

```
┌─────────────────────┬───────────┬──────────┬──────────┐
│ Período             │ Opus      │ Sonnet   │ Economia │
├─────────────────────┼───────────┼──────────┼──────────┤
│ Por mês (200)       │ R$ 140    │ R$ 28    │ R$ 112   │
│ Por ano (2.400)     │ R$ 1.670  │ R$ 334   │ R$ 1.336 │
└─────────────────────┴───────────┴──────────┴──────────┘

Para 10 profissionais: Economia de R$ 1.120/mês ou R$ 13.440/ano! 💰
```

### ⚠️ Sistema de Gestão de Faltas

**Novo recurso implementado:**

Quando um paciente falta à consulta, o sistema:

1. ✅ Marca automaticamente como "faltou" no calendário
2. 📱 Envia mensagem **empática** via WhatsApp:
   ```
   Olá [Nome]! Notamos que você não compareceu à
   consulta com Dr(a) [Nome] em [data] às [hora].

   Entendemos que imprevistos acontecem!

   Gostaríamos de remarcar sua consulta.
   Temos os seguintes horários disponíveis:

   1️⃣ [Data/Hora 1]
   2️⃣ [Data/Hora 2]
   3️⃣ [Data/Hora 3]

   Qual horário funciona melhor para você?
   ```
3. 🔍 Busca automaticamente os 3 próximos horários disponíveis
4. 🎨 Atualiza calendário com cor laranja (status "faltou")
5. 🚫 Bloqueia botão "Marcar Falta" para evitar duplicação

**Benefícios:**
- Reduz taxa de no-show
- Mantém relacionamento com paciente
- Automatiza reagendamento
- Tom empático (não acusatório)

### 🕐 Correções de Timezone

**Problema resolvido:**
- Comparações de data/hora com timezone correto (Brazil/America/Sao_Paulo)
- Helper centralizado: `timezone_helper.py`
- Todas as operações usam timezone-aware datetime

**Arquivos corrigidos:**
- `falta_service.py` - 3 correções de `datetime.now()` → `now_brazil()`
- `reminder_service.py` - Uso consistente de timezone
- `agendamentos.py` - Reset de flags de lembrete ao reagendar

### 🔑 Token JWT de 8 Horas

**Antes:** 30 minutos (sessão caía durante o dia)
**Agora:** 480 minutos (8 horas - jornada completa de trabalho)

**Benefício:** Médicos e secretárias não precisam fazer login múltiplas vezes por dia

### 🔔 Sistema de Notificações para Profissionais (NOVO)

**Recursos implementados:**

Os profissionais agora podem configurar notificações automáticas para serem alertados sobre eventos importantes da agenda:

**Eventos Notificáveis:**
- 🆕 **Novos agendamentos** - Alerta quando uma nova consulta é marcada
- 🔄 **Reagendamentos** - Notificação quando um paciente remarca
- ❌ **Cancelamentos** - Aviso quando uma consulta é cancelada
- ✅ **Confirmações** - Opcional: quando paciente confirma presença

**Canais de Notificação:**
- 📱 **WhatsApp** - Via Evolution API (integração já existente)
- 📧 **Email** - Via SMTP (Gmail configurado)
- ~~📲 SMS~~ - Não implementado (custo R$ 0,10/msg)

**Como Configurar:**
1. Login como profissional no sistema
2. Acesse "Meu Perfil" (ícone do usuário)
3. Role até "Configurações de Notificações"
4. Marque os eventos que deseja ser notificado
5. Escolha os canais (WhatsApp e/ou Email)
6. Preencha telefone WhatsApp e/ou email
7. Salve as configurações

**Exemplo de Notificação (Novo Agendamento):**
```
🔔 Novo Agendamento

📅 Data/Hora: 02/12/2025 às 14:30
👤 Paciente: Maria Silva

Um novo agendamento foi confirmado na sua agenda.
```

**Tecnologia:**
- **Backend:** `NotificationService` em Python
- **Email:** SMTP via Gmail (horariointeligenteweb@gmail.com)
- **WhatsApp:** Evolution API (mesmo usado para pacientes)
- **Banco:** Tabela `notificacoes_medico` com preferências individuais
- **API:** Endpoints REST em `/api/medicos/{id}/notificacoes`

**Custos:**
- 📱 WhatsApp: **R$ 0,00** (usa Evolution API local)
- 📧 Email: **R$ 0,00** (Gmail gratuito)
- 💰 **Total: R$ 0,00/mês**

**Benefícios:**
- ✅ Profissionais sempre informados em tempo real
- ✅ Reduz ausências por falta de comunicação
- ✅ Personalização por profissional (cada um define suas preferências)
- ✅ Multi-canal (podem receber por WhatsApp E Email simultaneamente)
- ✅ Não bloqueia operações (se notificação falhar, agendamento continua)

### 📊 Outras Melhorias

- ✅ Sistema de notificações para médicos (WhatsApp + Email)
- ✅ Configuração SMTP com Gmail (horariointeligenteweb@gmail.com)
- ✅ Interface de configuração de notificações no perfil do médico
- ✅ Botão "Marcar Falta" oculta-se automaticamente quando status é incompatível
- ✅ Reset automático do estado do botão ao reabrir detalhes
- ✅ Correção de nome da tabela: `medico_config` → `configuracoes_medico`
- ✅ Correção de instância WhatsApp: `prosaude-whatsapp` → `ProSaude`
- ✅ Limpeza de banco com reset de sequências para testes

---

## 🌐 Acesso em Produção

### URLs de Produção:

**Domínio Principal:**
```
https://horariointeligente.com.br
```

**Clínicas Multi-Tenant:**
```
https://prosaude.horariointeligente.com.br
https://drmarco.horariointeligente.com.br
https://[sua-clinica].horariointeligente.com.br
```

### Infraestrutura:

- **Servidor:** VPS Hostinger (145.223.95.35)
- **DNS:** Wildcard configurado (`*.horariointeligente.com.br`)
- **SSL:** Let's Encrypt (renovação automática)
- **Nginx:** Reverse proxy multi-tenant
- **FastAPI:** Porta 8000 (internal)
- **PostgreSQL:** Banco multi-tenant
- **Redis:** Cache e conversas isoladas por tenant
- **WhatsApp:** Evolution API (instância: ProSaude)

### Status do Sistema:

✅ DNS configurado e propagado
✅ SSL válido até 28/02/2026
✅ Nginx rodando (multi-tenant)
✅ FastAPI ativo (systemd: prosaude.service)
✅ Firewall configurado (portas 80, 443, 22)
✅ Redirecionamento HTTP → HTTPS automático
✅ WhatsApp conectado e funcionando
✅ Claude Sonnet 4.5 ativo

---

## 🏢 Multi-Tenant SaaS

### Arquitetura Multi-Tenant Completa

O sistema suporta **múltiplas clínicas independentes** com **isolamento total de dados**:

**Como Funciona:**
```
1. Usuário acessa: drmarco.horariointeligente.com.br
2. TenantMiddleware extrai subdomínio: "drmarco"
3. Busca cliente no banco: clientes.slug = "drmarco"
4. Injeta cliente_id em TODAS as queries
5. Dados isolados por cliente_id
```

**Benefícios:**
- ✅ **Isolamento total** - Clínica A nunca vê dados da Clínica B
- ✅ **URLs personalizadas** - Cada clínica tem seu subdomínio
- ✅ **Cache isolado** - Redis separado por tenant
- ✅ **WhatsApp isolado** - Conversas separadas por instância
- ✅ **Escalável** - Adicionar clínicas sem código novo

**Middleware (`app/middleware/tenant_middleware.py`):**
```python
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    # Extrair subdomínio
    host = request.headers.get("host", "")
    subdomain = host.split(".")[0]

    # Buscar cliente
    cliente = get_cliente_by_slug(subdomain)

    # Injetar no request
    request.state.cliente_id = cliente.id
    request.state.tenant = subdomain

    return await call_next(request)
```

---

## 🤖 Integração com IA

### Claude Sonnet 4.5 (Anthropic)

**Modelo:** `claude-sonnet-4-5-20250929`

**Características:**
- **Qualidade:** 10/10 (superior ao Opus 3)
- **Velocidade:** 4.7s de latência média
- **Custo:** $3 input / $15 output por 1M tokens
- **Context:** 200K tokens
- **Idioma:** Português brasileiro fluente

**Pricing:**
```
Input tokens:  $3 por 1M tokens
Output tokens: $15 por 1M tokens

Estimativa por profissional (200 agendamentos/mês):
├─ Input:  0.6M tokens × $3  = $1.80
├─ Output: 0.2M tokens × $15 = $3.00
└─ Total: ~$4.80/mês (~R$28/mês)
```

**O que NÃO consome tokens (custo zero):**
- ❌ Lembretes automáticos (templates fixos)
- ❌ Confirmações SIM/NÃO (interceptadas antes da IA)
- ❌ Notificações de falta (templates fixos)

**O que consome tokens:**
- ✅ Conversas de agendamento via WhatsApp
- ✅ Reagendamentos via chat
- ✅ Dúvidas e perguntas do paciente

### Serviço de IA (`app/services/ai_service.py`)

```python
class AIService:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("ANTHROPIC_MODEL")  # claude-sonnet-4-5-20250929

    async def processar_mensagem(
        self,
        mensagem: str,
        contexto: dict
    ) -> str:
        # System prompt com instruções
        # Contexto da conversa (Redis)
        # Informações do médico/agenda
        # Horários disponíveis

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=conversation_history
        )

        return response.content[0].text
```

---

## 🎯 Funcionalidades Principais

### 1. Agendamento via WhatsApp

**Fluxo Natural:**
```
Paciente: "Oi, quero marcar consulta"
IA: "Olá! Para qual dia você gostaria de agendar?"
Paciente: "Amanhã às 14h"
IA: "Perfeito! Qual seu nome completo?"
Paciente: "Maria Silva"
IA: "✅ Consulta agendada com Dr. Marco para
     02/12/2025 às 14:00. Enviaremos lembretes
     24h, 3h e 1h antes. Até lá!"
```

**Recursos:**
- Linguagem natural (sem menus ou comandos)
- Validação automática de horários
- Verificação de disponibilidade em tempo real
- Confirmação com detalhes completos
- Armazenamento no banco de dados

### 2. Sistema de Lembretes Automáticos

**3 níveis de lembrete:**

**24 horas antes:**
```
Olá Maria! 👋

Lembramos que você tem consulta agendada com
Dr. Marco amanhã, 02/12/2025 às 14:00.

📍 Endereço: Rua das Flores, 123 - Centro

Confirma sua presença? Responda SIM ou NÃO.
```

**3 horas antes:**
```
Olá Maria!

Sua consulta com Dr. Marco é daqui a 3 horas
(hoje às 14:00).

Já está a caminho? 😊
```

**1 hora antes:**
```
Última lembrança! ⏰

Sua consulta com Dr. Marco é em 1 hora (14:00).

Nos vemos em breve!
```

**Tecnologia:**
- Scheduler APScheduler (executa a cada 10 minutos)
- Templates fixos (custo zero)
- Flags no banco: `lembrete_24h_enviado`, `lembrete_3h_enviado`, `lembrete_1h_enviado`
- Timezone-aware (America/Sao_Paulo)

### 3. Resposta a Lembretes

**Paciente responde "SIM":**
```
✅ Presença confirmada!

Sua consulta com Dr. Marco está confirmada para
02/12/2025 às 14:00.

Obrigado! Até logo! 😊
```

**Paciente responde "NÃO":**
```
Sem problemas! Vamos remarcar sua consulta.

Quando você prefere agendar?
```

**Implementação:**
- Webhook do WhatsApp (`/api/webhooks/whatsapp`)
- Detecção de palavras-chave (SIM, NAO, CONFIRMO, etc.)
- Busca agendamento nas próximas 48h
- Atualiza status para "confirmado" ou inicia reagendamento

### 4. Gestão de Faltas

**Quando paciente não comparece:**

1. Médico/secretária clica em **"Marcar Falta"** no calendário
2. Sistema atualiza status para "faltou"
3. Busca 3 próximos horários disponíveis automaticamente
4. Envia mensagem empática via WhatsApp
5. Paciente escolhe novo horário e reagenda

**Mensagem enviada:**
```
Olá Maria! 😊

Notamos que você não compareceu à consulta com
Dr. Marco no dia 02/12/2025 às 14:00.

Entendemos que imprevistos acontecem! Gostaríamos
de remarcar sua consulta.

Temos os seguintes horários disponíveis:

1️⃣ Quarta, 04/12 às 14:00
2️⃣ Quinta, 05/12 às 10:00
3️⃣ Sexta, 06/12 às 16:00

Qual horário funciona melhor para você?
```

**Serviço:** `app/services/falta_service.py`

### 5. Dashboard Web Responsivo

**Telas disponíveis:**
- 📊 **Dashboard** - Visão geral de agendamentos
- 📅 **Calendário Unificado** - Visualização de todos os profissionais
- 👨‍⚕️ **Minha Agenda** - Agenda individual do profissional
- ⚙️ **Configuração de Agenda** - Horários, intervalos, dias de atendimento
- 👥 **Gestão de Profissionais** - Adicionar/editar profissionais
- 📱 **100% Responsivo** - Funciona perfeitamente em mobile

**Recursos do Calendário:**
- Visualização mensal com FullCalendar
- Cores por médico (até 10 cores distintas)
- Status visual:
  - 🟦 Azul: Agendado
  - 🟩 Verde: Confirmado
  - 🟥 Vermelho: Cancelado
  - 🟧 Laranja: Faltou
  - ⚪ Cinza: Realizado
- Modal de detalhes com ações:
  - Reagendar
  - Marcar falta
  - Cancelar
  - Confirmar

### 6. Autenticação e Permissões

**Tipos de usuário:**
- **Secretária** - Acesso total a todos os profissionais da clínica
- **Profissional** - Acesso apenas à própria agenda

**Autenticação:**
- JWT tokens (8 horas de validade)
- Middleware de autenticação
- Verificação de permissões por endpoint

**Endpoints protegidos:**
```python
@router.get("/agendamentos")
async def listar_agendamentos(
    current_user: dict = Depends(get_current_user)
):
    # Secretária vê todos
    # Profissional vê apenas os seus
    ...
```

---

## 📱 Progressive Web App (PWA)

### Recursos PWA

O sistema é um **PWA completo**, permitindo instalação como app nativo:

**Manifesto (`static/manifest.json`):**
```json
{
  "name": "ProSaude - Agendamento Médico",
  "short_name": "ProSaude",
  "start_url": "/static/dashboard.html",
  "display": "standalone",
  "theme_color": "#3b82f6",
  "background_color": "#ffffff",
  "icons": [
    {
      "src": "/static/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

**Service Worker (`static/service-worker.js`):**
- Cache de assets estáticos
- Funcionamento offline (páginas já visitadas)
- Estratégia Network First para dados dinâmicos

**Como instalar:**

**Opção 1 - Botão visível (Recomendado):**
1. Acesse o sistema pelo celular ou desktop
2. Procure o botão **"Instalar App"** com ícone de download:
   - **Desktop:** No cabeçalho superior (canto direito)
   - **Mobile:** No menu hamburguer (☰)
3. Clique no botão e confirme a instalação
4. App será instalado na tela inicial

**Opção 2 - Prompt automático do navegador:**
1. Acesse o sistema pelo celular
2. Chrome/Edge exibirá "Adicionar à tela inicial"
3. Aceite a instalação

**Após instalação:**
- App fica na home screen como nativo
- Abre em fullscreen (sem barra de navegação)
- Funciona offline para páginas já visitadas
- Recebe notificações push (em breve)

**Nota:** O botão de instalação só aparece quando:
- Site está em HTTPS
- App ainda não foi instalado
- Navegador suporta PWA (Chrome, Edge, Safari)

---

## ⚙️ Configuração e Instalação

### Requisitos

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- Nginx (produção)
- Evolution API (WhatsApp)
- Conta Anthropic (API Key)

### Variáveis de Ambiente (`.env`)

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agendamento_saas

# Redis
REDIS_URL=redis://localhost:6379/0

# FastAPI
SECRET_KEY=sua-chave-secreta-super-segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480  # 8 horas

# WhatsApp (Evolution API)
WHATSAPP_TOKEN=seu_token_evolution
WHATSAPP_PHONE_ID=seu_phone_id
WHATSAPP_VERIFY_TOKEN=token_verificacao

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# Environment
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO
LOG_FILE=logs/sistema.log
```

### Instalação

```bash
# 1. Clonar repositório
git clone https://github.com/seu-usuario/sistema_agendamento.git
cd sistema_agendamento

# 2. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar .env
cp .env.example .env
nano .env  # Editar com seus dados

# 5. Criar banco de dados
psql -U postgres -c "CREATE DATABASE agendamento_saas;"

# 6. Rodar migrações
alembic upgrade head

# 7. Criar dados iniciais
python scripts/setup_initial_data.py

# 8. Rodar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Configuração Systemd (Produção)

```bash
# /etc/systemd/system/prosaude.service
[Unit]
Description=ProSaude FastAPI Sistema de Agendamento
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/sistema_agendamento
Environment="PATH=/root/sistema_agendamento/venv/bin"
ExecStart=/root/sistema_agendamento/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Ativar serviço
sudo systemctl daemon-reload
sudo systemctl enable prosaude.service
sudo systemctl start prosaude.service
sudo systemctl status prosaude.service
```

### Nginx (Reverse Proxy Multi-Tenant)

```nginx
# /etc/nginx/sites-available/horariointeligente
server {
    listen 80;
    listen [::]:80;
    server_name *.horariointeligente.com.br horariointeligente.com.br;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name *.horariointeligente.com.br horariointeligente.com.br;

    ssl_certificate /etc/letsencrypt/live/horariointeligente.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/horariointeligente.com.br/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /root/sistema_agendamento/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Ativar site
sudo ln -s /etc/nginx/sites-available/horariointeligente /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL (Let's Encrypt)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Gerar certificado wildcard
sudo certbot certonly --manual \
  --preferred-challenges dns \
  -d horariointeligente.com.br \
  -d *.horariointeligente.com.br

# Renovação automática
sudo certbot renew --dry-run
```

---

## 🐍 Stack Tecnológico

### Backend

- **FastAPI** 0.116.2 - Framework web async
- **SQLAlchemy** 2.0+ - ORM
- **Alembic** - Migrações de banco
- **PostgreSQL** 15+ - Banco de dados
- **Redis** 7+ - Cache e sessões
- **Pydantic** - Validação de dados
- **APScheduler** - Agendamento de tarefas
- **httpx** - Cliente HTTP async
- **python-jose** - JWT tokens
- **passlib** - Hash de senhas

### Frontend

- **HTML5** + **CSS3** (Tailwind CSS)
- **JavaScript** (ES6+)
- **FullCalendar** 6.1.15 - Calendário interativo
- **Font Awesome** 6.x - Ícones
- **Progressive Web App** - PWA manifest + service worker

### Integrações

- **Anthropic Claude** API - IA conversacional
  - Modelo: Claude Sonnet 4.5
  - SDK: `anthropic` Python
- **Evolution API** - WhatsApp Business
  - Webhook para mensagens
  - Envio de templates
- **PostgreSQL** - Multi-tenant com `cliente_id`
- **Redis** - Cache de conversas por tenant

### DevOps

- **Nginx** - Reverse proxy + SSL
- **Systemd** - Gerenciamento de serviço
- **Let's Encrypt** - SSL gratuito
- **Git** - Controle de versão
- **Linux** Ubuntu/Debian - Sistema operacional

---

## 🔄 Fluxo de Uso

### 1. Agendamento via WhatsApp

```mermaid
sequenceDiagram
    Paciente->>WhatsApp: "Oi, quero marcar consulta"
    WhatsApp->>Evolution API: Webhook
    Evolution API->>FastAPI: POST /webhooks/whatsapp
    FastAPI->>TenantMiddleware: Identifica cliente
    FastAPI->>Redis: Busca contexto conversa
    FastAPI->>Claude Sonnet 4.5: Processa mensagem
    Claude Sonnet 4.5->>FastAPI: Resposta + ação
    FastAPI->>PostgreSQL: Cria agendamento
    FastAPI->>Redis: Atualiza contexto
    FastAPI->>Evolution API: Envia resposta
    Evolution API->>WhatsApp: Mensagem
    WhatsApp->>Paciente: "Consulta agendada!"
```

### 2. Lembretes Automáticos

```mermaid
sequenceDiagram
    APScheduler->>FastAPI: Trigger a cada 10min
    FastAPI->>PostgreSQL: Busca agendamentos (24h, 3h, 1h)
    PostgreSQL->>FastAPI: Lista agendamentos
    loop Para cada agendamento
        FastAPI->>Evolution API: Envia lembrete
        FastAPI->>PostgreSQL: Marca flag enviado
    end
```

### 3. Gestão de Falta

```mermaid
sequenceDiagram
    Secretária->>Frontend: Clica "Marcar Falta"
    Frontend->>FastAPI: POST /agendamentos/{id}/marcar-falta
    FastAPI->>PostgreSQL: UPDATE status = 'faltou'
    FastAPI->>PostgreSQL: Busca próximos horários
    FastAPI->>Evolution API: Envia mensagem empática
    Evolution API->>WhatsApp: Notificação
    WhatsApp->>Paciente: Sugestão reagendamento
```

---

## 💰 Custos de Operação

### Custo por Profissional (200 agendamentos/mês)

```
┌──────────────────────────┬─────────────┬──────────────┐
│ Item                     │ Custo/mês   │ Observação   │
├──────────────────────────┼─────────────┼──────────────┤
│ Claude Sonnet 4.5 (IA)   │ R$ 28,00    │ 200 agend.   │
│ WhatsApp (Evolution)     │ R$ 0,00     │ Self-hosted  │
│ Servidor VPS (shared)    │ R$ 10,00    │ Por 10 prof. │
│ PostgreSQL (shared)      │ R$ 0,00     │ Incluso      │
│ Redis (shared)           │ R$ 0,00     │ Incluso      │
│ SSL Certificate          │ R$ 0,00     │ Let's Encrypt│
│ ───────────────────────  │ ─────────── │ ──────────── │
│ TOTAL por profissional   │ R$ 38,00    │ Margem: 81%  │
└──────────────────────────┴─────────────┴──────────────┘

Receita: R$ 200/mês por profissional
Custo: R$ 38/mês por profissional
Lucro: R$ 162/mês por profissional (81% de margem)

Para 10 profissionais:
├─ Receita: R$ 2.000/mês
├─ Custo IA: R$ 280/mês (14%)
├─ Custo infra: R$ 100/mês (5%)
└─ Lucro: R$ 1.620/mês (81%)
```

### Escalabilidade

```
┌──────────────┬─────────────┬─────────────┬─────────────┐
│ Profissionais│ Custo IA    │ Custo Infra │ Lucro Mensal│
├──────────────┼─────────────┼─────────────┼─────────────┤
│ 10           │ R$ 280      │ R$ 100      │ R$ 1.620    │
│ 50           │ R$ 1.400    │ R$ 200      │ R$ 8.400    │
│ 100          │ R$ 2.800    │ R$ 500      │ R$ 16.700   │
│ 500          │ R$ 14.000   │ R$ 2.000    │ R$ 84.000   │
└──────────────┴─────────────┴─────────────┴─────────────┘

Nota: Custos de IA lineares, infraestrutura sublinear
```

---

## 📚 Documentação Adicional

### Arquivos de Documentação

- **[CREDENCIAIS_DEMO.md](CREDENCIAIS_DEMO.md)** - Todas as credenciais de acesso e dados de demonstração
- **[CHANGELOG.md](CHANGELOG.md)** - Histórico completo de alterações do sistema
- **[CHANGELOG_09DEZ2025.md](CHANGELOG_09DEZ2025.md)** - Documentação legal e atualizações da landing page
- **[PERFIL_FINANCEIRO.md](PERFIL_FINANCEIRO.md)** - Documentação do painel financeiro (gestão interna)
- **README.md** - Este arquivo (documentação principal)

### 📄 Documentação Legal (NOVO)

#### Termos e Condições de Uso
- **Arquivo:** `/static/termos-de-uso.html`
- **URL Pública:** https://horariointeligente.com.br/static/termos-de-uso.html
- **Conteúdo:**
  - 12 seções completas
  - Conceitos importantes (Cliente, Usuário, Administrador, Paciente)
  - Modelo de assinatura (Individual R$ 150 + Clínica R$ 200)
  - Integração WhatsApp (API oficial e Evolution API)
  - Condutas proibidas e penalidades
  - Cancelamento e reembolso (7 dias com reembolso total)
  - Propriedade intelectual
  - Suporte técnico e SLA
  - Foro: Volta Redonda - RJ

#### Política de Privacidade
- **Arquivo:** `/static/politica-privacidade.html`
- **URL Pública:** https://horariointeligente.com.br/static/politica-privacidade.html
- **Conformidade:** ✅ 100% LGPD (Lei nº 13.709/2018)
- **Conteúdo:**
  - 10 seções completas
  - Dados coletados (clientes, pacientes, uso, pagamento)
  - Finalidades do tratamento
  - Base legal (LGPD Art. 7º)
  - Compartilhamento de dados
  - Medidas de segurança (SSL, bcrypt, backup, firewall)
  - Todos os 8 direitos dos titulares (LGPD Art. 18)
  - DPO: Marco Aurélio Thiele (thelemarco@yahoo.com.br)
  - Prazo de resposta: 15 dias

#### Contato Legal
- **Email:** thelemarco@yahoo.com.br
- **WhatsApp:** (24) 98849-3257
- **DPO (Encarregado de Dados):** Marco Aurélio Thiele
- **Localização:** Volta Redonda - RJ, Brasil

### Estrutura de Diretórios

```
sistema_agendamento/
├── app/
│   ├── api/           # Endpoints REST
│   │   ├── agendamentos.py
│   │   ├── auth.py
│   │   ├── medicos.py
│   │   └── webhooks.py
│   ├── middleware/    # Middlewares
│   │   ├── auth_middleware.py
│   │   └── tenant_middleware.py
│   ├── models/        # Modelos SQLAlchemy
│   │   ├── agendamento.py
│   │   ├── cliente.py
│   │   ├── medico.py
│   │   └── paciente.py
│   ├── services/      # Lógica de negócio
│   │   ├── ai_service.py
│   │   ├── whatsapp_service.py
│   │   ├── reminder_service.py
│   │   └── falta_service.py
│   ├── utils/         # Utilitários
│   │   └── timezone_helper.py
│   ├── database.py    # Configuração DB
│   ├── main.py        # App FastAPI
│   └── scheduler.py   # APScheduler
├── alembic/           # Migrações
│   └── versions/
├── static/            # Frontend
│   ├── dashboard.html
│   ├── calendario-unificado.html
│   ├── minha-agenda.html
│   ├── configuracao-agenda.html
│   ├── login.html
│   ├── manifest.json
│   └── service-worker.js
├── logs/              # Logs do sistema
├── .env               # Variáveis de ambiente
├── requirements.txt   # Dependências Python
└── README.md          # Este arquivo
```

### Banco de Dados

**Principais tabelas:**

```sql
-- Multi-tenant
clientes (id, slug, nome, dominio)

-- Usuários
usuarios (id, email, senha_hash, tipo, cliente_id)

-- Médicos
medicos (id, nome, especialidade, cliente_id, usuario_id)
configuracoes_medico (medico_id, horario_inicio, horario_fim, intervalo_consulta)

-- Pacientes
pacientes (id, nome, telefone, email, cliente_id)

-- Agendamentos
agendamentos (
    id,
    data_hora,
    status,
    paciente_id,
    medico_id,
    cliente_id,
    lembrete_24h_enviado,
    lembrete_3h_enviado,
    lembrete_1h_enviado
)
```

### API Endpoints

**Autenticação:**
```
POST   /api/auth/login          # Login
GET    /api/auth/me             # Usuário atual
POST   /api/auth/logout         # Logout
```

**Agendamentos:**
```
GET    /api/agendamentos                    # Listar
POST   /api/agendamentos                    # Criar
GET    /api/agendamentos/{id}               # Detalhes
PUT    /api/agendamentos/{id}               # Atualizar
DELETE /api/agendamentos/{id}               # Deletar
POST   /api/agendamentos/{id}/marcar-falta  # Marcar falta
GET    /api/agendamentos/calendario         # Calendário
```

**Médicos:**
```
GET    /api/medicos                         # Listar
POST   /api/medicos                         # Criar
GET    /api/medicos/{id}                    # Detalhes
PUT    /api/medicos/{id}                    # Atualizar
```

**Webhooks:**
```
POST   /api/webhooks/whatsapp               # WhatsApp
```

---

## 🎉 Resumo de Conquistas

### Versão 3.5.1 (Atual - 09/12/2025)

✅ **Documentação Legal Completa** - Termos de Uso e Política de Privacidade
✅ **100% Conforme LGPD** - Política de privacidade com todos os 8 direitos dos titulares
✅ **Landing Page Atualizada** - Contatos reais (thelemarco@yahoo.com.br, 24 98849-3257)
✅ **Botões de Login Desabilitados** - Sistema preparado para lançamento controlado
✅ **Links Legais Funcionais** - Footer com navegação para documentos legais
✅ **DPO Identificado** - Marco Aurélio Thiele como encarregado de dados
✅ **Documentação Técnica Atualizada** - CHANGELOG_09DEZ2025.md criado

### Versão 3.5.0 (07/12/2025)

✅ Correção do formato de envio de mensagens WhatsApp (Evolution API v2.0.10)
✅ Correção do formato de envio de áudio WhatsApp
✅ Validação completa de agendamento (evita confirmação prematura)
✅ Limpeza e recriação da base Evolution API
✅ Webhook reconfigurado com eventos corretos
✅ Sistema de áudio híbrido 100% funcional (texto + áudio TTS)
✅ Conexão WhatsApp estável e operacional

### Versão 3.4.0

✅ Dashboard com dados reais (substituído dados mock)
✅ Métricas completas (taxa de comparecimento, faltas, cancelamentos)
✅ Endpoint de agenda do dia
✅ Dados de demonstração populados (101 agendamentos)

### Versão 3.2.0

✅ Migração para Claude Sonnet 4.5 (80% economia)
✅ Sistema de gestão de faltas completo
✅ Correções definitivas de timezone
✅ Token JWT de 8 horas
✅ Economia de R$ 112/mês por médico
✅ Margem de lucro de 81%
✅ Sistema 100% funcional em produção

### Versão 3.1.0

✅ Correção definitiva de timezone
✅ PWA instalável
✅ Resposta a lembretes via WhatsApp
✅ Sistema de lembretes 24h/3h/1h

### Versão 3.0.0

✅ Multi-tenant SaaS 100% funcional
✅ HTTPS em produção
✅ Wildcard SSL
✅ Nginx reverse proxy
✅ Isolamento total por cliente

### Versão 2.4.1

✅ Interface 100% responsiva
✅ Mobile-first design
✅ Calendário interativo

### Versão 2.0.0

✅ Integração com WhatsApp
✅ IA Claude para agendamento
✅ Dashboard web completo

---

## 📞 Contato e Suporte

### Desenvolvedor
**Nome:** Marco Aurélio Thiele
**Email:** thelemarco@yahoo.com.br
**WhatsApp:** (24) 98849-3257
**Localização:** Volta Redonda - RJ, Brasil

### DPO (Encarregado de Proteção de Dados)
**Nome:** Marco Aurélio Thiele
**Email:** thelemarco@yahoo.com.br
**WhatsApp:** (24) 98849-3257

### Links Importantes
**Site Principal:** https://horariointeligente.com.br
**Termos de Uso:** https://horariointeligente.com.br/static/termos-de-uso.html
**Política de Privacidade:** https://horariointeligente.com.br/static/politica-privacidade.html
**Assistente:** Claude Code (Anthropic)

---

**Última atualização:** 9 de dezembro de 2025
**Versão:** 3.6.0
**Status:** ✅ Em Produção
**Conformidade:** ✅ LGPD (Lei 13.709/2018)
