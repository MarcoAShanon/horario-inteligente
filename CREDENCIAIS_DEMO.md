# 🔑 CREDENCIAIS DE ACESSO - AMBIENTE DE DEMONSTRAÇÃO

**⚠️ ATENÇÃO:** Estas credenciais são apenas para **demonstração e desenvolvimento**.
**NÃO usar em produção sem aplicar hash bcrypt nas senhas!**

---

## 🌐 URL de Acesso

```
https://horariointeligente.com.br
```

---

## 👥 CLIENTE: PROSAUDE

### 1️⃣ Secretária/Administrador (Acesso Total)

```
Email:  admin@prosaude.com
Senha:  admin123
Tipo:   Secretária/Administrador
```

**Permissões:**
- ✅ Vê **TODOS** os médicos
- ✅ Vê **TODOS** os agendamentos (101 total)
- ✅ Cria/edita/cancela agendamentos para qualquer médico
- ✅ Gerencia pacientes
- ✅ Acessa configurações do sistema
- ✅ Dashboard completo

---

### 2️⃣ Dra. Tânia Maria - Alergista

```
Email:         tania@prosaude.com
Senha:         admin123
CRM:           CRM-RJ 12345
Especialidade: Alergista
```

**Permissões:**
- ✅ Vê **APENAS** sua própria agenda
- ✅ Visualiza **53 agendamentos** (apenas dela)
- ✅ Dashboard pessoal
- ❌ NÃO vê agendamentos do Dr. Marco (48 agendamentos)
- ❌ NÃO vê outros médicos
- ❌ NÃO acessa configurações do sistema

**Distribuição de Agendamentos:**
- Confirmados: 32 (60.4%)
- Concluídos: 4 (7.5%)
- Remarcados: 11 (20.8%)
- Cancelados: 4 (7.5%)
- Faltas: 2 (3.8%)

---

### 3️⃣ Dr. Marco Aurélio - Cardiologista

```
Email:         marco@prosaude.com
Senha:         admin123
CRM:           CRM-RJ 67890
Especialidade: Cardiologista
```

**Permissões:**
- ✅ Vê **APENAS** sua própria agenda
- ✅ Visualiza **48 agendamentos** (apenas dele)
- ✅ Dashboard pessoal
- ❌ NÃO vê agendamentos da Dra. Tânia (53 agendamentos)
- ❌ NÃO vê outros médicos
- ❌ NÃO acessa configurações do sistema

**Distribuição de Agendamentos:**
- Confirmados: 29 (60.4%)
- Concluídos: 4 (8.3%)
- Remarcados: 7 (14.6%)
- Cancelados: 8 (16.7%)

---

## 💰 PAINEL FINANCEIRO (Gestão Interna)

### 4️⃣ Gestor Financeiro

```
URL:   https://horariointeligente.com.br/static/financeiro/login.html
Email: financeiro@horariointeligente.com.br
Senha: financeiro123
Tipo:  Financeiro (Gestão Interna)
```

**Permissões:**
- ✅ Dashboard financeiro do SaaS
- ✅ Métricas de negócio (MRR, custos, lucro)
- ✅ Lista de todos os clientes
- ✅ Relatórios de faturamento
- ❌ NÃO vê dados de pacientes individuais
- ❌ NÃO acessa agendas dos médicos

---

## 🔐 PAINEL SUPER ADMIN (Gestão Técnica)

### 5️⃣ Super Administrador

```
URL:   https://horariointeligente.com.br/static/admin/login.html
Email: admin@horariointeligente.com.br
Senha: admin123
Tipo:  Super Admin
```

**Permissões:**
- ✅ Gerencia **TODOS** os clientes (CRUD)
- ✅ Cria novos clientes (onboarding)
- ✅ Configurações técnicas do sistema
- ✅ Acesso à infraestrutura
- ❌ NÃO acessa dados de pacientes individuais

---

## 📊 RESUMO DE DADOS DE DEMONSTRAÇÃO

### ProSaude (Cliente ID: 1)

**Pacientes:** 30 cadastrados
- 9 Amil
- 7 SulAmérica
- 5 Unimed
- 4 Bradesco Saúde
- 5 Particular

