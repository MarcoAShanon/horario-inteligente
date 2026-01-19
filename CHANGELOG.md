# Changelog - Horário Inteligente SaaS

## [3.6.0] - 2026-01-19

### ✅ Corrigido
- **Webhook WhatsApp API Oficial (Meta Cloud API)**: Corrigido problema de mensagens não chegando ao sistema
  - App não estava assinado na WABA - executado POST em `/subscribed_apps` para assinar
  - WABA_ID correto identificado: `1567749557793633` (era usado ID incorreto `214443058942535`)
  - Arquivo: `app/api/webhook_official.py`

- **Parâmetros incorretos no webhook_official.py**:
  - `limite` → `limit` (linha 107)
  - `tipo` → `message_type` (linhas 129, 138)
  - `texto` → `text` (linhas 130, 139)
  - `dados` → `dados_coletados` (linhas 132, 141)

- **Registro do número na Cloud API**: Número +55 21 92367-0092 registrado via endpoint `/register`

### 🔄 Modificado
- **WHATSAPP_BUSINESS_ACCOUNT_ID**: Atualizado no .env de `214443058942535` para `1567749557793633`

### ✅ Testado e Funcionando
- **Recebimento de mensagens**: Webhook recebendo POSTs do Facebook corretamente
- **Processamento com IA**: Claude processando mensagens via API Anthropic
- **Envio de respostas**: Respostas sendo enviadas via Graph API do WhatsApp
- **Persistência de contexto**: Conversas sendo salvas no Redis

### 📝 Observações Técnicas
- **App ID**: `1902202273996968` (Horario Inteligente API)
- **WABA ID**: `1567749557793633`
- **Phone ID**: `989612447561309`
- **Número**: +55 21 92367-0092 (Horário Inteligente)

---

## [3.5.0] - 2025-12-07

### ✅ Corrigido
- **Formato de envio de mensagens de texto WhatsApp**: Removido wrapper `textMessage` para compatibilidade com Evolution API v2.0.10
  - Antes: `{"textMessage": {"text": "..."}}`
  - Depois: `{"text": "..."}`
  - Arquivo: `app/api/webhooks.py` (linha 984)

- **Formato de envio de áudio WhatsApp**: Removido wrapper `mediaMessage` para compatibilidade com Evolution API v2.0.10
  - Antes: `{"mediaMessage": {"mediatype": "audio", "media": "..."}}`
  - Depois: `{"mediatype": "audio", "media": "..."}`
  - Arquivo: `app/services/whatsapp_service.py` (linhas 261-266)

- **Validação de agendamento via WhatsApp**: Adicionado requisito de especialidade/médico antes de confirmar agendamento
  - Impede confirmação prematura de agendamentos sem dados completos
  - Requer: nome, data, hora E (especialidade OU médico_id)
  - Arquivo: `app/api/webhooks.py` (linhas 545-570)

### 🔄 Modificado
- **Base de dados Evolution API**: Limpeza completa de instância corrompida
  - Removida instância ProSaude com dados de sessão corrompidos
  - Recriada instância do zero com configurações corretas

- **Webhook Evolution API**: Reconfigurado com eventos corretos
  - URL: `http://145.223.95.35:8000/webhook/whatsapp/ProSaude`
  - Eventos: MESSAGES_UPSERT, MESSAGES_UPDATE, SEND_MESSAGE, CONNECTION_UPDATE
  - Ativação automática confirmada

### 🎯 Melhorias de Sistema
- **Modo de áudio híbrido**: Funcionando corretamente (texto + áudio)
  - OpenAI TTS gerando áudios MP3
  - Base64 encoding correto
  - Envio via Evolution API v2.0.10 sem erros

- **Conexão WhatsApp**: Estável e operacional
  - QR Code gerado com sucesso
  - Conexão persistente (state: "open")
  - Webhook respondendo corretamente

### 📝 Observações Técnicas
- **Evolution API v2.0.10**: Versão estável confirmada (v2.1.1 apresentou problemas de compatibilidade)
- **Erro corrigido**: `400 - instance requires property "text"` → resolvido
- **Erro corrigido**: `400 - instance requires property "mediatype" and "media"` → resolvido
- **Auto-reload**: FastAPI detectando mudanças e recarregando automaticamente

---

## [3.4.0] - 2025-12-04

### ✅ Corrigido
- **Dashboard com dados reais**: Substituído dados mock por queries SQL reais em `app/api/dashboard_simples.py`
- **Métricas do dashboard**: Adicionados campos que estavam faltando:
  - `atendimentos_realizados` (status = 'concluido')
  - `faltas_sem_aviso` (status = 'faltou')
  - `cancelamentos` (status = 'cancelado')
  - `taxa_comparecimento` (cálculo: realizados / (realizados + faltas) * 100)
- **Contagem de consultas da semana**: Alterado para contar TODOS os agendamentos da semana (não apenas confirmados)
- **Endpoint `/api/dashboard/agenda/hoje`**: Adicionado endpoint que estava faltando para exibir agenda do dia

### 🔄 Modificado
- **Emails do sistema**: Corrigidos emails internos de @prosaude.com para @horariointeligente.com.br
  - Super Admin: admin@horariointeligente.com.br
  - Financeiro: financeiro@horariointeligente.com.br
- **Dados de demonstração**: Populados 101 agendamentos para ProSaude com distribuição realista:
  - 61 Confirmados (60.4%)
  - 18 Remarcados (17.8%)
  - 12 Cancelados (11.9%)
  - 8 Concluídos (7.9%)
  - 2 Faltas (2.0%)
- **Distribuição entre médicos**:
  - Dra. Tânia Maria (Alergista): 53 agendamentos
  - Dr. Marco Aurélio (Cardiologista): 48 agendamentos

### 📝 Documentado
- **CREDENCIAIS_DEMO.md**: Documentação completa de todas as credenciais de acesso
- **README.md**: Adicionado aviso crítico sobre hash de senhas pendente
- **CHANGELOG.md**: Criado arquivo de histórico de alterações

### ⚠️ Pendências Conhecidas
- **Segurança**: Senhas dos médicos ainda em texto plano (precisa aplicar hash bcrypt)
- **TODO**: Criar script `scripts/hash_medicos_passwords.py` antes de produção

---

## [3.3.0] - 2025-12-03

### ✅ Adicionado
- Painel Financeiro para gestão interna do SaaS
- Métricas de negócio (MRR, custos, lucro)
- Dashboard para visualização de clientes e faturamento

---

## [3.2.0] - 2025-12-02

### ✅ Adicionado
- Painel Admin Multi-Tenant
- Gestão de clientes (CRUD completo)
- Sistema de onboarding de novos clientes

---

## [3.1.0] - 2025-12-01

### ✅ Adicionado
- Integração completa com Evolution API
- Sistema de lembretes via WhatsApp
- Confirmação de consultas automática

---

## [3.0.0] - 2025-11-30

### ✅ Lançamento Inicial
- Sistema de agendamento médico multi-tenant
- Autenticação JWT
- Dashboard para médicos e secretárias
- Calendário de consultas
- Gestão de pacientes

---

**Legenda:**
- ✅ Adicionado: Novas funcionalidades
- 🔄 Modificado: Alterações em funcionalidades existentes
- ✅ Corrigido: Correções de bugs
- ⚠️ Pendências: Itens que precisam ser resolvidos
- 🔒 Segurança: Alterações relacionadas à segurança
- 📝 Documentado: Melhorias na documentação
