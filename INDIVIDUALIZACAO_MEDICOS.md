# Individualização de Configurações por Médico - Horário Inteligente

**Data:** 28 de novembro de 2025
**Desenvolvedor:** Marco (com assistência de Claude Code)
**Versão do Sistema:** 2.4.0

---

## 📋 Resumo

Sistema de configuração individualizada por médico implementado com sucesso! Agora cada médico pode ter:
- ✅ **Duração de consulta personalizada** (15, 20, 30, 45, 60, 90, 120 minutos)
- ✅ **Horários semanais detalhados** (múltiplos períodos por dia)
- ✅ **Intervalo de almoço personalizado**
- ✅ **Configurações individuais de agendamento**

---

## 🗄️ Estrutura do Banco de Dados

### Tabelas Utilizadas

#### 1. `configuracoes_medico`
Configurações gerais individualizadas por médico.

**Campos principais:**
- `medico_id` - ID único do médico (FK)
- `intervalo_consulta` - Duração da consulta em minutos
- `horario_inicio` - Horário padrão de início
- `horario_fim` - Horário padrão de fim
- `dias_atendimento` - Array JSON com dias da semana
- `intervalo_almoco_inicio` - Início do intervalo de almoço
- `intervalo_almoco_fim` - Fim do intervalo de almoço
- `tempo_antes_consulta` - Tempo de preparação (minutos)
- `consultas_simultaneas` - Número de consultas simultâneas permitidas
- `antecedencia_minima` - Antecedência mínima para agendamento (minutos)
- `antecedencia_maxima` - Antecedência máxima para agendamento (horas)

#### 2. `horarios_atendimento`
Horários semanais detalhados por médico.

**Características:**
- **Múltiplos períodos por dia** - Ex: Segunda 8h-12h E 14h-18h
- **Individualizado por médico** - Cada médico tem seus próprios horários
- **Ativar/Desativar** - Controle de status sem deletar

**Campos:**
- `id` - ID único do horário
- `medico_id` - ID do médico (FK)
- `dia_semana` - Dia da semana (1=Segunda, 2=Terça, ..., 7=Domingo)
- `hora_inicio` - Hora de início (TIME)
- `hora_fim` - Hora de fim (TIME)
- `ativo` - Status do horário (boolean)
- `created_at` - Data de criação

**Validações:**
- ✅ Não permite sobreposição de horários no mesmo dia
- ✅ Hora início deve ser menor que hora fim
- ✅ Formato de hora validado (HH:MM)

---

## 🔗 APIs Implementadas

### Configurações Gerais

#### `GET /api/configuracao/intervalos/{medico_id}`
Retorna as configurações gerais de um médico.

**Resposta:**
```json
{
  "id": 1,
  "medico_id": 1,
  "medico_nome": "Dra. Tânia Maria",
  "intervalo_consulta": 60,
  "horario_inicio": "08:00",
  "horario_fim": "18:00",
  "dias_atendimento": [2, 4, 5],
  "intervalo_almoco_inicio": "12:00",
  "intervalo_almoco_fim": "13:00",
  "tempo_antes_consulta": 5,
  "consultas_simultaneas": 1,
  "ativo": true
}
```

#### `POST /api/configuracao/intervalos`
Cria ou atualiza as configurações gerais de um médico.

**Requisição:**
```json
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

**Validações:**
- Intervalo deve estar entre 15 e 240 minutos
- Deve selecionar pelo menos 1 dia de atendimento

---

### Horários Semanais Detalhados

#### `GET /api/configuracao/horarios-semanais/{medico_id}`
Lista todos os horários semanais de um médico.

**Resposta:**
```json
[
  {
    "id": 6,
    "medico_id": 1,
    "medico_nome": "Dra. Tânia Maria",
    "dia_semana": 1,
    "dia_semana_nome": "Segunda-feira",
    "hora_inicio": "08:00",
    "hora_fim": "12:00",
    "ativo": true
  },
  {
    "id": 7,
    "medico_id": 1,
    "medico_nome": "Dra. Tânia Maria",
    "dia_semana": 1,
    "dia_semana_nome": "Segunda-feira",
    "hora_inicio": "14:00",
    "hora_fim": "18:00",
    "ativo": true
  }
]
```

#### `POST /api/configuracao/horarios-semanais`
Cria um novo horário semanal para o médico.

**Requisição:**
```json
{
  "medico_id": 1,
  "dia_semana": 1,
  "hora_inicio": "08:00",
  "hora_fim": "12:00",
  "ativo": true
}
```

**Validações:**
- ✅ Dia da semana entre 1 e 7
- ✅ Formato de hora válido (HH:MM)
- ✅ Hora início < Hora fim
- ✅ **Validação de conflito** - Não permite sobreposição de horários

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Horário criado com sucesso para Segunda-feira",
  "horario_id": 6,
  "horario": {
    "id": 6,
    "dia_semana": 1,
    "dia_semana_nome": "Segunda-feira",
    "hora_inicio": "08:00",
    "hora_fim": "12:00",
    "ativo": true
  }
}
```

