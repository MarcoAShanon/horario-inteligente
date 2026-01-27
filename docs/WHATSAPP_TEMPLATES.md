# Templates do WhatsApp Business API

Documentação dos templates aprovados na Meta para envio de mensagens via WhatsApp Business API.

## Visão Geral

Os templates são mensagens pré-aprovadas pela Meta que podem ser enviadas para iniciar conversas com pacientes. Cada template possui variáveis dinâmicas que são preenchidas no momento do envio.

**Serviço:** `app/services/whatsapp_template_service.py`

## Formatos Padrão

| Campo | Formato | Exemplo |
|-------|---------|---------|
| Data | DD/MM/AAAA | 28/01/2026 |
| Hora | HH:MM | 14:30 |
| Valor | com vírgula | 99,90 |
| Telefone | 55 + DDD + número | 5521999999999 |

---

## Templates Disponíveis

### 1. Template de Teste

#### `hello_world`
Template padrão da Meta para testes.

| Campo | Valor |
|-------|-------|
| Idioma | en_US |
| Variáveis | Nenhuma |
| Botões | Nenhum |

```python
await template_service.enviar_hello_world(telefone="5521999999999")
```

---

### 2. Templates de Lembrete

#### `lembrete_24h`
Lembrete enviado 24 horas antes da consulta.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do paciente | Maria |
| {{2}} | Nome do médico | Dr. João Silva |
| {{3}} | Data da consulta | 28/01/2026 |
| {{4}} | Hora da consulta | 14:30 |

**Botões:** "Confirmar presença" | "Preciso remarcar"

```python
await template_service.enviar_lembrete_24h(
    telefone="5521999999999",
    paciente="Maria",
    medico="Dr. João Silva",
    data="28/01/2026",
    hora="14:30"
)
```

#### `lembrete_2h`
Lembrete enviado 2 horas antes da consulta.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do paciente | Maria |
| {{2}} | Nome do médico | Dr. João Silva |
| {{3}} | Hora da consulta | 14:30 |

**Botões:** "Estou a caminho" | "Preciso remarcar"

```python
await template_service.enviar_lembrete_2h(
    telefone="5521999999999",
    paciente="Maria",
    medico="Dr. João Silva",
    hora="14:30"
)
```

---

### 3. Templates de Confirmação

#### `consulta_confirmada`
Confirmação de consulta agendada.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do paciente | Maria |
| {{2}} | Nome do médico | Dr. João Silva |
| {{3}} | Data da consulta | 28/01/2026 |
| {{4}} | Hora da consulta | 14:30 |
| {{5}} | Local/Endereço | Rua das Flores, 123 |

```python
await template_service.enviar_consulta_confirmada(
    telefone="5521999999999",
    paciente="Maria",
    medico="Dr. João Silva",
    data="28/01/2026",
    hora="14:30",
    local="Rua das Flores, 123"
)
```

---

### 4. Templates de Cancelamento

#### `consulta_cancelada_clinica`
Notificação de cancelamento pela clínica.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do paciente | Maria |
| {{2}} | Nome do médico | Dr. João Silva |
| {{3}} | Data da consulta | 28/01/2026 |
| {{4}} | Hora da consulta | 14:30 |
| {{5}} | Motivo | Imprevisto médico |

**Botões:** "Reagendar consulta" | "Entendi"

```python
await template_service.enviar_consulta_cancelada(
    telefone="5521999999999",
    paciente="Maria",
    medico="Dr. João Silva",
    data="28/01/2026",
    hora="14:30",
    motivo="Imprevisto médico"
)
```

---

### 5. Templates de Reagendamento

#### `consulta_reagendada_clinica`
Notificação de reagendamento com nova data já definida.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do paciente | Maria |
| {{2}} | Nome do médico | Dr. João Silva |
| {{3}} | Data original | 28/01/2026 |
| {{4}} | Hora original | 14:30 |
| {{5}} | Nova data | 30/01/2026 |
| {{6}} | Novo horário | 15:00 |

**Botões:** "Confirmar novo horário" | "Preciso de outro horário"

```python
await template_service.enviar_consulta_reagendada(
    telefone="5521999999999",
    paciente="Maria",
    medico="Dr. João Silva",
    data_antiga="28/01/2026",
    hora_antiga="14:30",
    data_nova="30/01/2026",
    hora_nova="15:00"
)
```

#### `necessidade_reagendamento`
Notificação de necessidade de reagendamento (sem nova data definida).

Usado quando a clínica precisa cancelar mas ainda não tem nova data disponível.
Ex: médico doente, emergência, imprevisto.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do paciente | Maria |
| {{2}} | Nome do médico | Dr. João Silva |
| {{3}} | Data original | 28/01/2026 |
| {{4}} | Hora original | 14:30 |
| {{5}} | Motivo | Imprevisto médico |

**Botões:** "Ok quais os horários disponíveis?" | "Remarcarei em outra oportunidade"

**Mensagem:**
```
Olá {{1}}, tudo bem?

Infelizmente precisamos reagendar sua consulta com {{2}} que estava marcada para {{3}} às {{4}}.

Motivo: {{5}}

Pedimos desculpas pelo inconveniente.
```

```python
await template_service.enviar_necessidade_reagendamento(
    telefone="5521999999999",
    paciente="Maria",
    medico="Dr. João Silva",
    data="28/01/2026",
    hora="14:30",
    motivo="Imprevisto médico"
)
```

---

### 6. Templates de Retorno

#### `retorno_agendado`
Confirmação de retorno/acompanhamento agendado.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do paciente | Maria |
| {{2}} | Nome do médico | Dr. João Silva |
| {{3}} | Data do retorno | 28/02/2026 |
| {{4}} | Hora do retorno | 10:00 |
| {{5}} | Procedimento | Retorno pós-operatório |

