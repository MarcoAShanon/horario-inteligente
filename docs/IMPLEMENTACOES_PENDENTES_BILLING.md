# Implementações Pendentes - Sistema de Billing ASAAS

**Data:** 22/01/2026
**Status:** Pendente de implementação
**Prioridade:** Alta

---

## 1. Middleware de Bloqueio para Inadimplentes

### Objetivo
Bloquear acesso ao sistema para clientes com assinatura suspensa, exibindo tela informativa com opção de pagamento.

### Comportamento Esperado
- Quando `cliente.ativo = false` ou `assinatura.status = 'suspensa'`
- Redirecionar para tela `/static/conta-suspensa.html`
- Exibir mensagem amigável explicando a situação
- Mostrar botão "Regularizar Pagamento" que leva ao link de pagamento ASAAS

### Arquivos a Criar/Modificar

#### 1.1 Middleware (`app/middleware/billing_middleware.py`)
```python
class BillingMiddleware(BaseHTTPMiddleware):
    """
    Bloqueia acesso para clientes inadimplentes
    Exceções: rotas de pagamento, webhook, login
    """

    ROTAS_LIBERADAS = [
        '/static/conta-suspensa.html',
        '/static/login.html',
        '/api/auth/',
        '/api/billing/pagar',
        '/api/webhooks/',
    ]

    async def dispatch(self, request, call_next):
        # Verificar se cliente está ativo
        # Se não, redirecionar para conta-suspensa
        pass
```

#### 1.2 Página de Bloqueio (`static/conta-suspensa.html`)
- Design responsivo com branding
- Mensagem: "Sua assinatura está suspensa"
- Informações da fatura pendente (valor, vencimento)
- Botão PIX com QR Code
- Botão Boleto
- Link para contato/suporte
- Após pagamento, atualização automática via webhook

#### 1.3 Endpoint de Pagamento (`app/api/billing.py`)
```python
@router.get("/pagar/{cliente_id}")
async def obter_link_pagamento(cliente_id: int):
    """Retorna link de pagamento da fatura pendente"""
    # Buscar fatura OVERDUE mais antiga
    # Retornar invoiceUrl do ASAAS
    pass
```

### Fluxo
```
Usuário acessa sistema
    ↓
Middleware verifica cliente.ativo
    ↓
Se ativo=false → Redireciona para /conta-suspensa.html
    ↓
Usuário paga via PIX/Boleto
    ↓
Webhook ASAAS recebe PAYMENT_CONFIRMED
    ↓
Régua reativa cliente (ativo=true)
    ↓
Usuário pode acessar sistema normalmente
```

---

## 2. Assinaturas Recorrentes (Cobranças Automáticas)

### Objetivo
Criar cobranças automáticas mensais no ASAAS para cada cliente ativo.

### Opções de Implementação

#### Opção A: Usar Assinatura Nativa do ASAAS
- Criar subscription no ASAAS vinculada ao cliente
- ASAAS gera cobranças automaticamente
- Mais simples, menos controle

#### Opção B: Scheduler Interno (Recomendado)
- Job diário que verifica assinaturas
- Cria cobrança X dias antes do vencimento
- Mais controle sobre regras de negócio

### Arquivos a Criar/Modificar

#### 2.1 Scheduler (`app/scheduler/billing_scheduler.py`)
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def gerar_cobrancas_mensais():
    """
    Executar diariamente às 08:00
    - Buscar assinaturas ativas
    - Verificar dia_vencimento
    - Se faltam X dias, criar cobrança no ASAAS
    """
    pass

async def verificar_vencimentos():
    """
    Executar diariamente às 09:00
    - Buscar cobranças vencidas há mais de X dias
    - Enviar lembrete ou suspender
    """
    pass
```

#### 2.2 Serviço de Cobrança (`app/services/cobranca_service.py`)
```python
class CobrancaService:
    def criar_cobranca_mensal(self, assinatura_id: int):
        """
        1. Calcular valor (mensal + adicionais)
        2. Criar cobrança no ASAAS
        3. Registrar em pagamentos
        4. Vincular à assinatura
        """
        pass

    def criar_cobranca_ativacao(self, assinatura_id: int):
        """Taxa de ativação para novos clientes"""
        pass
```

#### 2.3 Configurações
```python
# Dias antes do vencimento para gerar cobrança
DIAS_ANTECEDENCIA_COBRANCA = 5

# Dias de tolerância após vencimento
DIAS_TOLERANCIA = 3