**Resposta de Erro (Conflito):**
```json
{
  "detail": "Conflito de horário com período existente: 14:00 - 18:00"
}
```

#### `PUT /api/configuracao/horarios-semanais/{horario_id}`
Atualiza um horário semanal existente.

**Requisição:** (mesma do POST)

#### `DELETE /api/configuracao/horarios-semanais/{horario_id}`
Deleta um horário semanal permanentemente.

**Resposta:**
```json
{
  "success": true,
  "message": "Horário deletado com sucesso"
}
```

#### `PATCH /api/configuracao/horarios-semanais/{horario_id}/toggle`
Ativa/desativa um horário sem deletar.

**Resposta:**
```json
{
  "success": true,
  "message": "Horário desativado com sucesso",
  "ativo": false
}
```

---

### Opções e Auxiliares

#### `GET /api/configuracao/opcoes-intervalo`
Retorna opções disponíveis para configuração.

**Resposta:**
```json
{
  "opcoes_intervalo": [
    {"valor": 15, "texto": "15 minutos"},
    {"valor": 30, "texto": "30 minutos"},
    {"valor": 60, "texto": "1 hora"}
  ],
  "dias_semana": [
    {"valor": 1, "texto": "Segunda-feira"},
    {"valor": 2, "texto": "Terça-feira"}
  ],
  "horarios_padrao": [
    {"valor": "08:00", "texto": "08:00"},
    {"valor": "08:30", "texto": "08:30"}
  ]
}
```

---

## 🖥️ Interface Web

### Nova Página: `configuracao-medicos.html`

**URL:** `http://localhost:8000/static/configuracao-medicos.html`

**Funcionalidades:**

#### 1. Seleção de Médico
- Dropdown para selecionar qual médico configurar
- Exibe nome completo e especialidade
- Carrega automaticamente as configurações ao selecionar

#### 2. Abas de Configuração

**Aba 1: Configurações Gerais**
- Duração da Consulta (dropdown com opções)
- Consultas Simultâneas (1-5)
- Intervalo de Almoço (início e fim)
- Tempo de Preparação (minutos)
- Botão "Salvar Configurações Gerais"

**Aba 2: Horários Semanais**
- **Grade Visual por Dia da Semana**
- Cada dia mostra todos os períodos configurados
- Contador de períodos por dia
- Formulário para adicionar novo período
- Cards de horários com:
  - Switch para ativar/desativar
  - Botão de excluir
  - Efeito hover visual

#### 3. Recursos da Interface
- ✅ **Autenticação obrigatória** - Redireciona para login se não autenticado
- ✅ **Mensagens de feedback** - Sucesso/erro visíveis por 5 segundos
- ✅ **Validação de conflitos** - Exibe erro se houver sobreposição
- ✅ **Design responsivo** - Funciona em mobile e desktop
- ✅ **Animações suaves** - Fade-in e transições
- ✅ **Confirmação de exclusão** - Diálogo antes de deletar

#### 4. Exemplo Visual da Grade de Horários

```
┌─────────────────────────────────────────────────────┐
│ Segunda-feira                          (2 períodos) │
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐                │
│  │ 08:00 - 12:00│  │ 14:00 - 18:00│                │
│  │ [Toggle ON]  │  │ [Toggle ON]  │                │
│  │ [Excluir]    │  │ [Excluir]    │                │
│  └──────────────┘  └──────────────┘                │
└─────────────────────────────────────────────────────┘
```

