# Painel Administrativo - Horário Inteligente

**Versão:** 1.0
**Data:** 21/12/2025
**Status:** Implementado

---

## Sumário

1. [Visão Geral](#visão-geral)
2. [Acesso ao Painel](#acesso-ao-painel)
3. [Perfis e Dashboards](#perfis-e-dashboards)
4. [Dashboard Administrador](#dashboard-administrador)
5. [Dashboard Financeiro](#dashboard-financeiro)
6. [Dashboard Suporte](#dashboard-suporte)
7. [APIs Internas](#apis-internas)
8. [Segurança](#segurança)

---

## Visão Geral

O Painel Administrativo é a interface de gestão interna do SaaS Horário Inteligente. Permite que a equipe interna gerencie clientes, monitore o sistema, controle finanças e forneça suporte técnico.

### Características Principais
- Multi-perfil com dashboards especializados
- Gestão completa de clientes (tenants)
- Controle financeiro (custos, parceiros, comissões)
- Monitoramento de sistema em tempo real
- Logs de auditoria

---

## Acesso ao Painel

### URL de Acesso
```
https://admin.horariointeligente.com.br
```

### Usuários Cadastrados
| Perfil | Nome | Email |
|--------|------|-------|
| Administrador | Thele Marco | thelemarco@horariointeligente.com.br |
| Financeiro | Equipe Financeira | financeiro@horariointeligente.com.br |
| Suporte | Equipe Suporte | suporte@horariointeligente.com.br |

### Fluxo de Login
1. Acessar a URL do painel admin
2. Inserir email e senha
3. Sistema identifica o perfil do usuário
4. Redirecionamento para dashboard específico:
   - **admin** → `/static/admin/dashboard.html`
   - **financeiro** → `/static/admin/dashboard-financeiro.html`
   - **suporte** → `/static/admin/dashboard-suporte.html`

---

## Perfis e Dashboards

### Arquitetura de Perfis
```
┌────────────────────────────────────────────────────┐
│                   LOGIN ÚNICO                       │
│          /static/admin/login.html                  │
└───────────────────────┬────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   ADMIN       │ │  FINANCEIRO   │ │   SUPORTE     │
│   dashboard   │ │  dashboard    │ │  dashboard    │
│   .html       │ │  -financeiro  │ │  -suporte     │
│               │ │  .html        │ │  .html        │
└───────────────┘ └───────────────┘ └───────────────┘
```

### Permissões por Perfil
| Funcionalidade | Admin | Financeiro | Suporte |
|----------------|-------|------------|---------|
| Ver todos os clientes | Sim | Sim (dados financeiros) | Sim (dados técnicos) |
| Criar/Editar clientes | Sim | Não | Não |
| Desativar clientes | Sim | Não | Não |
| Ver custos operacionais | Sim | Sim | Não |
| Gerenciar parceiros | Sim | Sim | Não |
| Ver logs de auditoria | Sim | Não | Sim |
| Gerenciar usuários internos | Sim | Não | Não |

---

## Dashboard Administrador

### Arquivo
`/static/admin/dashboard.html`

### Funcionalidades

#### Seção: Status do Sistema
- Indicadores de API, Banco de Dados, WhatsApp
- Status em tempo real com cores (verde/amarelo/vermelho)

#### Seção: Métricas
| Métrica | Descrição |
|---------|-----------|
| Total de Clientes | Clínicas cadastradas (ativas/inativas) |
| Agendamentos do Mês | Volume de consultas realizadas |
| Receita Mensal (MRR) | Soma das mensalidades ativas |

#### Seção: Lista de Clientes
- Tabela paginada com todos os clientes
- Filtros por status (ativo/inativo)
- Ações: Editar, Desativar, Ver detalhes

#### Seção: Ações Rápidas
- Novo Cliente
- Gerar Relatório
- Limpar Cache de Tenants

---

## Dashboard Financeiro

### Arquivo
`/static/admin/dashboard-financeiro.html`

### Funcionalidades

#### Seção: Indicadores Financeiros
| Indicador | Descrição |
|-----------|-----------|
| Receita Total | Soma de todas as mensalidades |
| Custos Operacionais | Total de despesas cadastradas |
| Resultado Líquido | Receita - Custos |
| Comissões a Pagar | Débitos pendentes com parceiros |

#### Seção: Custos Operacionais
- Listagem de todos os custos cadastrados
- Filtro por categoria e período
- Modal para adicionar novo custo:
  - Categoria (Infraestrutura, APIs, Comunicação, etc.)
  - Descrição
  - Valor
  - Fornecedor
  - Recorrência (Único, Mensal, Anual)

#### Seção: Parceiros Comerciais
- Lista de parceiros indicadores
- Percentual de comissão
- Clientes vinculados
- Total de comissões acumuladas

#### Seção: Clientes (Visão Financeira)
- Nome e subdomínio
- Plano contratado
- Valor da mensalidade
- Status de pagamento

---

## Dashboard Suporte

### Arquivo
`/static/admin/dashboard-suporte.html`

### Funcionalidades

#### Seção: Status do Sistema
| Componente | Monitoramento |
|------------|---------------|
| API (FastAPI) | Uptime, erros/min |
| PostgreSQL | Conexões ativas |
| Evolution API | Status das instâncias WhatsApp |
| Nginx | Requisições/segundo |

#### Seção: Clientes (Visão Técnica)
- Status da instância WhatsApp
- Última atividade
- Volume de agendamentos
- Erros recentes

#### Seção: Logs de Auditoria
- Últimas ações no sistema
- Filtro por usuário e período
- Detalhes de cada ação (antes/depois)

#### Seção: Ações Rápidas
| Ação | Descrição |
|------|-----------|
| Reiniciar Instância WhatsApp | Força reconexão de cliente específico |
| Limpar Cache | Limpa cache de tenant |
| Health Check | Verifica todos os serviços |

---

## APIs Internas

### Autenticação
```
POST /api/interno/usuarios/login
```
**Body:**
```json
{
  "email": "admin@horariointeligente.com.br",
  "senha": "senha123"
}
```
**Response:**
```json
{
  "token": "interno_1",
  "usuario": {
    "id": 1,
    "nome": "Administrador",
    "email": "admin@horariointeligente.com.br",
    "perfil": "admin"
  }
}
```

### Listar Custos
```
GET /api/interno/custos
Authorization: Bearer interno_1
```

### Criar Custo
```
POST /api/interno/custos
Authorization: Bearer interno_1
```
**Body:**
```json
{
  "categoria": "Infraestrutura",
  "descricao": "Servidor VPS",
  "valor": 150.00,
  "fornecedor": "Hostinger",
  "recorrencia": "mensal"
}
```

### Listar Parceiros
```
GET /api/interno/parceiros
Authorization: Bearer interno_1
```

### Criar Parceiro
```
POST /api/interno/parceiros
Authorization: Bearer interno_1
```
**Body:**
```json
{
  "nome": "Dr. João Silva",
  "cnpj": "12.345.678/0001-90",
  "email": "joao@parceiro.com",
  "telefone": "(11) 98888-0000",
  "percentual_comissao": 20.00
}
```

### Logs de Auditoria
```
GET /api/interno/auditoria?limit=50
Authorization: Bearer interno_1
```

---

## Segurança

### Autenticação
- Token simples com prefixo "interno_"
- Validação de perfil em cada requisição
- Sessão armazenada em localStorage

### Autorização
```javascript
// Middleware verifica perfil do token
async function verificarAdmin(token) {
    // Aceita tokens "interno_X" e JWT legado
    if (token.startsWith('interno_')) {
        const userId = parseInt(token.replace('interno_', ''));
        // Busca usuário na tabela usuarios_internos
        // Verifica se perfil é admin/financeiro/suporte
    }
}
```

### Práticas Recomendadas
- Sempre fazer logout ao sair
- Não compartilhar credenciais
- Alterar senha periodicamente
- Reportar acessos suspeitos

### Auditoria
Todas as ações administrativas são registradas:
- Usuário que executou
- Ação realizada
- Recurso afetado
- Dados antes/depois
- IP de origem
- Timestamp

---

## Arquivos do Sistema

### Frontend (HTML/JS)
```
/static/admin/
├── login.html              # Página de login
├── dashboard.html          # Dashboard admin
├── dashboard-financeiro.html   # Dashboard financeiro
└── dashboard-suporte.html      # Dashboard suporte
```

### Backend (Python/FastAPI)
```
/app/api/
├── admin.py                # APIs administrativas legadas
├── usuarios_internos.py    # APIs de usuários internos
├── parceiros_comerciais.py # APIs de parceiros
└── custos_operacionais.py  # APIs de custos
```

### Modelos
```
/app/models/
├── usuario_interno.py      # Model UsuarioInterno
├── parceiro_comercial.py   # Model ParceiroComercial
├── cliente_parceiro.py     # Model ClienteParceiro
└── custo_operacional.py    # Model CustoOperacional
```

---

## Troubleshooting

### Erro: "Não autorizado"
- Verificar se token está sendo enviado no header
- Confirmar que usuário está ativo
- Verificar perfil tem permissão para a ação

### Erro: "Cliente não encontrado"
- Verificar se cliente existe no banco
- Confirmar cliente está ativo
- Verificar subdomain correto

### Erro: "Falha ao carregar dados"
- Verificar se API está rodando (porta 8000)
- Confirmar conexão com banco de dados
- Verificar logs do servidor

### Reset de Senha
Para resetar senha de usuário interno:
```python
from app.database import SessionLocal
from sqlalchemy import text
import bcrypt

db = SessionLocal()
nova_senha = bcrypt.hashpw("nova_senha".encode(), bcrypt.gensalt()).decode()
db.execute(text("""
    UPDATE usuarios_internos SET senha = :senha WHERE email = :email
"""), {"senha": nova_senha, "email": "usuario@horariointeligente.com.br"})
db.commit()
```

---

**Documento elaborado por:** Claude AI
**Última atualização:** 21/12/2025
