# Changelog - Horário Inteligente SaaS

## [3.6.1] - 2026-01-20

### 🆕 Adicionado
- **Botão de login na landing page**: Habilitado acesso para clientes
  - Menu desktop: Botão "Entrar" azul no header
  - Menu mobile: Botão "Entrar" no menu hambúrguer
  - Footer: Links "Login" e "Criar Conta" na seção Produto
  - Arquivo: `static/index.html`

- **Link "Ainda não é cliente?" na página de login**
  - Seção com separador visual após "Esqueci minha senha"
  - Direciona para formulário de contato da landing page
  - Facilita conversão de visitantes em leads
  - Arquivo: `static/login.html`

### 🔒 Segurança
- **Validação de senha aumentada para 8 caracteres**: Mínimo alterado de 6 para 8
  - Backend: `RegisterRequest`, `ResetPasswordRequest`, `ChangePasswordRequest`
  - Frontend: `registro.html`, `perfil.html`, `reset-senha.html`
  - Arquivo: `app/api/user_management.py`

- **Indicador visual de força de senha**: Adicionado em todos os formulários de senha
  - Barra de progresso colorida (vermelho → verde)
  - Label de força: Muito fraca, Fraca, Média, Forte, Muito forte
  - Checklist de 5 requisitos com atualização em tempo real:
    - Mínimo 8 caracteres
    - Uma letra minúscula
    - Uma letra maiúscula
    - Um número
    - Um caractere especial
  - Integração com `HiValidation.getPasswordStrength()`
  - Arquivos: `static/registro.html`, `static/perfil.html`, `static/reset-senha.html`

- **Link "Esqueci minha senha" adicionado**: Páginas de login admin e financeiro
  - `static/admin/login.html` - Estilo adaptado ao tema escuro
  - `static/financeiro/login.html` - Estilo verde consistente
  - Redireciona para `/static/esqueci-senha.html` (sistema já existente)

### 🎤 Áudio WhatsApp (API Oficial Meta)
- **Integração completa de áudio no webhook oficial**
  - Arquivo: `app/api/webhook_official.py`

- **Recebimento de áudio (Speech-to-Text)**
  - Download de áudio via `media_id` da API oficial Meta
  - Transcrição automática com OpenAI Whisper
  - Texto transcrito processado pela IA Claude
  - Suporte a arquivos `.ogg` (formato padrão WhatsApp)

- **Envio de áudio (Text-to-Speech)**
  - Geração de áudio com OpenAI TTS
  - Voz: `nova` (feminina, amigável)
  - Velocidade: 1.1x (ligeiramente mais rápida)
  - Upload de mídia para API oficial e envio

- **Preferências inteligentes do paciente**
  - Modo AUTO (espelho): áudio → resposta com áudio; texto → só texto
  - Modo SEMPRE: sempre envia texto + áudio
  - Modo NUNCA: apenas texto
  - Detecção automática por frases naturais:
    - "prefiro texto", "sem áudio" → modo NUNCA
    - "pode mandar áudio", "adorei o áudio" → modo SEMPRE
  - Integração com `audio_preference_service.py`

- **Configurações `.env`**
  ```
  ENABLE_AUDIO_INPUT=true
  ENABLE_AUDIO_OUTPUT=true
  AUDIO_OUTPUT_MODE=hybrid
  TTS_VOICE=nova
  TTS_SPEED=1.1
  ```

### ✅ Verificado
- **Hash bcrypt de senhas**: Verificado que todas as 8 senhas de médicos já estão em bcrypt
  - Script `scripts/hash_medicos_passwords.py --execute` executado
  - Nenhuma migração necessária (todas já hasheadas)

---

## [3.6.0] - 2026-01-19

### 🆕 Adicionado
- **Models de Conversas WhatsApp**: Persistência de conversas e mensagens no PostgreSQL
  - `Conversa`: cliente_id, paciente_telefone, paciente_nome, status, atendente_id
  - `Mensagem`: conversa_id, direcao, remetente, tipo, conteudo, midia_url
  - Enums: `StatusConversa`, `DirecaoMensagem`, `RemetenteMensagem`, `TipoMensagem`
  - Arquivos: `app/models/conversa.py`, `app/models/mensagem.py`

- **ConversaService**: Service para gerenciar conversas e mensagens
  - `criar_ou_recuperar_conversa()`: Busca ou cria conversa ativa
  - `adicionar_mensagem()`: Adiciona mensagem à conversa
  - `assumir_conversa()`: Atendente assume (desativa IA)
  - `devolver_para_ia()`: Devolve para IA
  - `encerrar_conversa()`: Encerra a conversa
  - `listar_conversas()`: Lista por cliente/status
  - `buscar_mensagens()`: Mensagens de uma conversa
  - `marcar_mensagens_como_lidas()`: Marca como lidas
  - `contar_nao_lidas()`: Conta não lidas
  - Arquivo: `app/services/conversa_service.py`

