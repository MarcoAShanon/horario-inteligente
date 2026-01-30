# Integração ASAAS - Horário Inteligente

> **Última atualização:** 22/01/2026
> **Status:** ✅ Sandbox Funcionando | ⏳ Produção Pendente

---

## Resumo do Status

| Componente | Sandbox | Produção |
|------------|---------|----------|
| Webhook configurado | ✅ | ⏳ |
| Autenticação token | ✅ | ⏳ |
| Criar cliente | ✅ | ⏳ |
| Criar cobrança | ✅ | ⏳ |
| Receber pagamento (webhook) | ✅ | ⏳ |
| Assinaturas recorrentes | ⏳ | ⏳ |
| Régua de inadimplência | ⏳ | ⏳ |

---

## Configuração

### Variáveis de Ambiente (.env)

```env
# ASAAS Configuration
ASAAS_API_KEY=<sua_api_key_sandbox_ou_producao>
ASAAS_ENVIRONMENT=sandbox   # ou 'production'
ASAAS_WEBHOOK_TOKEN=bdaf6ab236628b16294771b8612ce0a5c3a1b3c0858a10bd8e95b7fa7403b830
```

### URLs

| Ambiente | URL Base | Painel |
|----------|----------|--------|
| Sandbox | `https://sandbox.asaas.com/api/v3` | https://sandbox.asaas.com |
| Produção | `https://api.asaas.com/v3` | https://www.asaas.com |

### Webhook ASAAS

- **URL:** `https://horariointeligente.com.br/api/webhooks/asaas`
- **Autenticação:** Header `asaas-access-token` com o token configurado
- **Eventos habilitados:**
  - `PAYMENT_CREATED` - Cobrança criada
  - `PAYMENT_CONFIRMED` - Pagamento confirmado
  - `PAYMENT_RECEIVED` - Pagamento recebido
  - `PAYMENT_OVERDUE` - Pagamento vencido
  - `PAYMENT_UPDATED` - Cobrança atualizada
  - `PAYMENT_DELETED` - Cobrança cancelada
  - `PAYMENT_REFUNDED` - Pagamento estornado
  - Eventos de `SUBSCRIPTION_*` (assinaturas)

---

## Arquivos da Integração

```
app/
├── api/
│   ├── billing.py           # Endpoints de cobrança e assinatura
│   └── webhooks_asaas.py    # Handler de webhooks ASAAS
├── services/
│   └── asaas_service.py     # Cliente HTTP para API ASAAS
└── models/
    ├── pagamento.py         # Model de pagamentos
    └── assinatura.py        # Model de assinaturas
```

---

## Endpoints Disponíveis

### Clientes ASAAS

#### Criar cliente no ASAAS
```http
POST /api/billing/customers
Content-Type: application/json

{
  "cliente_id": 1,
  "cpf_cnpj": "12345678000195",
  "nome": "Nome do Cliente",
  "email": "email@cliente.com"
}
```

**Resposta:**
```json
{
  "cliente_id": 1,
  "asaas_customer_id": "cus_000007473181",
  "nome": "Nome do Cliente",
  "email": "email@cliente.com"
}
```

#### Buscar cliente ASAAS
```http
GET /api/billing/customers/{cliente_id}
```

---

### Cobranças

#### Criar cobrança
```http
POST /api/billing/charges
Content-Type: application/json

{
  "cliente_id": 1,
  "valor": 99.90,
  "descricao": "Mensalidade Janeiro/2026",
  "data_vencimento": "2026-01-25",
  "forma_pagamento": "PIX",
  "tipo": "AVULSO"
}
```

**Formas de pagamento:** `PIX`, `BOLETO`, `CREDIT_CARD`, `UNDEFINED`
**Tipos:** `AVULSO`, `ASSINATURA`, `ATIVACAO`

**Resposta:**
```json
{
  "id": 1,
  "asaas_payment_id": "pay_1h8z9j8p0j3m2myr",
  "valor": 99.90,
  "status": "PENDING",
  "data_vencimento": "2026-01-25",
  "link_boleto": null,
  "link_pix": "https://sandbox.asaas.com/i/...",
  "pix_copia_cola": "00020101021226..."
}
```

#### Listar cobranças do cliente
```http
GET /api/billing/charges/cliente/{cliente_id}?status=PENDING
```

#### Cancelar cobrança
```http
DELETE /api/billing/charges/{pagamento_id}
```

---

### Assinaturas Recorrentes

#### Criar assinatura
```http
POST /api/billing/subscriptions
Content-Type: application/json

{
  "cliente_id": 1,
  "assinatura_id": 1,
  "valor": 299.90,
  "ciclo": "MONTHLY",
  "descricao": "Plano Profissional",
  "forma_pagamento": "PIX",
  "data_inicio": "2026-02-01"
}
```

**Ciclos:** `MONTHLY`, `QUARTERLY`, `SEMIANNUALLY`, `YEARLY`

#### Cancelar assinatura
```http
DELETE /api/billing/subscriptions/{assinatura_id}
```

---

### Taxa de Ativação

```http
POST /api/billing/activation-fee/{cliente_id}?desconto_percentual=0&forma_pagamento=PIX
```

---

## Tabelas do Banco de Dados

