# Documento de Continuidade - Sistema de Agendamento

## Visão Geral
Sistema de agendamento médico multi-tenant (SaaS) chamado **Horário Inteligente**.

- **Stack**: FastAPI (Python) + PostgreSQL + HTML/JS (Tailwind CSS)
- **Serviço**: `horariointeligente.service` (systemd)
- **Porta**: 8000
- **Diretório**: `/root/sistema_agendamento`

---

## Estrutura Principal

```
/root/sistema_agendamento/
├── app/
│   ├── api/
│   │   ├── agendamentos.py    # CRUD de agendamentos, listagem de médicos
│   │   ├── dashboard.py       # Métricas e dados financeiros
│   │   ├── auth.py            # Autenticação
│   │   ├── medico_config.py   # Configurações do médico (horários, convênios)
│   │   └── ...
│   ├── database.py
│   └── main.py
├── static/
│   ├── calendario-unificado.html  # Tela principal de agendamentos
│   ├── dashboard.html             # Painel com métricas e financeiro
│   ├── js/components/
│   │   ├── top-nav.js             # Navegação desktop (HiTopNav)
│   │   ├── nav-init.js            # Inicializador unificado (HiNavInit)
│   │   ├── bottom-nav.js          # Navegação mobile (HiBottomNav)
│   │   └── ...
│   └── ...
└── venv/
```

---

## Banco de Dados (PostgreSQL)

**Conexão**: `PGPASSWORD=postgres psql -h localhost -U postgres -d agendamento_saas`

### Tabelas Principais
- `medicos` - Cadastro de médicos (inclui secretárias com `is_secretaria=true`)
  - `convenios_aceitos` (JSONB) - Array de convênios: `[{"nome": "Amil", "valor": 100.00, "codigo": "amil"}, ...]`
- `pacientes` - Cadastro de pacientes
- `agendamentos` - Agendamentos com campos:
  - `forma_pagamento` (VARCHAR) - 'particular' ou 'convenio_0', 'convenio_1', etc. (índice do array de convênios)
  - `valor_consulta` (VARCHAR) - Valor da consulta
  - `status` - 'confirmado', 'realizado', 'cancelado', 'faltou', etc.
  - `data_hora` (TIMESTAMP WITH TIME ZONE) - Armazenado em UTC
- `lembretes` - Lembretes de agendamentos (FK para agendamentos)
- `clientes` - Tenants do sistema (multi-tenant)

---

## APIs Principais

### Agendamentos
- `POST /api/agendamentos` - Criar agendamento
- `GET /api/agendamentos/{id}` - Detalhes do agendamento
- `GET /api/medicos` - Lista médicos (retorna `convenios_aceitos`)
- `GET /api/horarios-disponiveis` - Horários disponíveis

### Dashboard
- `GET /api/dashboard/metricas?periodo=mes_atual` - Métricas gerais (inclui horários populares em BRT)
- `GET /api/dashboard/financeiro?periodo=mes_atual` - Dados financeiros (faturamento, breakdown por tipo/convênio)
- `GET /api/dashboard/financeiro/resumo?mes=1&ano=2026` - Previsto vs Realizado

---

## Fluxo de Agendamento

1. Frontend (`calendario-unificado.html`) envia:
   - `paciente_nome`, `paciente_telefone`, `medico_id`, `data`, `hora`
   - `forma_pagamento` ('particular' ou 'convenio_X')
   - `valor_consulta` (obtido do dropdown de convênios)

2. Backend (`agendamentos.py`):
   - Cria/busca paciente
   - Insere agendamento com `forma_pagamento` e `valor_consulta`
   - Cria lembretes automáticos

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

# Acessar banco
PGPASSWORD=postgres psql -h localhost -U postgres -d agendamento_saas

