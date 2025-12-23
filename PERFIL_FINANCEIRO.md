# 💰 Perfil Financeiro - Horário Inteligente SaaS

**Data de Implementação:** 3 de dezembro de 2025
**Versão:** 3.4.0
**Status:** ✅ **IMPLEMENTADO E FUNCIONAL**

---

## 🎯 Visão Geral

O **Perfil Financeiro** foi criado para a **gestão interna** do Horário Inteligente como negócio SaaS. É um painel exclusivo para o time de gestão financeira visualizar métricas, custos, receitas e relatórios do negócio.

### **Diferença entre Perfis:**

```
┌─────────────────────────────────────────────────────┐
│    GESTÃO INTERNA DO SISTEMA HORÁRIO INTELIGENTE   │
├─────────────────────────────────────────────────────┤
│  👑 Super Admin (Técnico)                           │
│     - Gerencia clientes (CRUD)                      │
│     - Configurações técnicas                        │
│     - Infraestrutura do sistema                     │
├─────────────────────────────────────────────────────┤
│  💰 Financeiro (Gestão do Negócio) ← NOVO!         │
│     - Visualiza receitas (MRR)                      │
│     - Visualiza custos operacionais                 │
│     - Relatórios de faturamento                     │
│     - Métricas de negócio                           │
│     - SEM acesso a dados de clientes/pacientes     │
└─────────────────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
┌───────▼────────┐              ┌─────────▼────────┐
│  Clínica A     │              │  Clínica B       │
│  - Secretária  │              │  - Secretária    │
│  - Médico      │              │  - Médico        │
└────────────────┘              └──────────────────┘
```

---

## 🚀 Funcionalidades Implementadas

### **1. Dashboard - Visão Geral**
- 📊 **Métricas em Tempo Real:**
  - Clientes ativos
  - Novos clientes (últimos 7 dias)
  - Total de médicos ativos
  - MRR (Receita Recorrente Mensal)
  - Ticket médio por cliente
  - Agendamentos do mês

### **2. Gestão de Clientes**
- 📋 **Lista Completa de Clientes:**
  - Nome e ID
  - Subdomínio (link clicável)
  - Plano contratado
  - Total de profissionais (ativos/total)
  - Faturamento mensal (R$ 200/profissional)
  - Status (ativo/inativo)
  - Link de acesso direto ao sistema do cliente

### **3. Análise de Custos**
- 💸 **Custos Operacionais Detalhados:**
  - **IA Claude Sonnet 4.5:** R$ 28/mês por profissional
  - **Infraestrutura:** R$ 100/mês (VPS + WhatsApp + Email)
  - **Total mensal calculado**

- 📈 **Lucratividade:**
  - Receita (MRR)
  - Custos totais
  - Lucro líquido
  - Margem de lucro (%)

### **4. Relatórios de Faturamento**
- 📄 **Relatório por Período:**
  - Filtro por mês e ano
  - Faturamento por cliente
  - Profissionais ativos por cliente
  - Total de agendamentos (total e realizados)
  - Resumo: total de clientes e faturamento total

---

## 🔧 Arquitetura Técnica

### **1. Banco de Dados**

**Tabela:** `super_admins`

Nova coluna adicionada via migração Alembic:
```sql
perfil VARCHAR(20) NOT NULL DEFAULT 'super_admin'
-- Valores possíveis: 'super_admin' ou 'financeiro'
```

### **2. API Endpoints**