**Agendamentos:** 101 total (Dezembro 2025)
- 61 Confirmados (60.4%) - agendamentos futuros
- 18 Remarcados (17.8%)
- 12 Cancelados (11.9%)
- 8 Concluídos (7.9%) - pacientes atendidos
- 2 Faltas (2.0%) - pacientes não compareceram

**Distribuição por Médico:**
- Dra. Tânia Maria: 53 agendamentos
- Dr. Marco Aurélio: 48 agendamentos

**Tipos de Atendimento:**
- Exames: 39
- Consultas: 32
- Retornos: 29

---

## 🔒 SEGURANÇA - IMPORTANTE!

### ⚠️ PROBLEMA CRÍTICO

**STATUS ATUAL (Desenvolvimento):**
- Senhas dos médicos armazenadas em **texto plano**
- Campo `medicos.senha` contém: `admin123` (sem hash)

**ANTES DE PRODUÇÃO:**
```bash
# OBRIGATÓRIO: Aplicar hash bcrypt nas senhas
source venv/bin/activate
python scripts/hash_medicos_passwords.py
```

**Após aplicar hash:**
- As senhas continuam sendo `admin123` para login
- Mas serão armazenadas com hash bcrypt no banco
- Segurança em conformidade com boas práticas

---

## 🧪 TESTANDO ACESSO

### Teste de Isolamento de Médicos

```bash
# 1. Login como Dra. Tânia
curl -X POST 'https://horariointeligente.com.br/api/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=tania@prosaude.com&password=admin123'

# 2. Buscar agendamentos (deve retornar apenas 53)
curl 'https://horariointeligente.com.br/api/agendamentos/calendario' \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

### Teste de Acesso Total (Secretária)

```bash
# 1. Login como Secretária
curl -X POST 'https://horariointeligente.com.br/api/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin@prosaude.com&password=admin123'

# 2. Buscar agendamentos (deve retornar todos os 101)
curl 'https://horariointeligente.com.br/api/agendamentos/calendario' \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

---

## 📝 ROTEIRO DE DEMONSTRAÇÃO

### Para Cliente Novo:

1. **Acessar como Secretária** (`admin@prosaude.com`)
   - Mostrar dashboard completo
   - Mostrar calendário com todos os médicos
   - Criar um agendamento de exemplo
   - Mostrar gestão de pacientes

2. **Acessar como Médico** (`tania@prosaude.com`)
   - Mostrar dashboard pessoal
   - Mostrar que vê apenas sua agenda
   - Mostrar filtros e visualizações
   - Demonstrar segurança e privacidade

3. **Explicar Diferenças:**
   - Secretária = acesso total
   - Médico = apenas própria agenda
   - Isolamento de dados por médico
   - Multi-tenant por cliente

---

## 🔄 POPULANDO NOVOS DADOS

Se precisar resetar ou adicionar mais dados:

```bash
source venv/bin/activate
python scripts/populate_demo_data.py
```

**O script cria:**
- 30 pacientes fictícios
- 100 agendamentos para dezembro 2025
- Distribuição inicial: 70% confirmados, 18% remarcados, 12% cancelados
- Distribuição equilibrada entre os médicos
- **Nota:** Agendamentos passados são automaticamente atualizados para status 'concluido' (80%) e 'faltou' (20%)

---

## 📊 VALORES ESPERADOS DO DASHBOARD (Semana 01-07/Dez)

### Dra. Tânia Maria
- Total pacientes: 25
- Consultas hoje (04/12): 1
- Consultas esta semana: 9
- Atendimentos realizados: 4
- Faltas sem aviso: 2
- Cancelamentos: 0
- Taxa de comparecimento: 66.67%

### Secretária (Todos os médicos)
- Total pacientes: 30
- Consultas hoje (04/12): 2
- Consultas esta semana: 17
- Atendimentos realizados: 8
- Faltas sem aviso: 2
- Cancelamentos: 1
- Taxa de comparecimento: 80.0%

---

**Última atualização:** 4 de dezembro de 2025
**Desenvolvedor:** Marco (com Claude Code)
**Sistema:** Horário Inteligente v3.4.0
