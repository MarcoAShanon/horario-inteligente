# Configuração de Agenda do Médico - ProSaúde

**Data:** 28 de novembro de 2025
**Autor:** Marco com assistência do Claude Code
**Versão:** 2.3.1

## 📋 Resumo

Sistema completo para que médicos possam configurar seus horários de atendimento, tempo de consulta e dias disponíveis de forma independente e flexível.

---

## 🎯 Funcionalidades

### 1. **Tempo Padrão de Consulta** ⏱️

O médico pode escolher a duração padrão de cada consulta:

**Opções disponíveis:**
- ⏱️ **15 minutos** - Consultas rápidas
- ⏱️ **20 minutos** - Atendimento ágil
- ⏱️ **30 minutos** - Padrão recomendado
- ⏱️ **45 minutos** - Consultas detalhadas
- ⏱️ **1 hora** - Atendimentos especializados
- ⏱️ **1 hora e 30 minutos** - Procedimentos
- ⏱️ **2 horas** - Consultas extensas

**Como funciona:**
- Define automaticamente os slots de horário no calendário
- Exemplo: 30 min → horários disponíveis: 08:00, 08:30, 09:00, 09:30...

---

### 2. **Horário de Atendimento** 🕐

Configure início e fim do expediente:

**Configurações:**
- **Horário de início:** 06:00 até 23:30 (intervalos de 30 min)
- **Horário de fim:** 06:30 até 23:30 (intervalos de 30 min)
- **Intervalo de almoço:**
  - Início: 12:00 (padrão)
  - Fim: 13:00 (padrão)
  - Pode ser desabilitado

**Exemplo:**
```
Início: 08:00
Fim: 18:00
Almoço: 12:00 - 13:00

Resultado:
- Manhã: 08:00 às 12:00
- Tarde: 13:00 às 18:00
```

---

### 3. **Dias de Atendimento** 📅

Selecione quais dias da semana você atende:

**Opções:**
- ☐ Segunda-feira
- ☐ Terça-feira
- ☐ Quarta-feira
- ☐ Quinta-feira
- ☐ Sexta-feira
- ☐ Sábado
- ☐ Domingo

**Recursos:**
- ✅ Seleção múltipla
- ✅ Visual com toggle switches
- ✅ Pode atender todos os dias ou só alguns

---

### 4. **Configurações Avançadas** ⚙️

**Tempo antes da consulta:**
- Tempo de preparação entre consultas
- Padrão: 5 minutos
- Evita sobrecarga do médico

**Consultas simultâneas:**
- Número de pacientes atendidos ao mesmo tempo
- Padrão: 1 (um paciente por vez)
- Útil para clínicas com equipes

---

## 🖥️ Interface do Sistema

### Acesso à Configuração

**Pelo Calendário:**
1. Faça login no sistema
2. No calendário, clique no botão **"Configurações"** (ícone de engrenagem)
3. Será redirecionado para a página de configuração

**URL Direta:**
```
http://localhost:8000/static/configuracao-agenda.html
```

---

### Layout da Interface