# Ativar venv
source /root/sistema_agendamento/venv/bin/activate
```

---

## Correções Realizadas (Sessão 27/01/2026)

### 1. Salvar forma_pagamento no agendamento
- **Problema**: Campo `forma_pagamento` não estava sendo salvo no INSERT
- **Solução**: Adicionado campo no INSERT em `agendamentos.py:187-203`
- **Coluna criada**: `ALTER TABLE agendamentos ADD COLUMN forma_pagamento VARCHAR(50)`

### 2. Modal de detalhes - Exibir forma de pagamento
- **Arquivo**: `static/calendario-unificado.html`
- **Seção adicionada**: Bloco "Pagamento" no modal de detalhes
- **Lógica**: Busca nome do convênio do array `medicosData` baseado no índice

### 3. API Financeiro para Dashboard
- **Problema**: Endpoint `/api/dashboard/financeiro` não existia
- **Solução**: Criado endpoint em `dashboard.py` que retorna:
  - `faturamento_total`, `total_atendimentos`
  - `particular` e `convenio` (valor e quantidade)
  - `por_convenio` (lista para gráficos com nome real do convênio)

### 4. API de Médicos - Retornar convênios
- **Problema**: `/api/medicos` não retornava `convenios_aceitos`
- **Solução**: Adicionado campo no SELECT e retorno em `agendamentos.py:358-380`

### 5. Gráficos do Dashboard Financeiro não exibidos
- **Problema**: Gráfico "Distribuição por Tipo" (pizza) e "Detalhamento" não apareciam
- **Causa**: Função `renderizarBreakdown()` fazia `return` antes de chamar `renderizarGraficoFinanceiro()`
- **Solução**:
  - Movido a chamada do gráfico para antes da verificação de dados vazios
  - Adicionada mensagem "Sem dados para exibir" quando não há dados
- **Arquivo**: `static/dashboard.html:568-668`

### 6. Gráficos Financeiros - Incluir Previsto + Realizado
- **Problema**: Gráficos mostravam apenas agendamentos realizados
- **Solução**: API agora inclui todos os status válidos
- **Incluídos**: `realizado`, `realizada`, `concluido`, `concluida`, `confirmado`, `confirmada`, `agendado`, `agendada`, `pendente`
- **Excluídos**: `cancelado`, `cancelada`, `faltou`
- **Arquivo**: `app/api/dashboard.py:559-666`

### 7. Nome dos convênios não aparecia nos gráficos
- **Problema**: Todos os agendamentos apareciam como "Particular"
- **Causa**: Query usava `p.convenio` (paciente), mas o nome está em `medicos.convenios_aceitos` (JSON)
- **Solução**: Query extrai o nome do convênio do JSON usando índice:
  ```sql
  m.convenios_aceitos::jsonb -> CAST(SUBSTRING(a.forma_pagamento FROM 'convenio_([0-9]+)') AS INTEGER) ->> 'nome'
  ```
- **Arquivo**: `app/api/dashboard.py:645-680`

### 8. Horários mais procurados com fuso horário errado
- **Problema**: Gráfico mostrava horários em UTC ao invés de Brasília
- **Exemplo**: Agendamento às 09:00 BRT aparecia como 12:00 UTC
- **Solução**: Query alterada para usar `AT TIME ZONE 'America/Sao_Paulo'`
- **Arquivo**: `app/api/dashboard.py:380-394`

### 9. Dados demo do Dr. Carlos atualizados
- **Problema**: Todos os agendamentos estavam como "particular"
- **Solução**: Distribuição realista de convênios para demonstração
- **Distribuição atual**:
  | Tipo | Qtd | Valor | % |
  |------|-----|-------|---|
  | Particular | 52 | R$ 9.320,00 | 64.5% |
  | Bradesco Saúde | 9 | R$ 1.260,00 | 8.7% |
  | Unimed | 10 | R$ 1.200,00 | 8.3% |
  | SulAmérica | 9 | R$ 1.170,00 | 8.1% |
  | Amil | 10 | R$ 1.000,00 | 6.9% |
  | Hapvida | 7 | R$ 490,00 | 3.4% |

### 10. Senhas de teste resetadas
- **Usuários**: Dr. João (ID 31) e Ana Santos (ID 32)
- **Nova senha**: `teste123`

---

## Correções Realizadas (Sessão 28/01/2026)

### 11. Indicação Visual de Horários Indisponíveis no Calendário
- **Problema**: Calendário não mostrava visualmente quais horários/dias estavam indisponíveis
- **Solução**: Implementada indicação visual com CSS e verificação de disponibilidade
- **Arquivo principal**: `static/calendario-unificado.html`

#### Funcionalidades Implementadas:
1. **CSS para células indisponíveis** (linhas 554-634):
   - Dias indisponíveis (mensal): fundo cinza, cursor not-allowed
   - Slots indisponíveis (semanal): padrão listrado diagonal
   - Slots indisponíveis (diário): fundo claro com padrão sutil

2. **Variáveis globais**:
   - `configMedicoSelecionado`: configurações de horário do médico
   - `bloqueiosPeriodo`: bloqueios ativos do período visível

3. **Funções de verificação**:
   - `carregarDisponibilidadeMedico(medicoId)`: carrega config e bloqueios
   - `carregarBloqueiosPeriodo(medicoId)`: carrega bloqueios do período
   - `verificarDiaDisponivel(data)`: verifica dias de atendimento
   - `verificarHorarioDisponivel(data, hora)`: verifica horário no expediente
   - `verificarDataBloqueada(data)`: verifica bloqueios

4. **Comportamento**:
   - Médico logado: disponibilidade carregada automaticamente
   - Secretária: disponibilidade carregada ao selecionar médico no filtro
   - "Todos os médicos": sem indicação (todos clicáveis)
   - Células indisponíveis: não abrem modal de agendamento

5. **Legenda atualizada**: Adicionado item "Fora do Expediente"

#### APIs Utilizadas:
- `GET /api/medicos/{id}/configuracoes` - Configurações do médico
- `GET /api/medicos/{id}/bloqueios` - Bloqueios ativos

### 12. IA não consultava horários reais do médico
- **Problema**: IA "inventava" horários genéricos (8h-17h) para todos os médicos
- **Causa Raiz**: O prompt da IA tinha horários hardcoded na linha 218:
  ```
  "Os médicos atendem de hora em hora: 8h, 9h, 10h, 11h, 12h, 13h, 14h, 15h, 16h, 17h"
  ```
- **A IA NÃO recebia**: dias de atendimento, horários por dia, bloqueios de agenda
- **Solução implementada**:
  1. Modificado `_obter_contexto_clinica()` para buscar configurações de `configuracoes_medico`
  2. Adicionado import `from sqlalchemy import text`
  3. Cada médico agora inclui `disponibilidade` com `dias_atendimento` e `horarios_por_dia`
  4. Modificado `_construir_prompt()` para exibir horários reais de cada médico
  5. Substituída regra genérica por instruções para consultar os horários configurados
- **Arquivo**: `app/services/anthropic_service.py`
- **Resultado**: IA agora informa corretamente os dias e horários de atendimento de cada médico
  - Exemplo Dr. João: Segunda/Quarta 08:00-18:00 (almoço 12:00-13:00), Sexta 08:00-11:00

### 13. IA permitia agendar em horários já ocupados
- **Problema**: IA confirmava agendamento em horários que já tinham paciente marcado
- **Causa Raiz**: Função `criar_agendamento_from_ia()` não verificava conflito de horário
- **Solução implementada**:
  1. Adicionado import `from app.services.agendamento_service import AgendamentoService`
  2. Antes de criar agendamento, chama `verificar_disponibilidade_medico()`
  3. Se horário ocupado, retorna dict com erro `{"erro": "horario_indisponivel"}`
  4. Webhook trata o erro e envia mensagem informando que horário não está disponível
- **Arquivo**: `app/api/webhook_official.py`
- **Mensagem de erro**: "😔 Desculpe, mas o horário de [data] não está mais disponível..."

### 14. Cache do Redis mantinha histórico de conversa
- **Problema**: Mesmo após deletar conversa do PostgreSQL, o histórico permanecia no Redis
- **Causa**: `ConversationManager` salva contexto no Redis (`conversation:cliente_X:telefone`)
- **Solução**: Ao limpar testes, deletar também as chaves do Redis:
  ```bash
  redis-cli KEYS "*telefone*"
  redis-cli DEL "conversation:cliente_11:5524988493257"
  ```

### 15. Convênios não salvavam automaticamente (UX confusa)
- **Problema**: Ao adicionar convênio no modal, aparecia na tela mas não era salvo no banco
- **Causa UX**: Usuário precisava clicar em "Salvar Valores" após "Adicionar" no modal
- **Confusão**: Convênio aparecia visualmente, dando impressão de que já estava salvo
- **Solução**: Salvar automaticamente ao adicionar/editar/remover convênio
- **Arquivo**: `static/configuracoes.html`
- **Função criada**: `salvarConveniosAutomatico()` - chamada após cada operação com convênio
- **Resultado**: Convênio é salvo imediatamente ao clicar "Adicionar" no modal

### 16. Lista de conversas não atualizava em tempo real
- **Problema**: Painel lateral com lista de conversas não atualizava quando nova conversa chegava
- **Causa**: Função `send_nova_conversa()` existia no WebSocket mas nunca era chamada
- **Solução**:
  1. Modificado `criar_ou_recuperar_conversa()` para retornar tupla `(conversa, is_nova)`
  2. No webhook, quando `is_nova=True`, chama `websocket_manager.send_nova_conversa()`
  3. Frontend já tinha `handleNovaConversa()` implementado, só precisava do evento
- **Arquivos modificados**:
  - `app/services/conversa_service.py` - retorna flag `is_nova`
  - `app/api/webhook_official.py` - envia evento WebSocket para novas conversas
  - `app/api/webhooks.py` - ajustado para nova assinatura da função
- **Resultado**: Lista lateral atualiza automaticamente quando nova conversa chega

### 17. IA retornava medico_id errado
- **Problema**: IA usava ID 2 ao invés de 31 para o Dr. João
- **Causa**: Prompt não mostrava o ID real dos médicos
- **Solução**: Adicionado `[ID: X]` antes do nome de cada médico no prompt
- **Arquivo**: `app/services/anthropic_service.py`
- **Formato**: `- [ID: 31] Dr. João da Silva (Pediatra) - CRM: ...`

### 18. IA perguntava especialidade mesmo com médico único
- **Problema**: Em clínicas com apenas 1 médico, não faz sentido perguntar especialidade
- **Solução**:
  1. Filtrar secretárias da lista de médicos (`is_secretaria = true`)
  2. Adicionar flag `medico_unico` no contexto
  3. Quando médico único: pular pergunta de especialidade, usar ID automaticamente
  4. Quando múltiplos médicos: perguntar normalmente
- **Arquivo**: `app/services/anthropic_service.py`
- **Contexto adicionado no prompt**:
  - Médico único: "NÃO pergunte qual especialidade - use automaticamente o ID X"
  - Múltiplos médicos: "Pergunte para qual especialidade deseja agendar"

### Correções Adicionais (Sessão 28/01/2026 - Tarde)

### 19. Timezone do PostgreSQL alterado para Brasília
- **Problema**: Sistema usava UTC no banco, causando confusão em cálculos de "hoje"
- **Solução**: Alterado timezone do banco para America/Sao_Paulo
- **Comando**: `ALTER DATABASE agendamento_saas SET timezone TO 'America/Sao_Paulo'`
- **Resultado**: Datas armazenadas e comparações agora usam horário de Brasília

### 20. IA não detectava "hoje" e "amanhã" nas mensagens
- **Problema**: Quando paciente dizia "tem horário pra hoje?", a IA não reconhecia
- **Causa**: Código usava `date.today()` que não considera timezone
- **Solução**:
  1. Usar `datetime.now(tz_brazil).date()` com pytz
  2. Detectar palavras: "hoje", "amanhã", "depois de amanhã"
  3. Buscar também no histórico de conversa
- **Arquivo**: `app/services/anthropic_service.py` linhas 115-130

### 21. Dashboard contava agendamentos "remarcados" no total
- **Problema**: Card "Total de Agendamentos" incluía status remarcado/cancelado/faltou
- **Solução**: Filtrar esses status em todas as queries de contagem
- **Arquivos modificados**:
  - `app/api/dashboard.py` - total_agendamentos e consultas
  - `app/api/dashboard_simples.py` - consultas_semana
  - `app/api/financeiro.py` - total e previsto
  - `app/api/admin.py` - estatísticas
- **Filtro adicionado**: `status NOT IN ('cancelado', 'remarcado', 'faltou')`

### 22. Financeiro mostrava R$ 300 ao invés do valor configurado
- **Problema**: Valor da consulta particular era hardcoded como R$ 300
- **Causa**: Webhook usava `valor = 300.00` fixo
- **Solução**:
  1. Adicionado campo `valor_consulta_particular` no modelo Medico
  2. Webhook agora usa `medico.valor_consulta_particular`
- **Arquivos**:
  - `app/models/medico.py` - novo campo `valor_consulta_particular = Column(Numeric(10, 2))`
  - `app/api/webhook_official.py` - usa valor do médico

### 23. Status muda de "agendado" para "confirmado" no lembrete
- **Problema**: Não estava claro quando o status deveria mudar
- **Fluxo implementado**:
  1. Agendamento criado → status = "agendado"
  2. Paciente recebe lembrete 24h/2h com botões "Confirmar" ou "Preciso remarcar"
  3. Ao clicar "Confirmar" ou "Estou a caminho" → status = "confirmado"
- **Arquivo**: `app/services/lembrete_service.py`

### 24. Botão "Estou a caminho" não era reconhecido
- **Problema**: Template de 2h usa botão "Estou a caminho" que não estava mapeado
- **Solução**: Adicionado no BUTTON_ACTIONS
- **Arquivo**: `app/services/button_handler_service.py`
- **Mapeamento**: `"Estou a caminho": "confirmar"`

### 25. IA dizia "horário ocupado" quando estava livre (ex: 13h)
- **Problema**: Paciente pedia 13h, IA dizia "já tem paciente" mesmo estando disponível
- **Causa**: IA ignorava a lista de horários livres fornecida no prompt
- **Solução**: Reforço das regras no prompt com exemplos específicos:
  - "Se 13:00 ESTÁ na lista → Diga que está disponível!"
  - "NUNCA diga ocupado se o horário APARECE na lista de livres"
- **Arquivo**: `app/services/anthropic_service.py`
- **Nota**: 13h estava sendo confundido porque é logo após o almoço (12h-13h)

### 26. Mensagem de confirmação não mencionava lembrete de 2h
- **Problema**: Para consultas no mesmo dia, IA dizia "lembrete 24h antes"
- **Solução**: Regra adaptativa no prompt:
  - Consulta > 24h: "Você receberá lembrete 24h e 2h antes"
  - Consulta hoje: "Como sua consulta é em breve, receberá lembrete 2h antes"
- **Arquivo**: `app/services/anthropic_service.py`

### 27. Mensagem sobre indisponibilidade mais genérica
- **Problema**: IA dizia "já tem paciente" para horário de almoço
- **Solução**: Mudou de "OCUPADO (JÁ TEM PACIENTE)" para "INDISPONÍVEL"
- **Motivo**: Horário pode estar indisponível por: almoço, fora do expediente, bloqueio
- **Arquivo**: `app/services/anthropic_service.py`

### 28. Convênio não salvava forma_pagamento corretamente
- **Problema**: Agendamentos via IA salvavam `tipo_atendimento` mas não `forma_pagamento`
- **Causa**: Webhook não buscava índice do convênio no array `convenios_aceitos`
- **Solução**:
  1. Buscar convênio pelo nome no array do médico
  2. Salvar `forma_pagamento` como `convenio_X` (índice)
  3. Salvar valor do convênio em `valor_consulta`
- **Arquivo**: `app/api/webhook_official.py`
- **Resultado**: Dashboard financeiro agora contabiliza convênios corretamente

### 29. Campo forma_pagamento faltando no modelo Agendamento
- **Problema**: `TypeError: 'forma_pagamento' is an invalid keyword argument`
- **Causa**: Campo existia no banco mas não no modelo SQLAlchemy
- **Solução**: Adicionado `forma_pagamento = Column(String(50), nullable=True)`
- **Arquivo**: `app/models/agendamento.py`

### 30. IA oferecia horários que já passaram
- **Problema**: Às 10:26, IA oferecia "10:00" como opção para hoje
- **Solução**: Filtrar horários passados quando data = hoje
- **Arquivo**: `app/services/agendamento_service.py`
- **Lógica**: `if eh_hoje and hora_atual <= agora + timedelta(minutes=30): continue`
- **Margem**: 30 minutos para evitar agendamentos muito em cima da hora

### 31. Chat do painel mostrava horário em UTC
- **Problema**: Mensagens mostravam 13:26 quando eram 10:26 (3h de diferença)
- **Causa**: Timestamps salvos em UTC (`datetime.utcnow`) sem conversão ao exibir
- **Solução**: Função `converter_para_brasil(dt)` converte UTC → America/Sao_Paulo
- **Arquivos**:
  - `app/api/conversas.py` - API de mensagens
  - `app/api/webhook_official.py` - WebSocket notifications
- **Resultado**: Horários exibidos corretamente no fuso de Brasília

### 32. Motivo da consulta implementado no fluxo
- **Problema**: Campo `motivo_consulta` era preenchido com especialidade do médico
- **Solução**: Novo passo no fluxo de agendamento
- **Fluxo atualizado**:
  1. Nome
  2. Médico (se múltiplos)
  3. **Motivo da consulta** ← NOVO
  4. Data
  5. Horário
  6. Convênio/Particular
  7. Confirmação
- **Opções de motivo**:
  - 🔄 Rotina/Retorno
  - 📋 Levar resultados de exames
  - 🩺 Sintoma específico (registrar qual)
  - 🆕 Primeira consulta
- **Arquivo**: `app/services/anthropic_service.py`
- **Dados coletados**: `motivo_consulta` adicionado ao JSON de resposta

### 33. Lembrete de trazer exames na confirmação
- **Problema**: Paciente não era lembrado de trazer exames
- **Solução**: Adicionar na mensagem de confirmação:
  - "📎 Se tiver exames recentes, traga no dia da consulta!"
- **Arquivo**: `app/services/anthropic_service.py`

### 34. Detecção de paciente novo vs retorno
- **Problema**: IA não sabia se paciente era novo ou tinha histórico
- **Solução**: Verificar quantidade de agendamentos anteriores do paciente
- **Lógica**:
  - `qtd_agendamentos > 0` → "Provavelmente é RETORNO"
  - `qtd_agendamentos == 0` → "Pode ser PRIMEIRA CONSULTA"
  - Paciente não encontrado → "PACIENTE NOVO"
- **Arquivo**: `app/services/anthropic_service.py`

---

## Sistema de Onboarding com Aceite de Termos (Sessão 28/01/2026 - Noite)

### 35. Fluxo completo de onboarding com aceite de termos
- **Objetivo**: Admin/Parceiro cadastra cliente → cliente recebe email → aceita termos → conta ativa
- **Antes**: `POST /api/admin/clientes` criava cliente com `ativo=true` direto
- **Depois**: Cliente criado com `ativo=false`, `status='pendente_aceite'`, token de ativação (7 dias)

#### Migrations Criadas (j01, j02, j03):
- **j01**: Campos de onboarding na tabela `clientes`: `status`, `token_ativacao`, `token_expira_em`, `cadastrado_por_id/tipo`, `aceite_termos_em`, `aceite_ip`, `aceite_user_agent`, `aceite_versao_termos/privacidade`
- **j02**: Tabela `historico_aceites` (registro de todos os aceites de termos)
- **j03**: Campos de autenticação em `parceiros_comerciais`: `senha_hash`, `token_login`, `ultimo_login`

#### Novos Arquivos:
| Arquivo | Descrição |
|---------|-----------|
| `app/models/historico_aceite.py` | Model HistoricoAceite (FK clientes) |
| `app/api/ativacao.py` | API pública de ativação de conta |
| `app/api/parceiro_auth.py` | API do portal do parceiro (login, dashboard, CRUD clientes) |
| `static/ativar-conta.html` | Página de aceite de termos (6 estados) |
| `static/parceiro/login.html` | Login do parceiro |
| `static/parceiro/dashboard.html` | Dashboard com stats e lista de clientes |
| `static/parceiro/novo-cliente.html` | Form de cadastro simplificado |

#### APIs de Ativação (`/api/ativacao/`):
- `POST /api/ativacao/reenviar` — Reenvia email (gera novo token)
- `GET /api/ativacao/{token}` — Retorna dados do cliente (público)
- `POST /api/ativacao/{token}` — Processa aceite e ativa conta

#### APIs do Portal Parceiro (`/api/parceiro/`):
- `POST /api/parceiro/login` — Login com email+senha (bcrypt), retorna JWT
- `GET /api/parceiro/me` — Dados do parceiro logado
- `GET /api/parceiro/dashboard` — Stats: total, por status, comissões
- `GET /api/parceiro/clientes` — Lista clientes do parceiro
- `POST /api/parceiro/clientes` — Criar cliente (fluxo simplificado)
- `POST /api/parceiro/reenviar-ativacao/{id}` — Reenviar email

#### Arquivos Modificados:
- `app/models/cliente.py` — Novos campos + relationship `aceites`
- `app/models/parceiro_comercial.py` — Campos de autenticação
- `app/models/__init__.py` — Export HistoricoAceite
- `app/services/email_service.py` — 3 novos métodos: `send_ativacao_conta()`, `send_boas_vindas_ativacao()`, `send_notificacao_parceiro_ativacao()`
- `app/api/admin_clientes.py` — Onboarding cria com `pendente_aceite`, envia email, resposta inclui `link_ativacao`
- `app/api/parceiros_comerciais.py` — Endpoint `POST /{id}/definir-senha`
- `app/main.py` — Routers de ativação e parceiro registrados
- `app/middleware/tenant_middleware.py` — Bypass para `/api/ativacao/` e `/api/parceiro/`
- `app/middleware/billing_middleware.py` — Rotas liberadas para ativação e parceiro
- `static/admin/clientes-novo.html` — Modal mostra "Ativação Pendente" + link de ativação
- `static/admin/clientes.html` — Badges de status (pendente=amarelo, ativo=verde, suspenso=vermelho), filtro "Pendente Aceite"

#### Status de Cliente:
| Status | Cor Badge | Descrição |
|--------|-----------|-----------|
| `pendente_aceite` | Amarelo | Aguardando aceite de termos |
| `ativo` | Verde | Conta ativa e funcional |
| `aguardando_pagamento` | Laranja | Aguardando primeiro pagamento |
| `suspenso` | Vermelho | Suspenso por inadimplência |
| `cancelado` | Cinza | Conta cancelada |

#### Fluxo Completo:
1. Admin/Parceiro cadastra cliente via painel
2. Sistema cria cliente com `ativo=false`, `status='pendente_aceite'`
3. Gera `token_ativacao` (URL-safe, 64 chars) com expiração de 7 dias
4. Envia email com link: `https://horariointeligente.com.br/static/ativar-conta.html?token=XXX`
5. Cliente acessa link, vê resumo dos dados + 2 checkboxes (Termos v1.0 + Privacidade v1.1)
6. Ao aceitar: `status='ativo'`, `ativo=true`, registra IP/user-agent/versões em `historico_aceites`
7. Envia email de boas-vindas + notifica parceiro (se aplicável)
8. Token é limpo (`token_ativacao=NULL`)