```python
await template_service.enviar_retorno_agendado(
    telefone="5521999999999",
    paciente="Maria",
    medico="Dr. João Silva",
    data="28/02/2026",
    hora="10:00",
    procedimento="Retorno pós-operatório"
)
```

---

### 7. Templates de Pagamento

#### `pagamento_pendente`
Notificação de pagamento pendente com link.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do cliente | Clínica ABC |
| {{2}} | Valor | 99,90 |
| {{3}} | Vencimento | 05/02/2026 |

**Botão URL:** Link do boleto/pix

```python
await template_service.enviar_pagamento_pendente(
    telefone="5521999999999",
    cliente="Clínica ABC",
    valor="99,90",
    vencimento="05/02/2026",
    url_pagamento="https://asaas.com/b/xxx"
)
```

#### `pagamento_vencido`
Notificação de pagamento em atraso com link.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do cliente | Clínica ABC |
| {{2}} | Valor | 99,90 |
| {{3}} | Vencimento | 05/01/2026 |

**Botão URL:** Link do boleto/pix

```python
await template_service.enviar_pagamento_vencido(
    telefone="5521999999999",
    cliente="Clínica ABC",
    valor="99,90",
    vencimento="05/01/2026",
    url_pagamento="https://asaas.com/b/xxx"
)
```

#### `pagamento_confirmado`
Confirmação de pagamento recebido.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do cliente | Clínica ABC |
| {{2}} | Valor | 99,90 |
| {{3}} | Data do pagamento | 03/02/2026 |

```python
await template_service.enviar_pagamento_confirmado(
    telefone="5521999999999",
    cliente="Clínica ABC",
    valor="99,90",
    data_pagamento="03/02/2026"
)
```

#### `conta_suspensa`
Notificação de conta suspensa por inadimplência.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do cliente | Clínica ABC |
| {{2}} | Valor pendente | 299,90 |

**Botão URL:** Link do boleto/pix

```python
await template_service.enviar_conta_suspensa(
    telefone="5521999999999",
    cliente="Clínica ABC",
    valor="299,90",
    url_pagamento="https://asaas.com/b/xxx"
)
```

---

### 8. Templates de Relacionamento

#### `boas_vindas_clinica`
Mensagem de boas-vindas para novo paciente.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome da clínica | Clínica São José |
| {{2}} | Nome do paciente | Maria |

```python
await template_service.enviar_boas_vindas(
    telefone="5521999999999",
    clinica="Clínica São José",
    paciente="Maria"
)
```

#### `pesquisa_satisfacao`
Pesquisa de satisfação pós-consulta.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do paciente | Maria |
| {{2}} | Nome do médico | Dr. João Silva |
| {{3}} | Data da consulta | 27/01/2026 |

```python
await template_service.enviar_pesquisa_satisfacao(
    telefone="5521999999999",
    paciente="Maria",
    medico="Dr. João Silva",
    data_consulta="27/01/2026"
)
```

#### `paciente_inativo`
Mensagem para reativar paciente inativo.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| {{1}} | Nome do paciente | Maria |
| {{2}} | Nome da clínica | Clínica São José |
| {{3}} | Última consulta | 15/06/2025 |

```python
await template_service.enviar_paciente_inativo(
    telefone="5521999999999",
    paciente="Maria",
    clinica="Clínica São José",
    ultima_consulta="15/06/2025"
)
```

---

## Resumo dos Templates

| Template | Variáveis | Botões |
|----------|-----------|--------|
| `hello_world` | 0 | - |
| `lembrete_24h` | 4 | Quick Reply (2) |
| `lembrete_2h` | 3 | Quick Reply (2) |
| `consulta_confirmada` | 5 | - |
| `consulta_cancelada_clinica` | 5 | Quick Reply (2) |
| `consulta_reagendada_clinica` | 6 | Quick Reply (2) |
| `necessidade_reagendamento` | 5 | Quick Reply (2) |
| `retorno_agendado` | 5 | - |
| `pagamento_pendente` | 3 | URL (1) |
| `pagamento_vencido` | 3 | URL (1) |
| `pagamento_confirmado` | 3 | - |
| `conta_suspensa` | 2 | URL (1) |
| `boas_vindas_clinica` | 2 | - |
| `pesquisa_satisfacao` | 3 | - |
| `paciente_inativo` | 3 | - |

---

## Cadastro na Meta

Para cadastrar um novo template na Meta:

1. Acesse o [Meta Business Suite](https://business.facebook.com/)
2. Vá em **WhatsApp Manager** > **Message Templates**
3. Clique em **Create Template**
4. Preencha:
   - **Category:** UTILITY (para transacionais) ou MARKETING
   - **Name:** nome_do_template (snake_case)
   - **Language:** Portuguese (Brazil)
   - **Body:** Mensagem com variáveis {{1}}, {{2}}, etc.
   - **Buttons:** Quick Reply ou URL conforme necessidade
5. Envie para aprovação

**Tempo de aprovação:** Geralmente 24-48 horas.

---

## Tratamento de Respostas dos Botões

As respostas dos botões são tratadas pelo `button_handler_service.py`:

- **"Confirmar presença"** → Confirma agendamento
- **"Preciso remarcar"** → Inicia fluxo de reagendamento via IA
- **"Estou a caminho"** → Registra confirmação
- **"Ok quais os horários disponíveis?"** → IA sugere horários similares
- **"Remarcarei em outra oportunidade"** → Registra e encerra fluxo
