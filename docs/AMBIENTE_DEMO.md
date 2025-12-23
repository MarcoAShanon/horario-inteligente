# Ambiente Demo - Horário Inteligente

**Versão:** 1.0
**Data:** 21/12/2025
**Status:** Implementado

---

## Sumário

1. [Visão Geral](#visão-geral)
2. [Acesso ao Demo](#acesso-ao-demo)
3. [Dados Simulados](#dados-simulados)
4. [Tour Guiado](#tour-guiado)
5. [Reset Automático](#reset-automático)
6. [Fluxo de Conversão](#fluxo-de-conversão)
7. [Configuração Técnica](#configuração-técnica)
8. [Manutenção](#manutenção)

---

## Visão Geral

O Ambiente Demo é um sandbox interativo que permite que potenciais clientes testem o sistema Horário Inteligente antes de contratar. O ambiente contém dados fictícios realistas e é resetado automaticamente todas as noites.

### Objetivos
- Demonstrar funcionalidades do sistema
- Permitir teste prático sem compromisso
- Facilitar conversão de leads em clientes
- Reduzir dúvidas no processo de venda

### Características
- Dados pré-carregados (médicos, pacientes, agendamentos)
- Tour guiado interativo com Intro.js
- Funcionalidades completas (exceto WhatsApp real)
- Reset diário às 03:00

---

## Acesso ao Demo

### URL Principal
```
https://demo.horariointeligente.com.br
```

### Fluxo de Acesso
1. Visitante acessa a URL do demo
2. Página apresenta opções de perfil:
   - **Profissional de Saúde** (Médico)
   - **Secretária**
3. Ao clicar, login é feito automaticamente
4. Dashboard carrega com tour guiado

### Credenciais Disponíveis
| Perfil | Email | Senha |
|--------|-------|-------|
| Médico 1 | dr.carlos@demo.horariointeligente.com.br | demo123 |
| Médica 2 | dra.ana@demo.horariointeligente.com.br | demo123 |
| Médico 3 | dr.roberto@demo.horariointeligente.com.br | demo123 |

---

## Dados Simulados

### Cliente Demo
```
ID: 3
Nome: Clínica Demo
Subdomínio: demo
Plano: Profissional
Status: Ativo
```

### Médicos (3 profissionais)
| Nome | Especialidade | CRM |
|------|---------------|-----|
| Dr. Carlos Silva | Clínico Geral | 123456-SP |
| Dra. Ana Beatriz | Cardiologia | 234567-SP |
| Dr. Roberto Mendes | Ortopedia | 345678-SP |

### Pacientes (20 cadastros)
Nomes fictícios brasileiros com dados variados:
- Maria Santos, João Oliveira, Ana Paula Costa, Pedro Almeida...
- Convênios: Particular, Unimed, Bradesco Saúde, Amil, SulAmérica
- Telefones gerados aleatoriamente

### Agendamentos
| Período | Quantidade | Status |
|---------|------------|--------|
| Últimos 30 dias | 40 | Realizado |
| Próximos 14 dias | 25 | Confirmado/Pendente |

Tipos de atendimento:
- Consulta
- Retorno
- Primeira Consulta

Valores: R$ 150,00, R$ 180,00, R$ 200,00, R$ 250,00

---

## Tour Guiado

### Tecnologia
**Intro.js** - Biblioteca JavaScript para tours interativos

### CDN Utilizado
```html
<link href="https://unpkg.com/intro.js/minified/introjs.min.css" rel="stylesheet">
<script src="https://unpkg.com/intro.js/minified/intro.min.js"></script>
```

### Etapas do Tour
1. **Dashboard** - Visão geral do dia, consultas pendentes
2. **Calendário** - Agenda visual com cores por status
3. **Novo Agendamento** - Formulário de criação
4. **Pacientes** - Lista e gestão de cadastros
5. **Relatórios** - Métricas e estatísticas
6. **Configurações** - Personalização do sistema

### Configuração do Tour
```javascript
const tourSteps = [
    {
        element: '#dashboard-section',
        title: 'Dashboard',
        intro: 'Aqui você visualiza um resumo do seu dia...',
        position: 'bottom'
    },
    {
        element: '#calendar-section',
        title: 'Calendário',
        intro: 'Sua agenda visual com todos os agendamentos...',
        position: 'right'
    },
    // ... mais etapas
];

introJs().setOptions({
    steps: tourSteps,
    showProgress: true,
    showBullets: false,
    exitOnOverlayClick: false,
    doneLabel: 'Concluir Tour',
    nextLabel: 'Próximo',
    prevLabel: 'Anterior'
}).start();
```

### Botão de Reinício
Um botão flutuante no canto inferior direito permite reiniciar o tour a qualquer momento:
```html
<button id="btn-tour" onclick="iniciarTour()">
    Fazer Tour
</button>
```

---

## Reset Automático

### Script de Reset
**Localização:** `/scripts/reset_demo.py`

### Execução
```bash
# Manual
cd /root/sistema_agendamento
source venv/bin/activate
python scripts/reset_demo.py

# Via cron (automático)
0 3 * * * /root/sistema_agendamento/venv/bin/python /root/sistema_agendamento/scripts/reset_demo.py >> /var/log/demo_reset.log 2>&1
```

### Processo de Reset
1. Limpa agendamentos do cliente demo (ID: 3)
2. Limpa pacientes do cliente demo
3. Limpa médicos do cliente demo
4. Recria 3 médicos com credenciais padrão
5. Recria 20 pacientes com dados aleatórios
6. Cria 40 agendamentos passados (status: realizado)
7. Cria 25 agendamentos futuros (status: confirmado/pendente)

### Logs
```bash
# Verificar último reset
tail -50 /var/log/demo_reset.log

# Exemplo de saída
[2025-12-21 03:00:01] Iniciando reset do ambiente demo...
  ✓ Agendamentos limpos
  ✓ Pacientes limpos
  ✓ Médicos limpos
  ✓ 3 médicos criados
  ✓ 20 pacientes criados
  ✓ 65 agendamentos criados

[2025-12-21 03:00:03] ✅ Reset do ambiente demo concluído com sucesso!
```

### Cron Job
```bash
# Editar crontab
crontab -e

# Linha do cron (executa às 3h da manhã)
0 3 * * * /root/sistema_agendamento/venv/bin/python /root/sistema_agendamento/scripts/reset_demo.py >> /var/log/demo_reset.log 2>&1
```

---

## Fluxo de Conversão

### Jornada do Visitante
```
┌─────────────────────────────────────────────────────────────────┐
│                     LANDING PAGE                                 │
│               horariointeligente.com.br                          │
│                          │                                       │
│                    "Testar Grátis"                               │
│                          ▼                                       │
├─────────────────────────────────────────────────────────────────┤
│                     PÁGINA DEMO                                  │
│              demo.horariointeligente.com.br                      │
│                          │                                       │
│              Escolha: Médico / Secretária                        │
│                          ▼                                       │
├─────────────────────────────────────────────────────────────────┤
│                   DASHBOARD DEMO                                 │
│                 (Login automático)                               │
│                          │                                       │
│                   Tour Guiado                                    │
│                          │                                       │
│              Explora funcionalidades                             │
│                          ▼                                       │
├─────────────────────────────────────────────────────────────────┤
│                   CONVERSÃO                                      │
│              "Contratar Agora"                                   │
│                          │                                       │
│              Página de onboarding                                │
│                          ▼                                       │
├─────────────────────────────────────────────────────────────────┤
│                   NOVO CLIENTE                                   │
│          [subdominio].horariointeligente.com.br                  │
└─────────────────────────────────────────────────────────────────┘
```

### Elementos de Conversão
1. **Botão flutuante** - "Contratar Agora" em todas as telas
2. **Banner no topo** - "Ambiente de demonstração - Dados fictícios"
3. **Modal ao final do tour** - Convite para contratação
4. **Timeout opcional** - Lembrete após 10 minutos de uso

### CTA (Call to Action)
```html
<a href="https://horariointeligente.com.br/#contato" class="btn-contratar">
    Contratar Agora
</a>
```

---

## Configuração Técnica

### Middleware de Tenant
O middleware identifica o subdomínio "demo" e configura:
```python
# app/middleware/tenant_middleware.py
if subdomain == 'demo':
    request.state.cliente_id = 3  # ID fixo do demo
    request.state.is_admin = False
    request.state.is_demo = True
```

### Nginx
Configuração em `/etc/nginx/sites-enabled/horariointeligente`:
```nginx
server {
    server_name demo.horariointeligente.com.br;
    # ... configurações SSL e proxy
}
```

### SSL (Let's Encrypt)
O subdomínio demo está incluído no certificado:
```bash
certbot --expand -d horariointeligente.com.br \
                 -d www.horariointeligente.com.br \
                 -d admin.horariointeligente.com.br \
                 -d demo.horariointeligente.com.br
```

### Arquivos do Frontend
```
/static/demo/
└── index.html              # Página inicial do demo

/static/
└── dashboard-demo.html     # Dashboard com tour integrado
```

---

## Manutenção

### Verificar Status do Demo
```bash
# Verificar se cliente demo existe
psql -U postgres -d agendamentos_db -c "SELECT * FROM clientes WHERE subdomain='demo';"

# Contar dados demo
psql -U postgres -d agendamentos_db -c "SELECT COUNT(*) FROM medicos WHERE cliente_id=3;"
psql -U postgres -d agendamentos_db -c "SELECT COUNT(*) FROM pacientes WHERE cliente_id=3;"
psql -U postgres -d agendamentos_db -c "SELECT COUNT(*) FROM agendamentos WHERE medico_id IN (SELECT id FROM medicos WHERE cliente_id=3);"
```

### Reset Manual
```bash
cd /root/sistema_agendamento
source venv/bin/activate
python scripts/reset_demo.py
```

### Atualizar Credenciais Demo
Editar o script `/scripts/reset_demo.py`:
```python
medicos_data = [
    {"nome": "Dr. Novo Nome", "email": "dr.novo@demo...", ...},
    # ...
]
```

### Adicionar Mais Dados
Editar o script para aumentar quantidade:
```python
# Mais pacientes
nomes_pacientes = [
    "Maria Santos", "João Oliveira", ...
    # Adicionar mais nomes
]

# Mais agendamentos passados
for i in range(60):  # Era 40
    # ...

# Mais agendamentos futuros
for i in range(35):  # Era 25
    # ...
```

### Desabilitar Funções Específicas
Para desabilitar funções no demo (como envio de WhatsApp):
```python
# app/services/whatsapp.py
def enviar_mensagem(numero, texto, cliente_id):
    if cliente_id == 3:  # Demo
        logger.info(f"[DEMO] Mensagem simulada para {numero}")
        return {"status": "demo", "message": "Simulado"}
    # ... código real
```

---

## Troubleshooting

### Demo não carrega
1. Verificar DNS: `dig demo.horariointeligente.com.br`
2. Verificar Nginx: `nginx -t && systemctl status nginx`
3. Verificar certificado SSL
4. Verificar API rodando na porta 8000

### Dados não aparecem
1. Verificar se cliente demo existe (ID: 3)
2. Executar reset manual
3. Verificar logs: `journalctl -u sistema_agendamento -f`

### Tour não inicia
1. Verificar console do navegador (F12)
2. Confirmar CDN do Intro.js carregando
3. Verificar elementos com IDs corretos

### Erro no reset automático
1. Verificar cron: `crontab -l`
2. Verificar logs: `tail /var/log/demo_reset.log`
3. Testar script manualmente
4. Verificar permissões do Python

---

## Métricas de Uso (Futuro)

### Sugestões de Tracking
- Quantidade de acessos ao demo
- Taxa de conclusão do tour
- Tempo médio de sessão
- Taxa de conversão (demo → cliente)
- Funcionalidades mais utilizadas

### Implementação Sugerida
```javascript
// analytics.js
function trackDemoEvent(event, details) {
    // Enviar para serviço de analytics
    fetch('/api/analytics/demo', {
        method: 'POST',
        body: JSON.stringify({
            event: event,
            details: details,
            timestamp: new Date().toISOString()
        })
    });
}

// Uso
trackDemoEvent('tour_started', {step: 1});
trackDemoEvent('tour_completed', {duration: 120});
trackDemoEvent('cta_clicked', {button: 'contratar'});
```

---

**Documento elaborado por:** Claude AI
**Última atualização:** 21/12/2025