#### Retrocompatibilidade:
- Migration j01 faz `UPDATE clientes SET status='ativo' WHERE ativo=true` e `status='suspenso' WHERE ativo=false`
- Clientes existentes continuam funcionando normalmente

---

## Pendências / Próximos Passos

- [x] ~~Testar criação de novo agendamento com convênio~~ (Funcionando)
- [x] ~~Gráficos do dashboard financeiro renderizando~~ (Corrigido)
- [x] ~~Dados demo atualizados com convênios~~ (Concluído)
- [x] ~~Horários populares com fuso horário correto~~ (Corrigido)
- [x] ~~Indicação visual de horários indisponíveis~~ (Implementado)
- [x] ~~IA consultando horários reais do médico~~ (Implementado)
- [x] ~~Verificação de conflito de horário ao agendar via IA~~ (Implementado)
- [x] ~~Timezone do banco alterado para Brasília~~ (Implementado)
- [x] ~~IA detectando "hoje", "amanhã"~~ (Implementado)
- [x] ~~Dashboard excluindo remarcados/cancelados~~ (Corrigido)
- [x] ~~Valor consulta particular do médico~~ (Implementado)
- [x] ~~Fluxo agendado → confirmado~~ (Implementado)
- [x] ~~Botão "Estou a caminho"~~ (Mapeado)
- [x] ~~IA reconhecendo 13h como disponível~~ (Corrigido)
- [x] ~~Lembrete 2h para consultas do dia~~ (Implementado)
- [x] ~~Convênio salvando forma_pagamento~~ (Corrigido)
- [x] ~~Filtrar horários passados para hoje~~ (Implementado)
- [x] ~~Chat do painel com horário correto~~ (Corrigido UTC→BRT)
- [x] ~~Motivo da consulta no fluxo~~ (Implementado)
- [x] ~~Detecção paciente novo vs retorno~~ (Implementado)
- [x] ~~Onboarding com aceite de termos~~ (Implementado)
- [x] ~~Portal do parceiro (login, dashboard, CRUD)~~ (Implementado)
- [x] ~~Página de ativação de conta~~ (Implementado)
- [x] ~~Email de ativação + boas-vindas~~ (Implementado)
- [x] ~~Status badges no painel admin~~ (Implementado)
- [x] ~~Navegação unificada (top nav desktop + bottom nav mobile)~~ (Implementado)
- [x] ~~Calibrar IA: lembrete de 24h na confirmação de presença~~ (Corrigido)
- [x] ~~Calibrar IA: "lotado" vs "não atende nesse dia"~~ (Corrigido)
- [x] ~~Modal de cancelamento com motivos + notificação WhatsApp~~ (Implementado)
- [x] ~~Motivo e notificação WhatsApp no reagendamento~~ (Implementado)
- [x] ~~Templates WhatsApp registrados no painel de conversas~~ (Implementado)
- [x] ~~Horários não desapareciam ao trocar data no reagendamento~~ (Corrigido)
- [x] ~~IA não reconhecia datas curtas (DD/MM, D/M)~~ (Corrigido)
- [x] ~~Exibir nomes de pacientes e telefones formatados na sidebar de conversas~~ (Implementado)
- [ ] Calibrar empatia da IA (não usar emojis em situações de dor/urgência)
- [ ] Validar exibição do nome do convênio no modal de detalhes
- [ ] Definir senha para parceiros existentes via admin
- [ ] Testar fluxo completo: admin cria → email chega → aceitar → conta ativa