### pagamentos
```sql
id                  SERIAL PRIMARY KEY
cliente_id          INTEGER REFERENCES clientes(id)
assinatura_id       INTEGER REFERENCES assinaturas(id)
asaas_payment_id    VARCHAR  -- ID do pagamento no ASAAS
asaas_invoice_url   VARCHAR  -- URL da fatura
valor               NUMERIC
valor_pago          NUMERIC
data_vencimento     DATE
data_pagamento      DATE
forma_pagamento     VARCHAR  -- PIX, BOLETO, CREDIT_CARD
link_boleto         VARCHAR
link_pix            VARCHAR
pix_copia_cola      TEXT
status              VARCHAR  -- PENDING, CONFIRMED, OVERDUE, DELETED, REFUNDED
descricao           VARCHAR
tipo                VARCHAR  -- AVULSO, ASSINATURA, ATIVACAO
criado_em           TIMESTAMP
atualizado_em       TIMESTAMP
```

### Colunas adicionadas em `clientes`
```sql
asaas_customer_id   VARCHAR  -- ID do cliente no ASAAS
```

### Colunas adicionadas em `assinaturas`
```sql
asaas_subscription_id   VARCHAR  -- ID da assinatura no ASAAS
taxa_ativacao_paga      BOOLEAN  -- Se a taxa foi paga
```

---

## Fluxo de Pagamento

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Sistema HI    │────▶│   API ASAAS     │────▶│  Banco Dados    │
│                 │     │                 │     │                 │
│ POST /charges   │     │ Cria cobrança   │     │ status=PENDING  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │ Cliente paga    │
                        │ (PIX/Boleto)    │
                        └─────────────────┘
                                │
                                ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Webhook HI     │◀────│   ASAAS         │     │  Banco Dados    │
│                 │     │                 │     │                 │
│ PAYMENT_RECEIVED│     │ Notifica        │────▶│ status=CONFIRMED│
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Testes Realizados (22/01/2026)

### ✅ Teste 1: Criar Cliente ASAAS
```bash
curl -X POST "https://horariointeligente.com.br/api/billing/customers" \
  -H "Content-Type: application/json" \
  -d '{"cliente_id": 1, "cpf_cnpj": "12345678000195"}'

# Resultado: cus_000007473181
```

### ✅ Teste 2: Criar Cobrança
```bash
curl -X POST "https://horariointeligente.com.br/api/billing/charges" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 1,
    "valor": 99.90,
    "descricao": "Cobrança de Teste via API",
    "data_vencimento": "2026-01-25",
    "forma_pagamento": "PIX"
  }'

# Resultado: pay_1h8z9j8p0j3m2myr - PIX gerado com sucesso
```

### ✅ Teste 3: Webhook PAYMENT_RECEIVED
- Pagamento simulado no painel ASAAS Sandbox
- Webhook recebeu evento às 00:34:33
- Status atualizado de `PENDING` → `CONFIRMED`
- `valor_pago` e `data_pagamento` preenchidos

---

## Comandos Úteis

### Verificar logs do webhook
```bash
journalctl -u horariointeligente.service --since "15 minutes ago" | grep -i "asaas\|payment"
```

### Verificar pagamentos no banco
```bash
cd /root/sistema_agendamento && source venv/bin/activate && python3 -c "
from sqlalchemy import create_engine, text
with open('.env') as f:
    for line in f:
        if 'DATABASE_URL=' in line:
            db_url = line.split('=',1)[1].strip()
            break
engine = create_engine(db_url)
with engine.connect() as conn:
    result = conn.execute(text('SELECT id, asaas_payment_id, status, valor FROM pagamentos ORDER BY id DESC LIMIT 5'))
    for r in result:
        print(r)
"
```

### Verificar status do webhook
```bash
curl -s https://horariointeligente.com.br/api/webhooks/asaas/status | python3 -m json.tool
```

---

## Próximos Passos

### Prioridade Alta
- [ ] **Régua de Inadimplência** - Processar `PAYMENT_OVERDUE` e notificar cliente
- [ ] **Testar Assinaturas Recorrentes** - Criar assinatura e verificar cobranças automáticas
- [ ] **Notificações WhatsApp** - Enviar comprovante de pagamento via WhatsApp

### Prioridade Média
- [ ] **Dashboard Financeiro** - Exibir cobranças e status no painel admin
- [ ] **Relatórios** - Faturamento por período, inadimplência
- [ ] **Migrar para Produção** - Configurar API key de produção

### Prioridade Baixa
- [ ] **Cartão de Crédito** - Implementar tokenização de cartão
- [ ] **Split de Pagamento** - Divisão de valores (se aplicável)

---

## Troubleshooting

### Webhook retorna 401
- Verificar se o token no painel ASAAS está **sem** o prefixo `ASAAS_WEBHOOK_TOKEN=`
- Token correto: `bdaf6ab236628b16294771b8612ce0a5c3a1b3c0858a10bd8e95b7fa7403b830`

### Pagamento não atualiza no banco
- Verificar se o pagamento foi criado via API (não diretamente no painel ASAAS)
- Cliente precisa ter `asaas_customer_id` vinculado

### Erro ao criar cobrança
- Verificar se o cliente já foi criado no ASAAS via `/api/billing/customers`

---

## Referências

- [Documentação ASAAS API](https://docs.asaas.com/reference)
- [Webhooks ASAAS](https://docs.asaas.com/reference/webhook)
- [Sandbox ASAAS](https://sandbox.asaas.com)