**Base:** `/api/financeiro`

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/auth/login` | POST | Login de usuário financeiro |
| `/dashboard/metricas` | GET | Métricas gerais do negócio |
| `/dashboard/clientes` | GET | Lista detalhada de clientes |
| `/dashboard/custos` | GET | Custos operacionais e lucratividade |
| `/relatorios/faturamento` | GET | Relatório de faturamento por período |
| `/health` | GET | Health check do serviço |

**Autenticação:**
- JWT Token com perfil `financeiro` ou `super_admin`
- Tipo: `gestao_interna` (diferente dos usuários de clínicas)
- Validade: 8 horas

### **3. Frontend**

**Arquivos criados:**
- `/static/financeiro/login.html` - Tela de login
- `/static/financeiro/dashboard.html` - Dashboard completo

**Tecnologias:**
- Tailwind CSS (design moderno)
- Font Awesome (ícones)
- Chart.js (gráficos - preparado para uso)
- JavaScript Vanilla (sem dependências pesadas)
- PWA habilitado (instalável como app)

---

## 🔑 Credenciais de Acesso

### **Usuário Financeiro de Teste**

```
URL: https://horariointeligente.com.br/static/financeiro/login.html
Email: financeiro@horariointeligente.com.br
Senha: financeiro123
```

### **Como Criar Novos Usuários Financeiros**

**Opção 1: Script Python**
```bash
source venv/bin/activate
python scripts/create_financeiro_user.py
```

**Opção 2: SQL Direto**
```sql
-- Gerar hash da senha usando bcrypt em Python:
-- import bcrypt
-- bcrypt.hashpw('senha123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

INSERT INTO super_admins (nome, email, senha, perfil, ativo, criado_em, atualizado_em)
VALUES (
    'Nome do Gestor',
    'email@exemplo.com',
    '$2b$12$HASH_BCRYPT_AQUI',  -- Hash da senha
    'financeiro',
    true,
    NOW(),
    NOW()
);
```

---

## 💡 Como Usar

### **1. Acessar o Dashboard**
1. Acesse: https://horariointeligente.com.br/static/financeiro/login.html
2. Faça login com credenciais de perfil financeiro
3. Você será redirecionado para o dashboard

### **2. Navegar pelas Abas**

**Visão Geral:**
- Veja métricas gerais em tempo real
- Cards com dados principais do negócio

**Clientes:**
- Lista completa de todos os clientes
- Clique no subdomínio para acessar o sistema do cliente
- Veja faturamento individual

**Custos:**
- Analise custos operacionais
- Veja lucratividade e margem

**Relatórios:**
- Selecione mês e ano
- Clique em "Buscar"
- Veja faturamento detalhado por cliente

### **3. Atualizar Dados**
- Os dados são carregados automaticamente ao trocar de aba
- Use o botão "Atualizar" na aba de Clientes para recarregar

---

## 📊 Cálculos Financeiros

### **MRR (Receita Recorrente Mensal)**
```
MRR = Total de Profissionais Ativos × R$ 200
```

### **Ticket Médio por Cliente**
```
Ticket Médio = MRR ÷ Total de Clientes Ativos
```

### **Faturamento por Cliente**
```
Faturamento = Profissionais Ativos do Cliente × R$ 200
```

### **Custo Total Mensal**
```
Custo IA = Total de Profissionais × R$ 28
Custo Infraestrutura = R$ 100 (fixo)
Custo Total = Custo IA + Custo Infraestrutura
```

### **Lucro Líquido**
```
Lucro = MRR - Custo Total
```

### **Margem de Lucro**
```
Margem = (Lucro ÷ MRR) × 100
```

---

## 🔒 Segurança e Permissões

### **O que o Perfil Financeiro PODE fazer:**
✅ Visualizar métricas gerais do negócio
✅ Ver lista de clientes (nomes e subdomínios)
✅ Ver faturamento por cliente
✅ Analisar custos e lucratividade
✅ Gerar relatórios financeiros
✅ Acessar link do sistema de clientes (modo visualização)

### **O que o Perfil Financeiro NÃO PODE fazer:**
❌ Ver dados de pacientes individuais
❌ Ver agendas dos profissionais
❌ Criar ou editar clientes
❌ Criar ou editar profissionais
❌ Acessar configurações técnicas do sistema
❌ Ver conversas de WhatsApp
❌ Modificar dados de clínicas

### **Isolamento de Dados:**
- Token JWT específico para gestão interna
- Middleware valida tipo `gestao_interna`
- Queries retornam apenas dados agregados
- Sem acesso a dados sensíveis de pacientes

---

## 🎨 Design e UX

### **Tema Visual:**
- **Cores:** Verde (primária) e Emerald (secundária)
- **Estilo:** Clean, moderno, profissional
- **Layout:** Responsivo (mobile-first)

### **Componentes:**
- Cards com hover effect
- Tabelas responsivas
- Loading states
- Error handling
- Mensagens de feedback

### **Acessibilidade:**
- Ícones Font Awesome para clareza visual
- Cores com bom contraste
- Textos legíveis
- Responsivo em todos os tamanhos de tela

---

## 📱 PWA (Progressive Web App)

O Dashboard Financeiro é um **PWA completo**:

✅ Instalável como app nativo
✅ Funciona offline (páginas já visitadas)
✅ Ícones personalizados
✅ Experiência de app nativo

**Como instalar:**
1. Acesse o dashboard pelo celular
2. Chrome/Edge exibirá "Adicionar à tela inicial"
3. Aceite a instalação
4. App fica na home screen

---

## 🔄 Manutenção e Atualizações

### **Adicionar Novos Campos de Custo**
Edite: `app/api/financeiro.py`
```python
@router.get("/dashboard/custos")
async def get_custos_operacionais(...):
    # Adicionar novos custos aqui
    custo_novo_servico = 50  # exemplo
    custo_total = custo_ia_total + custo_servidor + custo_novo_servico
```

### **Adicionar Novas Métricas**
Edite: `app/api/financeiro.py`
```python
@router.get("/dashboard/metricas")
async def get_metricas_gerais(...):
    # Adicionar novas queries aqui
```

### **Modificar Design**
Edite: `/static/financeiro/dashboard.html`
- Classes Tailwind CSS para estilização
- JavaScript para comportamento

---

## 📈 Roadmap Futuro (Opcional)

### **Melhorias Planejadas:**
- [ ] Gráficos interativos (Chart.js)
- [ ] Exportar relatórios (PDF, Excel)
- [ ] Histórico de receita (últimos 12 meses)
- [ ] Previsão de crescimento
- [ ] Alertas de inadimplência
- [ ] Cobrança automática (integração Stripe/Mercado Pago)
- [ ] Métricas de churn
- [ ] Análise de CAC (Custo de Aquisição de Cliente)
- [ ] LTV (Lifetime Value) por cliente

---

## 🧪 Testes

### **Testar Login**
```bash
curl -X POST 'https://horariointeligente.com.br/api/financeiro/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=financeiro@horariointeligente.com.br&password=financeiro123'
```

### **Testar Métricas (com token)**
```bash
curl 'https://horariointeligente.com.br/api/financeiro/dashboard/metricas' \
  -H 'Authorization: Bearer SEU_TOKEN_AQUI'
```

### **Testar Clientes**
```bash
curl 'https://horariointeligente.com.br/api/financeiro/dashboard/clientes' \
  -H 'Authorization: Bearer SEU_TOKEN_AQUI'
```

---

## 📝 Arquivos Modificados/Criados

### **Novos Arquivos:**
1. `app/api/financeiro.py` - API endpoints financeiros
2. `static/financeiro/login.html` - Página de login
3. `static/financeiro/dashboard.html` - Dashboard completo
4. `scripts/create_financeiro_user.py` - Script de criação de usuários
5. `alembic/versions/f42012c09a90_add_perfil_to_super_admins.py` - Migração

### **Arquivos Modificados:**
1. `app/main.py` - Registro do router financeiro

### **Banco de Dados:**
- Tabela `super_admins` - Nova coluna `perfil`

---

## ✅ Checklist de Validação

- [x] Migração do banco aplicada
- [x] API endpoints criados e testados
- [x] Frontend (login + dashboard) criado
- [x] PWA habilitado
- [x] Usuário financeiro de teste criado
- [x] Servidor FastAPI reiniciado
- [x] Autenticação JWT funcionando
- [x] Métricas calculadas corretamente
- [x] Relatórios gerando dados
- [x] Design responsivo
- [x] Documentação completa

---

## 🎉 Resumo

O **Perfil Financeiro** está **100% implementado e funcional**!

Agora a equipe de gestão financeira do ProSaude SaaS pode:
- 📊 Acompanhar métricas de negócio em tempo real
- 💰 Analisar custos e lucratividade
- 📈 Gerar relatórios de faturamento
- 🏢 Visualizar status de todos os clientes

**Tudo isso sem ter acesso a dados sensíveis de pacientes ou configurações técnicas do sistema!**

---

**Desenvolvido por:** Marco (com Claude Code)
**Data:** 3 de dezembro de 2025
**Versão:** 3.4.0 - ProSaude SaaS
**Status:** ✅ Produção
