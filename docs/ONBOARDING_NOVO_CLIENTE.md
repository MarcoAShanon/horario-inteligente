# ⏱️ Onboarding de Novo Cliente - Tempo de Implementação

## 📊 Resumo Executivo

**Tempo total:** ⚡ **5 a 15 minutos** (configuração básica)
**Tempo com personalização completa:** 🎨 **30 a 60 minutos**

---

## 🚀 Cenário 1: Configuração Rápida (5-15 minutos)

### Pré-requisitos Já Atendidos ✅
- ✅ **DNS Wildcard já configurado** - Qualquer subdomínio funciona instantaneamente
- ✅ **SSL automático** - Certificado wildcard já cobre todos os subdomínios
- ✅ **Nginx multi-tenant** - Já roteia automaticamente
- ✅ **TenantMiddleware** - Isola dados por tenant automaticamente

### Etapas Necessárias

#### 1️⃣ Criar Cliente no Banco (2 minutos)

```sql
-- Inserir novo cliente
INSERT INTO clientes (
    nome,
    subdomain,
    email,
    whatsapp_instance,
    logo_icon,
    cor_primaria,
    cor_secundaria,
    plano,
    ativo,
    criado_em,
    atualizado_em
) VALUES (
    'Clínica São Lucas',           -- Nome da clínica
    'saolucas',                     -- Subdomínio (saolucas.horariointeligente.com.br)
    'contato@saolucas.com.br',     -- Email
    'SaoLucas',                     -- Nome da instância WhatsApp
    'fa-hospital',                  -- Ícone (FontAwesome)
    '#10b981',                      -- Verde (cor primária)
    '#059669',                      -- Verde escuro (cor secundária)
    'profissional',                 -- Plano
    true,                           -- Ativo
    NOW(),
    NOW()
);
```

**Tempo:** 2 minutos

#### 2️⃣ Cadastrar Médicos (3-5 minutos)

```sql
-- Pegar o ID do cliente recém-criado
SELECT id FROM clientes WHERE subdomain = 'saolucas';
-- Resultado: id = 2

-- Inserir médico
INSERT INTO medicos (
    nome,
    email,
    especialidade,
    crm,
    telefone,
    cliente_id,
    criado_em,
    atualizado_em
) VALUES (
    'Dr. João Silva',
    'joao@saolucas.com.br',
    'Cardiologista',
    'CRM-SP 123456',
    '11999998888',
    2,  -- ID do cliente
    NOW(),
    NOW()
);

-- Inserir configuração de agenda do médico
INSERT INTO configuracoes (
    medico_id,
    intervalo_consulta,
    horario_inicio,
    horario_fim,
    dias_atendimento
) VALUES (
    (SELECT id FROM medicos WHERE email = 'joao@saolucas.com.br'),
    30,
    '08:00',
    '18:00',
    '1,2,3,4,5'  -- Segunda a sexta
);
```

**Tempo:** 3-5 minutos (por médico)

#### 3️⃣ Testar Acesso (2 minutos)

```bash
# Testar branding API
curl https://saolucas.horariointeligente.com.br/api/tenant/branding

# Acessar no navegador
https://saolucas.horariointeligente.com.br
```

**Tempo:** 2 minutos

#### 4️⃣ Criar Usuário de Acesso (3 minutos)

```python
# Script para criar usuário (criar_usuario.py)
from app.database import SessionLocal
from app.models.usuario import Usuario
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

# Criar usuário secretária
usuario = Usuario(
    nome="Maria Secretária",
    email="secretaria@saolucas.com.br",
    senha=pwd_context.hash("senha123"),
    tipo="secretaria",
    cliente_id=2,  # ID do cliente São Lucas
    ativo=True
)

db.add(usuario)
db.commit()
db.close()

print("✅ Usuário criado com sucesso!")
```

**Tempo:** 3 minutos

---

## 🎨 Cenário 2: Configuração Completa com Personalização (30-60 minutos)

Inclui tudo do Cenário 1 mais:

### 5️⃣ Upload e Configuração de Logo (10-15 minutos)

```bash
# 1. Cliente envia logo (PNG, SVG, etc)
# 2. Upload para servidor
scp logo-saolucas.png root@servidor:/root/sistema_agendamento/static/logos/

# 3. Atualizar banco
UPDATE clientes
SET logo_url = '/static/logos/logo-saolucas.png'
WHERE subdomain = 'saolucas';
```

**Tempo:** 10-15 minutos

### 6️⃣ Configurar WhatsApp Evolution API (10-20 minutos)

```bash
# 1. Criar nova instância no Evolution API
curl -X POST http://localhost:8080/instance/create \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "SaoLucas",
    "token": "TOKEN_SEGURO_AQUI"
  }'

# 2. Conectar QR Code
# Abrir Evolution API Manager
# Escanear QR Code com WhatsApp

# 3. Configurar webhook
curl -X POST http://localhost:8080/webhook/set/SaoLucas \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://horariointeligente.com.br/webhook/whatsapp/SaoLucas",
    "webhook_by_events": false
  }'
```

**Tempo:** 10-20 minutos

