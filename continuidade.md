# Documento de Continuidade - Sistema de Agendamento

## Visão Geral
Sistema de agendamento médico multi-tenant (SaaS) chamado **Horário Inteligente** / **ProSaude**.

- **Stack**: FastAPI (Python) + PostgreSQL + HTML/JS (Tailwind CSS)
- **Serviço**: `prosaude.service` (systemd)
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
systemctl restart prosaude.service

# Ver status
systemctl status prosaude.service

# Logs em tempo real
journalctl -u prosaude.service -f

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

## Pendências / Próximos Passos

- [x] ~~Testar criação de novo agendamento com convênio~~ (Funcionando)
- [x] ~~Gráficos do dashboard financeiro renderizando~~ (Corrigido)
- [x] ~~Dados demo atualizados com convênios~~ (Concluído)
- [x] ~~Horários populares com fuso horário correto~~ (Corrigido)
- [ ] Validar exibição do nome do convênio no modal de detalhes

---

## Observações Técnicas

### Fuso Horário
- **Banco de dados**: UTC (Etc/UTC)
- **Exibição para usuário**: America/Sao_Paulo (BRT, UTC-3)
- **Queries de horário**: Usar `AT TIME ZONE 'America/Sao_Paulo'`

### Forma de Pagamento
- `'particular'` → Consulta particular
- `'convenio_0'` → Primeiro convênio do array `convenios_aceitos` do médico
- `'convenio_1'` → Segundo convênio do array
- Para obter o nome: `medicos.convenios_aceitos[índice].nome`

---

*Última atualização: 27/01/2026 21:30*