---

## Correções Realizadas (Sessão 29/01/2026)

### 36. Navegação Unificada — Top Nav (Desktop) + Bottom Nav (Mobile)
- **Problema**: Cada página HTML tinha seu próprio header/nav inline com lógica duplicada de logout, menu mobile, navegação de secretária, etc. Manutenção difícil e comportamento inconsistente entre páginas.
- **Solução**: Criados 2 componentes JS centralizados que gerenciam toda a navegação do sistema.

#### Novos Arquivos:
| Arquivo | Descrição |
|---------|-----------|
| `static/js/components/top-nav.js` | `HiTopNav` — Barra de navegação superior para desktop (>= 1024px). Sticky, 56px, com logo, links de navegação, nome do usuário e botão de sair. Suporta badges, dark mode e acessibilidade (ARIA). |
| `static/js/components/nav-init.js` | `HiNavInit` — Inicializador que configura `HiTopNav` (desktop) + `HiBottomNav` (mobile) com itens baseados no perfil do usuário (médico vs secretária). Inclui menu overflow "Mais" no mobile com animação. |

#### Navegação por Perfil:
| Perfil | Desktop (Top Nav) | Mobile (Bottom Nav) |
|--------|-------------------|---------------------|
| **Médico** | Painel, Agenda, Conversas, Configurações, Perfil | Agenda, Conversas, **Novo** (FAB), Config, Mais (...) |
| **Secretária** | Agenda, Conversas | Agenda, Conversas, **Novo** (FAB), Config, Senha |