```
┌─────────────────────────────────────────────────────────────┐
│  🏥 Configuração de Agenda                    👤 Dr. Marco   │
│  Configure os intervalos e horários          [Voltar]       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ ⏱️ Tempo de Consulta  │  │ 📅 Horários           │        │
│  │                       │  │                       │        │
│  │ [ 30 minutos ▼ ]     │  │ Início: [08:00 ▼]    │        │
│  │                       │  │ Fim:    [18:00 ▼]    │        │
│  │                       │  │                       │        │
│  │                       │  │ Almoço:               │        │
│  │                       │  │ Início: [12:00 ▼]    │        │
│  │                       │  │ Fim:    [13:00 ▼]    │        │
│  └──────────────────────┘  └──────────────────────┘        │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📆 Dias de Atendimento                                │   │
│  │                                                        │   │
│  │  [✓] Segunda   [✓] Terça    [✓] Quarta              │   │
│  │  [✓] Quinta    [✓] Sexta    [ ] Sábado              │   │
│  │  [ ] Domingo                                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 👁️ Preview dos Horários                               │   │
│  │                                                        │   │
│  │  08:00  08:30  09:00  09:30  10:00  10:30           │   │
│  │  11:00  11:30  13:00  13:30  14:00  14:30           │   │
│  │  15:00  15:30  16:00  16:30  17:00  17:30           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│                              [💾 Salvar Configurações]       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 APIs Backend

### 1. Obter Opções de Configuração

```http
GET /api/configuracao/opcoes-intervalo
```

**Resposta:**
```json
{
  "opcoes_intervalo": [
    {"valor": 15, "texto": "15 minutos"},
    {"valor": 20, "texto": "20 minutos"},
    {"valor": 30, "texto": "30 minutos"},
    {"valor": 45, "texto": "45 minutos"},
    {"valor": 60, "texto": "1 hora"},
    {"valor": 90, "texto": "1 hora e 30 minutos"},
    {"valor": 120, "texto": "2 horas"}
  ],
  "dias_semana": [
    {"valor": 1, "texto": "Segunda-feira"},
    {"valor": 2, "texto": "Terça-feira"},
    ...
  ],
  "horarios_padrao": [
    {"valor": "08:00", "texto": "08:00"},
    {"valor": "08:30", "texto": "08:30"},
    ...
  ]
}
```

### 2. Obter Configuração do Médico

```http
GET /api/configuracao/intervalos/{medico_id}
```

**Resposta:**
```json
{
  "id": 1,
  "medico_id": 1,
  "medico_nome": "Dr. Marco Aurélio",
  "intervalo_consulta": 30,
  "horario_inicio": "08:00",
  "horario_fim": "18:00",
  "dias_atendimento": [1, 2, 3, 4, 5],
  "intervalo_almoco_inicio": "12:00",
  "intervalo_almoco_fim": "13:00",
  "tempo_antes_consulta": 5,
  "consultas_simultaneas": 1,
  "ativo": true
}
```

### 3. Salvar Configuração

```http
POST /api/configuracao/intervalos
Content-Type: application/json

{
  "medico_id": 1,
  "intervalo_consulta": 30,
  "horario_inicio": "08:00",
  "horario_fim": "18:00",
  "dias_atendimento": [1, 2, 3, 4, 5],
  "intervalo_almoco_inicio": "12:00",
  "intervalo_almoco_fim": "13:00",
  "tempo_antes_consulta": 5,
  "consultas_simultaneas": 1
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Configuração salva com sucesso!",
  "configuracao": {
    "id": 1,
    "medico_id": 1,
    ...
  }
}
```

**Validações:**
- Intervalo de consulta: entre 15 e 240 minutos
- Pelo menos 1 dia de atendimento selecionado
- Horário de fim deve ser maior que início

---

## 🎯 Como Usar

### Passo 1: Acessar Configurações
1. Faça login no sistema
2. No calendário, clique em **"Configurações"**
3. Ou acesse diretamente: `/static/configuracao-agenda.html`

### Passo 2: Definir Tempo de Consulta
1. No campo "Duração da Consulta"
2. Selecione uma das opções:
   - 15, 20, 30, 45, 60, 90 ou 120 minutos
3. Visualize o preview dos horários gerados

### Passo 3: Configurar Horários
1. **Horário de Início:** Ex: 08:00
2. **Horário de Fim:** Ex: 18:00
3. **Intervalo de Almoço (opcional):**
   - Início: 12:00
   - Fim: 13:00

### Passo 4: Selecionar Dias
1. Clique nos dias da semana que você atende
2. Switches ficam verdes quando selecionados
3. Mínimo: 1 dia

### Passo 5: Salvar
1. Clique em **"Salvar Configurações"**
2. Aguarde a confirmação: ✅ "Configuração salva com sucesso!"
3. As mudanças entram em vigor imediatamente

---

## 📊 Exemplos Práticos

### Exemplo 1: Clínico Geral - Atendimento Padrão

```yaml
Tempo de consulta: 30 minutos
Horário: 08:00 às 18:00
Dias: Segunda a Sexta
Almoço: 12:00 às 13:00

Resultado:
- 8 horas de atendimento/dia
- 1 hora de almoço
- 7 horas úteis
- 14 consultas/dia
- 70 consultas/semana
```

### Exemplo 2: Pediatra - Consultas Rápidas

```yaml
Tempo de consulta: 20 minutos
Horário: 07:00 às 19:00
Dias: Segunda a Sábado
Almoço: 12:00 às 13:00