# Formas de pagamento aceitas
BILLING_TYPES = ['PIX', 'BOLETO']
```

### Fluxo de Cobrança Mensal
```
Dia 5 do mês (dia_vencimento=10)
    ↓
Scheduler identifica assinatura
    ↓
Calcula valor: R$200 + adicionais
    ↓
Cria cobrança no ASAAS (venc. dia 10)
    ↓
Registra em tabela pagamentos
    ↓
Cliente recebe notificação (email/WhatsApp)
    ↓
Se não pagar até dia 10 → PAYMENT_OVERDUE
    ↓
Régua suspende cliente
```

---

## 3. Notificações de Inadimplência via WhatsApp

### Objetivo
Avisar cliente automaticamente quando houver problema com pagamento.

### Tipos de Notificação

| Evento | Mensagem | Timing |
|--------|----------|--------|
| Cobrança criada | "Sua fatura de R$X vence dia DD/MM" | Imediato |
| Lembrete | "Sua fatura vence amanhã" | D-1 |
| Vencimento | "Sua fatura venceu hoje" | D+0 |
| Suspensão | "Sua conta foi suspensa por inadimplência" | Ao suspender |
| Reativação | "Pagamento confirmado! Sua conta foi reativada" | Ao reativar |

### Arquivos a Criar/Modificar

#### 3.1 Serviço de Notificação (`app/services/notificacao_billing.py`)
```python
class NotificacaoBillingService:

    async def notificar_cobranca_criada(self, pagamento_id: int):
        """Envia WhatsApp informando nova cobrança"""
        pass

    async def notificar_vencimento_proximo(self, pagamento_id: int):
        """Lembrete 1 dia antes do vencimento"""
        pass

    async def notificar_suspensao(self, cliente_id: int):
        """Avisa que conta foi suspensa"""
        # Incluir link de pagamento na mensagem
        pass

    async def notificar_reativacao(self, cliente_id: int):
        """Confirma que pagamento foi recebido"""
        pass
```

#### 3.2 Templates de Mensagem
```python
TEMPLATES = {
    'cobranca_criada': """
🧾 *Nova Fatura Disponível*

Olá {nome}!

Sua fatura mensal do Horário Inteligente está disponível:

💰 Valor: R$ {valor}
📅 Vencimento: {vencimento}

Pague via PIX para liberação imediata:
{link_pagamento}

Dúvidas? Responda esta mensagem.
""",

    'suspensao': """
⚠️ *Conta Suspensa*

Olá {nome},

Identificamos que sua fatura está em atraso e sua conta foi temporariamente suspensa.

Para regularizar, acesse:
{link_pagamento}

Após o pagamento, sua conta será reativada automaticamente.

Precisa de ajuda? Estamos aqui!
""",

    'reativacao': """
✅ *Pagamento Confirmado!*

Olá {nome}!

Recebemos seu pagamento de R$ {valor}.

Sua conta no Horário Inteligente foi reativada com sucesso!

Obrigado pela confiança. 💙
"""
}
```

#### 3.3 Integração com Webhook
Adicionar chamadas no `webhooks_asaas.py`:
```python
async def processar_pagamento_vencido(db, payment_data):
    # ... código existente ...

    # Enviar notificação WhatsApp
    await notificacao_service.notificar_suspensao(cliente_id)

async def processar_pagamento_confirmado(db, payment_data):
    # ... código existente ...

    # Enviar notificação WhatsApp
    await notificacao_service.notificar_reativacao(cliente_id)
```

---

## Ordem de Implementação Sugerida

1. **Middleware de Bloqueio** (Prioridade Alta)
   - Impacto imediato na experiência do inadimplente
   - Necessário para o fluxo completo funcionar

2. **Notificações WhatsApp** (Prioridade Alta)
   - Melhora comunicação com cliente
   - Reduz inadimplência por esquecimento

3. **Assinaturas Recorrentes** (Prioridade Média)
   - Automatiza processo manual
   - Pode ser feito manualmente inicialmente

---

## Dependências Técnicas

- [x] Webhook ASAAS configurado
- [x] Régua de inadimplência funcionando
- [x] Tabela historico_inadimplencia
- [ ] Evolution API configurada para WhatsApp
- [ ] Templates de mensagem aprovados

---

## Estimativa de Esforço

| Feature | Complexidade | Arquivos |
|---------|--------------|----------|
| Middleware de Bloqueio | Média | 3-4 |
| Assinaturas Recorrentes | Alta | 4-5 |
| Notificações WhatsApp | Média | 2-3 |

---

**Documento criado em:** 22/01/2026
**Última atualização:** 22/01/2026