- **Menu "Mais" (mobile médico)**: Painel, Perfil, separador, Sair — com backdrop animado e menu popup

#### Arquivos Modificados (8 páginas HTML):
| Arquivo | Mudanças |
|---------|----------|
| `static/calendario-unificado.html` | Removidos: header inline (~110 linhas), breadcrumb, `configurarNavegacaoSecretaria()`, `toggleMobileMenu()`, `logout()`, config inline do `HiBottomNav`. Adicionado: `HiNavInit.init({ activeId: 'agenda', onNewAppointment: ... })`. Null checks em `userName`. |
| `static/configuracao-agenda.html` | Substituída config inline do `HiBottomNav` por `HiNavInit.init({ activeId: 'config' })`. |
| `static/configuracoes.html` | Removidos: header/nav inline (~30 linhas), `logout()`, botões de navegação para secretária. Adicionado: `HiNavInit.init({ activeId: 'config' })`. Null checks em `userName`. |
| `static/conversas.html` | Removidos: header completo com links de navegação (~60 linhas), switching médico/secretária, `logout()`. Substituído por barra compacta de stats (48px). Adicionado: `HiNavInit.init({ activeId: 'conversas' })`. |
| `static/dashboard-v2.html` | Removidos: header inline (~33 linhas), `logout()`. Adicionado: `HiNavInit.init({ activeId: 'dashboard' })`. Null check em `userName`. |
| `static/dashboard.html` | Removidos: header inline (~40 linhas), `logout()`. Badge de conversas agora usa `HiTopNav.setBadge()` e `HiBottomNav.setBadge()`. Adicionado: `HiNavInit.init({ activeId: 'dashboard' })`. |
| `static/minha-agenda.html` | Removidos: header/nav inline (~25 linhas), `logout()`. Adicionado: `HiNavInit.init({ activeId: 'config' })`. Null check em `userName`. |
| `static/perfil.html` | Removido: header inline (~18 linhas). Substituída config inline do `HiBottomNav` por `HiNavInit.init({ activeId: 'perfil' })`. |