Resultado:
- 12 horas de expediente
- 11 horas úteis
- 33 consultas/dia
- 198 consultas/semana
```

### Exemplo 3: Psicólogo - Sessões Longas

```yaml
Tempo de consulta: 1 hora
Horário: 09:00 às 18:00
Dias: Segunda a Sexta
Almoço: Sem intervalo fixo

Resultado:
- 9 horas de atendimento
- 9 sessões/dia
- 45 sessões/semana
```

### Exemplo 4: Plantão - Fim de Semana

```yaml
Tempo de consulta: 15 minutos
Horário: 08:00 às 20:00
Dias: Sábado e Domingo
Almoço: 12:00 às 13:00

Resultado:
- 12 horas de expediente
- 11 horas úteis
- 44 consultas/dia
- 88 consultas/fim de semana
```

---

## 🔒 Segurança

**Autenticação:**
- ✅ Requer login com JWT
- ✅ Apenas o médico pode alterar suas configurações
- ✅ Token validado a cada requisição

**Validações:**
- ✅ Tempo de consulta entre 15-240 minutos
- ✅ Horário fim > horário início
- ✅ Mínimo 1 dia de atendimento
- ✅ Dados sanitizados no backend

---

## 📂 Arquivos do Sistema

```
sistema_agendamento/
├── static/
│   ├── configuracao-agenda.html       # Interface de configuração (ATUALIZADO)
│   └── calendario-unificado.html      # Calendário com botão de config (ATUALIZADO)
│
├── app/api/
│   └── configuracao.py                # APIs de configuração
│
├── app/models/
│   └── configuracoes.py               # Model ConfiguracoesMedico
│
└── CONFIGURACAO_AGENDA_MEDICO.md     # Esta documentação (NOVO)
```

---

## 🆕 Melhorias Implementadas (v2.3.1)

**Interface:**
- ✅ Adicionada autenticação JWT
- ✅ Exibição do nome do médico logado
- ✅ Botão "Voltar ao Calendário"
- ✅ Proteção contra acesso não autenticado

**Calendário:**
- ✅ Botão "Configurações" no header
- ✅ Acesso direto à página de configuração
- ✅ Visual com ícone de engrenagem

**Segurança:**
- ✅ Verificação de token ao carregar
- ✅ Redirecionamento automático se não logado
- ✅ ID do médico obtido do usuário logado

---

## 🧪 Como Testar

### Teste 1: Acessar Interface
```
1. Acesse: http://localhost:8000/static/login.html
2. Login: admin@prosaude.com / admin123
3. Clique no botão "Configurações"
4. Deve abrir a página de configuração
```

### Teste 2: Configurar Horários
```
1. Selecione: 30 minutos
2. Horário: 08:00 às 18:00
3. Dias: Segunda a Sexta
4. Clique em "Salvar"
5. Deve mostrar: ✅ Configuração salva com sucesso!
```

### Teste 3: Ver Preview
```
1. Altere o tempo de consulta para 20 minutos
2. Observe o preview dos horários mudar automaticamente
3. Mais slots devem aparecer
```

### Teste 4: API
```bash
# Obter opções
curl http://localhost:8000/api/configuracao/opcoes-intervalo

# Obter configuração
curl http://localhost:8000/api/configuracao/intervalos/1

# Salvar (requer autenticação)
curl -X POST http://localhost:8000/api/configuracao/intervalos \
  -H "Content-Type: application/json" \
  -d '{
    "medico_id": 1,
    "intervalo_consulta": 30,
    "horario_inicio": "08:00",
    "horario_fim": "18:00",
    "dias_atendimento": [1,2,3,4,5]
  }'
```

---

## ✅ Status

- ✅ **Interface:** Completa e funcional
- ✅ **APIs:** Implementadas e testadas
- ✅ **Autenticação:** Protegida com JWT
- ✅ **Validações:** Backend e frontend
- ✅ **Preview:** Tempo real
- ✅ **Integração:** Link no calendário

**Sistema 100% pronto para uso!** 🚀

---

**Documentação criada em:** 28 de novembro de 2025
**Versão do sistema:** 2.3.1
**Status:** ✅ Funcional e em Produção