---

## 🧪 Testes Realizados

### Testes de API

#### ✅ Teste 1: Listar Opções
```bash
curl http://localhost:8000/api/configuracao/opcoes-intervalo
```
**Resultado:** Retornou 7 opções de intervalo + dias da semana ✅

#### ✅ Teste 2: Criar Horário
```bash
curl -X POST http://localhost:8000/api/configuracao/horarios-semanais \
  -H "Content-Type: application/json" \
  -d '{"medico_id": 1, "dia_semana": 1, "hora_inicio": "08:00", "hora_fim": "12:00"}'
```
**Resultado:** Horário criado com ID 6 ✅

#### ✅ Teste 3: Criar Segundo Período (Mesmo Dia)
```bash
curl -X POST http://localhost:8000/api/configuracao/horarios-semanais \
  -H "Content-Type: application/json" \
  -d '{"medico_id": 1, "dia_semana": 1, "hora_inicio": "14:00", "hora_fim": "18:00"}'
```
**Resultado:** Horário criado com ID 7 ✅

#### ✅ Teste 4: Validação de Conflito
```bash
curl -X POST http://localhost:8000/api/configuracao/horarios-semanais \
  -H "Content-Type: application/json" \
  -d '{"medico_id": 1, "dia_semana": 1, "hora_inicio": "10:00", "hora_fim": "15:00"}'
```
**Resultado:** Erro com mensagem "Conflito de horário com período existente: 14:00 - 18:00" ✅

#### ✅ Teste 5: Toggle Ativo/Inativo
```bash
curl -X PATCH http://localhost:8000/api/configuracao/horarios-semanais/6/toggle
```
**Resultado:** Horário desativado com sucesso ✅

#### ✅ Teste 6: Listar Horários
```bash
curl http://localhost:8000/api/configuracao/horarios-semanais/1
```
**Resultado:** Retornou array com 2 horários ✅

---

## 🔄 Integração com Sistema de Agendamentos

### CalendarioService
O serviço `app/services/calendario_service.py` **JÁ ESTÁ INTEGRADO** com as novas configurações:

**Linha 155-162:** Busca `intervalo_consulta` de `configuracoes_medico`
```python
config = db.execute(text("""
    SELECT intervalo_consulta, tempo_antes_consulta
    FROM configuracoes_medico
    WHERE medico_id = :medico_id
"""), {'medico_id': medico_id}).fetchone()

if config:
    duracao_consulta = config.intervalo_consulta or duracao_consulta
```

**Linha 168-173:** Busca `horarios_atendimento` por médico e dia
```python
horarios_base = db.execute(text("""
    SELECT dia_semana, hora_inicio, hora_fim
    FROM horarios_atendimento
    WHERE medico_id = :medico_id AND ativo = true
    ORDER BY dia_semana, hora_inicio
"""), {'medico_id': medico_id}).fetchall()
```

### Impacto no Sistema
✅ **Bot WhatsApp** - Agora oferece horários individualizados por médico
✅ **Calendário Web** - Respeita configurações individuais
✅ **Verificação de Disponibilidade** - Usa horários semanais específicos
✅ **Listagem de Horários Disponíveis** - Baseada em configurações individuais

---

## 📊 Comparação: Antes vs Depois

| Aspecto | ANTES | DEPOIS |
|---------|-------|--------|
| **Duração de Consulta** | Global para todos | Individualizada por médico |
| **Horários Semanais** | JSON no campo do médico | Tabela dedicada com múltiplos períodos |
| **Interface** | Apenas para médico logado | Admin pode configurar qualquer médico |
| **Períodos por Dia** | 1 período por dia | Múltiplos períodos (ex: manhã E tarde) |
| **Validação de Conflitos** | Não tinha | Validação automática de sobreposição |
| **Ativar/Desativar** | Não tinha | Toggle sem deletar |
| **Intervalo de Almoço** | Genérico | Personalizado por médico |

---

## 🎯 Exemplo de Uso Prático

### Cenário: Clínica com 2 Médicos