#### Impacto:
- **Redução de código**: ~522 linhas removidas, ~119 adicionadas (net -403 linhas)
- **Logout centralizado**: Função `logout()` removida de todas as páginas — agora tratada pelos componentes de navegação
- **Null checks**: Referências a `document.getElementById('userName')` agora verificam se o elemento existe, já que o header inline foi removido
- **Consistência**: Todas as páginas agora compartilham o mesmo comportamento de navegação
- **Uso**: `HiNavInit.init({ activeId: 'pagina' })` — uma única chamada configura desktop + mobile

#### Backup:
- `static/index.html.bak_20260128` — Backup do index.html antes das mudanças

### 37. IA mencionava lembrete de 24h ao confirmar presença
- **Problema**: Quando paciente confirmava presença (respondendo ao lembrete de 24h), a IA dizia "Você receberá um lembrete 24h antes e outro 2h antes" — mas o de 24h já tinha sido enviado
- **Causa**: Regra de lembretes no prompt não distinguia entre criar novo agendamento e confirmar presença em um existente
- **Solução**: Regra reformulada com 3 cenários:
  1. **Confirmando presença** → NÃO mencionar lembrete de 24h (já recebeu). Só mencionar o de 2h se faltar mais de 2h para a consulta
  2. **Novo agendamento > 24h** → Mencionar ambos os lembretes
  3. **Novo agendamento < 24h** → Mencionar só o de 2h