- **API REST de Conversas**: Endpoints para painel de atendimento
  - `GET /api/conversas`: Lista conversas do cliente
  - `GET /api/conversas/stats`: Estatísticas (ativas, assumidas, não lidas)
  - `GET /api/conversas/{id}`: Detalhes com mensagens
  - `POST /api/conversas/{id}/mensagens`: Enviar mensagem (atendente)
  - `PUT /api/conversas/{id}/assumir`: Assumir conversa
  - `PUT /api/conversas/{id}/devolver-ia`: Devolver para IA
  - `PUT /api/conversas/{id}/encerrar`: Encerrar conversa
  - Arquivo: `app/api/conversas.py`

- **WebSocket para Tempo Real**: Notificações instantâneas no painel
  - `WebSocketManager`: Gerenciador de conexões por tenant
  - `WS /ws/conversas?token=JWT`: Endpoint WebSocket autenticado
  - `GET /ws/status`: Status das conexões (debug)
  - Eventos: `nova_mensagem`, `conversa_atualizada`, `nova_conversa`
  - Arquivos: `app/services/websocket_manager.py`, `app/api/websocket.py`

- **Webhook Integrado com PostgreSQL**: Persistência de mensagens
  - Salva mensagem do paciente no banco ao receber
  - Salva resposta da IA no banco após processar
  - Verifica status da conversa (se humano assumiu, IA não responde)
  - Notifica via WebSocket em tempo real
  - Arquivo: `app/api/webhook_official.py`

- **Painel de Conversas WhatsApp** (Frontend): Interface completa
  - Layout responsivo (sidebar + chat)
  - Lista de conversas com busca, filtros e badges
  - Chat estilo WhatsApp (bolhas coloridas por remetente)
  - Conexão WebSocket para atualizações em tempo real
  - Botões: Assumir, Devolver para IA, Encerrar
  - Som de notificação para novas mensagens
  - Arquivo: `static/conversas.html`

- **Link no Dashboard**: Acesso rápido ao painel de conversas
  - Botão verde "Conversas" no header
  - Badge dinâmico com contador de não lidas
  - Item no menu mobile (HiBottomNav)
  - Arquivo: `static/dashboard.html`

- **Script de Seed para Testes**: Dados de teste para validação do sistema
  - Cria usuários de teste: Ana Silva, Dr. Carlos, Dra. Maria
  - Trata duplicatas graciosamente (atualiza em vez de falhar)
  - Arquivo: `scripts/seed_prosaude.py`

### 🔒 Segurança
- **Migração de senhas para bcrypt**: Script para migrar senhas em texto plano
  - Arquivo: `scripts/hash_medicos_passwords.py`
- **Removido fallback de texto plano**: `verify_password()` agora rejeita senhas não-bcrypt
  - Arquivo: `app/api/auth.py`

### ✅ Corrigido
- **Envio de mensagem pelo painel**: Corrigido erro `missing positional argument`
  - Trocado `WhatsAppService` por `WhatsAppOfficialService` (API Meta)
  - Usa `send_text(to, message)` com assinatura correta
  - Arquivo: `app/api/conversas.py`

- **Duplicação de mensagens no frontend**: Mensagens do atendente apareciam 2x
  - Adicionado `data-msg-id` em cada mensagem HTML
  - Verificação de duplicata antes de inserir via WebSocket
  - Arquivo: `static/conversas.html`

- **Token de autenticação no painel**: Chave incorreta no localStorage
  - Corrigido `token` → `authToken` (consistente com dashboard)
  - Arquivo: `static/conversas.html`

- **Acesso a current_user como dict**: API retorna dict, não objeto
  - Corrigido `current_user.cliente_id` → `current_user["cliente_id"]`
  - Arquivo: `app/api/conversas.py`

- **Tipo de mensagem no webhook**: Atributo incorreto
  - Corrigido `message.type` → `message.message_type`
  - Arquivo: `app/api/webhook_official.py`
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
- **Painel de Conversas**: Interface web funcionando com WebSocket em tempo real
- **Assumir Conversa**: Atendente assume e IA para de responder
- **Devolver para IA**: Conversa volta para atendimento automático
- **Envio manual**: Atendente pode enviar mensagens pelo painel
- **Sem duplicatas**: Mensagens não duplicam mais no frontend

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

### ⚠️ Pendências Conhecidas (Resolvidas em 3.6.1)
- ~~**Segurança**: Senhas dos médicos ainda em texto plano~~ → ✅ Verificado: todas já em bcrypt
- ~~**TODO**: Criar script `scripts/hash_medicos_passwords.py`~~ → ✅ Script criado e executado

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