**Dr. Marco (Cardiologista):**
- Consultas de 60 minutos
- Segunda: 08h-12h e 14h-18h
- Quarta: 14h-20h
- Sexta: 08h-13h
- Almoço: 12h-14h

**Dra. Tânia (Alergista):**
- Consultas de 30 minutos
- Terça: 08h-12h
- Quinta: 08h-17h
- Sexta: 14h-18h
- Almoço: 12h-13h

### Como Configurar:

1. Acesse: `http://localhost:8000/static/configuracao-medicos.html`
2. Selecione "Dr. Marco Aurélio"
3. **Aba Configurações Gerais:**
   - Duração: 60 minutos
   - Almoço: 12:00 - 14:00
   - Salvar
4. **Aba Horários Semanais:**
   - Adicionar: Segunda, 08:00 - 12:00
   - Adicionar: Segunda, 14:00 - 18:00
   - Adicionar: Quarta, 14:00 - 20:00
   - Adicionar: Sexta, 08:00 - 13:00
5. Repetir para Dra. Tânia com suas configurações

---

## 🚀 Próximos Passos (Opcional)

### Melhorias Futuras Sugeridas
- [ ] Copiar configuração de um médico para outro
- [ ] Templates de horários (manhã completa, tarde completa, etc.)
- [ ] Histórico de alterações de configurações
- [ ] Bloqueios temporários na interface (férias, folgas)
- [ ] Exportar/importar configurações (JSON/Excel)
- [ ] Dashboard com resumo de configurações de todos os médicos
- [ ] Validação de carga horária (alertar se médico trabalha >10h/dia)

---

## 📝 Arquivos Modificados/Criados

### Arquivos Criados
- ✅ `static/configuracao-medicos.html` - Nova interface completa
- ✅ `INDIVIDUALIZACAO_MEDICOS.md` - Esta documentação

### Arquivos Modificados
- ✅ `app/api/configuracao.py` - Adicionadas APIs de horários semanais
  - `GET /horarios-semanais/{medico_id}`
  - `POST /horarios-semanais`
  - `PUT /horarios-semanais/{horario_id}`
  - `DELETE /horarios-semanais/{horario_id}`
  - `PATCH /horarios-semanais/{horario_id}/toggle`

### Arquivos Backups
- ✅ `static/configuracao-agenda.html.backup_20251128_*` - Backup do arquivo anterior

---

## ✅ Checklist de Validação

### Backend
- [x] Tabela `configuracoes_medico` existe
- [x] Tabela `horarios_atendimento` existe
- [x] API GET intervalos funcionando
- [x] API POST intervalos funcionando
- [x] API GET horários semanais funcionando
- [x] API POST horários semanais funcionando
- [x] API PUT horários semanais funcionando
- [x] API DELETE horários semanais funcionando
- [x] API PATCH toggle funcionando
- [x] Validação de conflitos funcionando
- [x] Integração com CalendarioService

### Frontend
- [x] Seleção de médico funcionando
- [x] Aba Configurações Gerais funcionando
- [x] Aba Horários Semanais funcionando
- [x] Adicionar período funcionando
- [x] Deletar período funcionando
- [x] Toggle ativo/inativo funcionando
- [x] Mensagens de sucesso/erro funcionando
- [x] Validação de conflitos no frontend
- [x] Design responsivo
- [x] Autenticação obrigatória

### Sistema
- [x] Serviço reiniciado com sucesso
- [x] Sem erros no log
- [x] Testes de API aprovados
- [x] Integração com agendamentos

---

## 🎉 Conclusão

✅ **Implementação 100% Concluída!**

O sistema Horário Inteligente agora possui configurações **completamente individualizadas por médico**, permitindo:
- Durações de consulta diferentes para cada profissional
- Horários semanais flexíveis com múltiplos períodos por dia
- Interface moderna e intuitiva para gerenciamento
- Validações robustas para evitar conflitos
- Integração completa com o sistema de agendamentos existente

**Sistema testado e validado com sucesso!** 🚀

---

**Desenvolvido com ❤️ por Marco com assistência de Claude Code**
**Data:** 28 de novembro de 2025
**Versão do Sistema:** Horário Inteligente 2.4.0