- **Arquivo**: `app/services/anthropic_service.py:545-550`

### 38. IA dizia "agenda lotada" quando médico não atende no dia
- **Problema**: Paciente pedia data em dia que o médico não atende (ex: quinta-feira), e a IA respondia "agenda completamente lotada" — quando na verdade o médico simplesmente não trabalha nesse dia
- **Causa**: Quando `obter_horarios_disponiveis()` retornava lista vazia, o prompt sempre dizia "DIA LOTADO" sem verificar se o médico atende naquele dia da semana
- **Solução**: Antes de declarar "lotado", verifica os `dias_atendimento` do médico contra o dia da semana solicitado:
  - **Médico não atende no dia** → "O dia 26/02 é quinta-feira e o Dr. João não atende nesse dia. Ele atende às segundas, quartas e sextas."
  - **Médico atende mas sem vagas** → "A agenda está lotada para esta data"
- **Arquivo**: `app/services/anthropic_service.py:268-315`
- **Lógica**: Busca `medico_info` no `contexto_clinica`, extrai `dias_atendimento` da `disponibilidade`, normaliza e compara com o dia da semana da data pedida

### 39. Modal de cancelamento e motivo no reagendamento + notificação WhatsApp
- **Problema**: "Cancelar Consulta" usava `prompt()` nativo do browser (feio); "Reagendar" não pedia motivo; nenhum dos dois notificava o paciente via WhatsApp
- **Solução**:
  1. **Novo modal de cancelamento** (`#modalCancelamento`): select com motivos predefinidos (Paciente solicitou, Médico indisponível, etc.), input "Outro", checkbox "Notificar via WhatsApp" (checked por padrão)
  2. **Campos novos no modal de reagendamento**: select de motivo (opcional), input "Outro", checkbox WhatsApp
  3. **Backend PUT** (reagendar): `motivo_reagendamento` salvo em `observacoes`; envia template `consulta_reagendada_clinica` ao paciente se checkbox marcado
  4. **Backend DELETE** (cancelar): parâmetro `notificar_paciente`; envia template `consulta_cancelada_clinica` ao paciente se checkbox marcado
  5. **Registro na conversa**: Após envio WhatsApp com sucesso, mensagem salva no painel de conversas via `ConversaService.adicionar_mensagem()` (remetente=SISTEMA)
  6. **Toast de feedback**: Indica se paciente foi notificado via WhatsApp ou se houve falha
- **Arquivos modificados**:
  - `app/api/agendamentos.py` — Schema `AgendamentoUpdate` (+`motivo_reagendamento`, `notificar_paciente`), PUT e DELETE com envio de templates e registro na conversa
  - `static/calendario-unificado.html` — Modal cancelamento, campos motivo/checkbox no reagendamento, JS atualizado
- **Templates WhatsApp usados** (já aprovados pela Meta):
  - `consulta_reagendada_clinica` (paciente, medico, data_antiga, hora_antiga, data_nova, hora_nova)
  - `consulta_cancelada_clinica` (paciente, medico, data, hora, motivo)

### 40. Horários não desapareciam ao trocar data no reagendamento
- **Problema**: No modal de reagendamento, ao trocar de uma data com horários para uma sem horários (médico não atende), os horários antigos continuavam visíveis
- **Causa**: Função `verificarHorariosDisponiveisReagendamento()` só tinha lógica para *mostrar* horários, faltava `else` para esconder quando a API retornava lista vazia
- **Solução**: Adicionado bloco `else` que esconde o container, limpa a lista e reseta o campo de hora; tratamento no `catch` também esconde os horários
- **Arquivo**: `static/calendario-unificado.html`

### 41. IA não reconhecia datas no formato curto (DD/MM ou D/M)
- **Problema**: Paciente escrevia "03/2" (3 de fevereiro), e a IA não reconhecia — inventava o dia da semana e oferecia horários sem verificar o banco
- **Causa**: Parser de datas só reconhecia formato completo `DD/MM/YYYY` (regex `\d{2}/\d{2}/\d{4}`). Formatos curtos como `03/2`, `3/02`, `15/3` não eram capturados
- **Consequência**: Sem a data parseada, a função `_extrair_data_e_horarios_disponiveis()` retornava vazia. A IA não recebia horários disponíveis nem o alerta de "dia sem atendimento", ficando às cegas
- **Solução**: Adicionado segundo parser com regex `(?<!\d)(\d{1,2})/(\d{1,2})(?!/|\d)` que:
  1. Captura formatos: `D/M`, `DD/M`, `D/MM`, `DD/MM`
  2. Não captura `DD/MM/YYYY` (lookahead negativo impede)
  3. Infere o ano automaticamente: se a data já passou no ano atual, usa o próximo ano
- **Arquivo**: `app/services/anthropic_service.py:113-130`
- **Resultado**: "03/2" agora é corretamente parseado como 03/02/2026 (terça-feira), e o sistema injeta no prompt o alerta de "DIA SEM ATENDIMENTO" quando aplicável

---

## Observações Técnicas

### Fuso Horário
- **Banco de dados**: America/Sao_Paulo (BRT, UTC-3)
- **Exibição para usuário**: America/Sao_Paulo (BRT, UTC-3)
- **Código Python**: Usar `datetime.now(pytz.timezone('America/Sao_Paulo'))`

### Forma de Pagamento
- `'particular'` → Consulta particular
- `'convenio_0'` → Primeiro convênio do array `convenios_aceitos` do médico
- `'convenio_1'` → Segundo convênio do array
- Para obter o nome: `medicos.convenios_aceitos[índice].nome`

### Onboarding / Ativação
- **Token**: `secrets.token_urlsafe(64)` — URL-safe, 64 chars
- **Expiração**: 7 dias
- **Versões termos**: `VERSAO_TERMOS = "1.0"`, `VERSAO_PRIVACIDADE = "1.1"` (em `app/api/ativacao.py`)
- **Parceiro auth**: JWT com `SECRET_KEY`, expira em 24h
- **Definir senha parceiro**: `POST /api/interno/parceiros/{id}/definir-senha`