### 7️⃣ Cadastrar Múltiplos Médicos e Pacientes (5-10 minutos)

Se o cliente já tem base de dados:

```python
# Script de importação em massa
import pandas as pd
from app.database import SessionLocal
from app.models.medico import Medico

db = SessionLocal()

# Ler CSV com dados dos médicos
medicos_df = pd.read_csv('medicos_saolucas.csv')

for _, row in medicos_df.iterrows():
    medico = Medico(
        nome=row['nome'],
        email=row['email'],
        especialidade=row['especialidade'],
        crm=row['crm'],
        cliente_id=2
    )
    db.add(medico)

db.commit()
db.close()
```

**Tempo:** 5-10 minutos

### 8️⃣ Testes de Integração (5-10 minutos)

- ✅ Login funciona
- ✅ Calendário carrega
- ✅ Agendamento via WhatsApp funciona
- ✅ Lembretes automáticos funcionam
- ✅ Branding correto (logo, cores, nome)

**Tempo:** 5-10 minutos

---

## ⚡ Automatização Completa (FUTURO)

### Script de Onboarding Automático

```bash
#!/bin/bash
# onboard_cliente.sh

NOME="Clínica São Lucas"
SUBDOMAIN="saolucas"
EMAIL="contato@saolucas.com.br"
COR_PRIMARIA="#10b981"
COR_SECUNDARIA="#059669"

# 1. Criar cliente
python3 << EOF
from app.database import SessionLocal
from app.models.cliente import Cliente

db = SessionLocal()
cliente = Cliente(
    nome="$NOME",
    subdomain="$SUBDOMAIN",
    email="$EMAIL",
    logo_icon="fa-hospital",
    cor_primaria="$COR_PRIMARIA",
    cor_secundaria="$COR_SECUNDARIA",
    plano="profissional",
    ativo=True
)
db.add(cliente)
db.commit()
print(f"✅ Cliente criado: ID {cliente.id}")
db.close()
EOF

# 2. Configurar WhatsApp
# 3. Criar usuário admin
# 4. Enviar email de boas-vindas

echo "✅ Cliente $SUBDOMAIN configurado e ativo!"
echo "🌐 Acesse: https://$SUBDOMAIN.horariointeligente.com.br"
```

**Tempo com script:** ⚡ **2-3 minutos** (apenas executar)

---

## 📋 Checklist de Onboarding

### Antes de Ativar o Cliente

- [ ] Cliente criado no banco
- [ ] Subdomínio funcionando (testar no navegador)
- [ ] Branding configurado (logo, cores)
- [ ] Pelo menos 1 médico cadastrado
- [ ] Usuário de acesso criado
- [ ] WhatsApp conectado (se aplicável)
- [ ] Testes básicos realizados
- [ ] Cliente notificado e treinado

---

## 💰 Comparação com Concorrentes

| Sistema | Tempo de Onboarding | Complexidade |
|---------|-------------------|--------------|
| **Seu Sistema** | ⚡ 5-15 min | 🟢 Baixa |
| Doctoralia | 2-3 dias | 🔴 Alta |
| Agenda Online | 1-2 dias | 🟡 Média |
| Custom Build | 1-2 semanas | 🔴 Muito Alta |

---

## 🎯 Melhorias Futuras

### 1. Dashboard de Onboarding
- Interface web para cadastrar clientes
- Upload de logo via drag-and-drop
- Seletor de cores visual
- Preview em tempo real

### 2. Wizard de Configuração
- Passo a passo guiado
- Validação automática
- Geração de QR Code WhatsApp na interface

### 3. API de Onboarding
```
POST /api/admin/clientes/onboard
{
  "nome": "Clínica XYZ",
  "subdomain": "xyz",
  "email": "contato@xyz.com",
  "admin_email": "admin@xyz.com",
  "admin_senha": "senha123",
  "medicos": [...]
}
```

---

## 🔍 Resumo por Complexidade

### 🟢 Cliente Simples (1 médico, sem logo)
**Tempo:** 5-10 minutos
- Inserir cliente no banco
- Cadastrar 1 médico
- Criar usuário
- Testar acesso

### 🟡 Cliente Médio (3-5 médicos, com logo)
**Tempo:** 20-30 minutos
- Tudo acima +
- Upload de logo
- Configurar branding personalizado
- Cadastrar múltiplos médicos
- Configurar WhatsApp

### 🔴 Cliente Complexo (10+ médicos, importação de base)
**Tempo:** 45-60 minutos
- Tudo acima +
- Importação em massa de médicos
- Importação de pacientes existentes
- Configurações personalizadas de agenda
- Treinamento do time

---

## ✅ Conclusão

**O sistema foi projetado para onboarding RÁPIDO:**

- ✅ **DNS já pronto** (wildcard)
- ✅ **SSL automático** (certificado wildcard)
- ✅ **Isolamento automático** (TenantMiddleware)
- ✅ **Branding dinâmico** (sem código novo)

**Resultado:** Adicionar um novo cliente é questão de **minutos**, não dias! 🚀

---

**Última atualização:** 2 de dezembro de 2025
**Versão do Sistema:** 3.4.0