---

### Navegação Unificada
- **Desktop (>= 1024px)**: `HiTopNav` — barra superior sticky, 56px
- **Mobile (< 1024px)**: `HiBottomNav` — barra inferior fixa com FAB central
- **Inicialização**: `HiNavInit.init({ activeId: 'pagina' })` — configura ambas automaticamente
- **Perfis**: Itens de menu variam por perfil (médico vs secretária)
- **Componentes**: `static/js/components/top-nav.js`, `static/js/components/nav-init.js`, `static/js/components/bottom-nav.js`

## Correções Realizadas (Sessão 30/01/2026)

### 42. Cláusula de prazo de 72h para ativação nos Termos de Uso
- **Problema**: Os termos não informavam que a ativação da conta não é imediata após o aceite
- **Motivo**: Configurações técnicas e aprovações de templates pela Meta (WhatsApp Business API) exigem prazo
- **Solução**: Adicionada cláusula e ajustes em múltiplos arquivos
- **Alterações**:
  1. **Novo item 5.4 (Prazo de Ativação)** na Seção 5 do `static/termos-de-uso.html` — informa prazo de 72h úteis com justificativa técnica (aprovações Meta)
  2. **Seção de Aceitação** atualizada com referência à Seção 5.4
  3. **Versão dos termos** atualizada de 1.0 para 1.1; data de vigência para 30/01/2026
  4. **`app/api/ativacao.py`** — `VERSAO_TERMOS` de "1.0" para "1.1"
  5. **`static/ativar-conta.html`** — versão atualizada no checkbox, aviso informativo de 72h antes do botão de aceite, mensagem de sucesso ajustada ("Termos Aceitos com Sucesso" ao invés de "Conta Ativada")

### 43. Exibição de nomes e telefones formatados na sidebar de conversas
- **Problema**: Lista de conversas exibia telefones crus (ex: `5524988493257`) quando `paciente_nome` era NULL na tabela `conversas`. O nome existia na tabela `pacientes` mas não era aproveitado. Mesmo como fallback, o telefone não era formatado.
- **Solução**: Duas mudanças complementares (backend + frontend):

#### Backend (`app/api/conversas.py`):
1. **Import**: `from app.utils.phone_utils import format_phone_display`
2. **Schema**: Adicionado campo `paciente_telefone_formatado: Optional[str] = None` em `ConversaResponse`
3. **`listar_conversas`**: Busca nomes de pacientes da tabela `pacientes` (por telefone + cliente_id) para conversas sem `paciente_nome`. Usa `mapa_nomes` para enriquecer o campo. Adiciona `paciente_telefone_formatado` via `format_phone_display()`
4. **`get_conversa`**: Mesma lógica de enriquecimento para a view de detalhe (usada no header do chat)

#### Frontend (`static/conversas.html`):
1. **Sidebar — nome**: Fallback chain: `paciente_nome || paciente_telefone_formatado || paciente_telefone`
2. **Sidebar — subtítulo**: Quando paciente tem nome, exibe telefone formatado abaixo em cinza (`text-xs text-gray-400`)
3. **Busca**: Filtro agora inclui `paciente_telefone_formatado` para busca por telefone formatado (ex: `(24) 98849`)
4. **Header do chat**: Nome e telefone usam versão formatada

#### Resultado:
- Conversas exibem nome do paciente mesmo quando `paciente_nome` é NULL na conversa (busca da tabela `pacientes`)
- Telefones formatados como `+55 (24) 98849-3257` ao invés de `5524988493257`
- Busca funciona tanto por telefone cru quanto formatado

---

### 44. Renomeação de referências ProSaude → Horário Inteligente
- **Problema**: Sistema nasceu como "ProSaude" mas agora se chama "Horário Inteligente". Referências ao nome antigo persistiam no código, config, scripts e docs
- **Solução**: Renomeação completa em todo o codebase
- **Alterações**:
  1. **`app/middleware/tenant_middleware.py`** — Default de desenvolvimento: `prosaude` → `drjoao` (cliente real ID 11)
  2. **`.env`** — `WHATSAPP_PROVIDER=official`, Evolution API comentada como legado
  3. **Serviços Evolution (legado)** — `"ProSaude"` → `"HorarioInteligente"` em reminder_service, notification_service, falta_service, whatsapp_monitor
  4. **`app/services/whatsapp_service.py`** — API key hardcoded → `os.getenv("EVOLUTION_API_KEY", "")`
  5. **`scripts/seed_prosaude.py`** → renomeado para `scripts/seed_clinica_teste.py` com dados atualizados
  6. **`scripts/populate_demo_data.py`** — subdomain `prosaude` → `drjoao`
  7. **Systemd** — `prosaude.service` → `horariointeligente.service`
  8. **Documentação** — continuidade.md, README.md e demais .md atualizados
- **Nota**: Evolution API é código legado; sistema usa apenas API Oficial Meta

### 45. Remoção de referências a "lançamento" na landing page
- **Problema**: Textos na landing page e demo ainda diziam "quando lançarmos", "pré-lançamento", etc., mas o sistema já está em produção
- **Solução**: Atualização de textos para refletir que o produto já foi lançado
- **Alterações**:
  1. **`static/index.html`** — "OFERTA EXCLUSIVA DE LANÇAMENTO" → "OFERTA EXCLUSIVA"; removido "quando lançarmos"; checkbox sem "sobre o lançamento"; mensagem de sucesso sem "lista VIP" e "em breve"
  2. **`static/demo/index.html`** — "preço especial de lançamento" → "condições especiais"; checkbox e alerta atualizados
  3. **`static/admin/pre-cadastros.html`** — "Leads do Pré-Lançamento" → "Leads e interessados"
  4. **`static/admin/dashboard.html`** — "Leads de lançamento" → "Leads e interessados"

---

*Última atualização: 30/01/2026 - Remoção de referências a lançamento na landing page*
