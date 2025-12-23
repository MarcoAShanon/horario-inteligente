# 📘 Exemplos Práticos de Onboarding

## 🚀 Método 1: Modo Interativo (Recomendado)

O modo mais fácil e guiado:

```bash
cd /root/sistema_agendamento
source venv/bin/activate
python scripts/onboard_cliente.py
```

**Exemplo de execução:**

```
==================================================================
🚀 ONBOARDING DE NOVO CLIENTE - SISTEMA HORÁRIO INTELIGENTE
==================================================================

📋 DADOS DA CLÍNICA:
Nome da clínica: Clínica São Lucas
Subdomínio (ex: saolucas): saolucas
Email da clínica: contato@saolucas.com.br

🎨 PERSONALIZAÇÃO (pressione Enter para usar padrão):
Cor primária (hex, ex: #10b981): #10b981
Cor secundária (hex, ex: #059669): #059669
Ícone FontAwesome (ex: fa-hospital): fa-clinic-medical

🏥 Criando cliente...
✅ Cliente criado com sucesso!
   ID: 2
   Nome: Clínica São Lucas
   Subdomínio: saolucas
   URL: https://saolucas.horariointeligente.com.br

👨‍⚕️ CADASTRO DE MÉDICOS:

Nome do médico: Dr. João Silva
Email do médico: joao@saolucas.com.br
Especialidade: Cardiologista
CRM (ex: CRM-SP 123456): CRM-SP 123456
Telefone (opcional): 11999998888

✅ Médico adicionado:
   Nome: Dr. João Silva
   Email: joao@saolucas.com.br
   Especialidade: Cardiologista

Adicionar outro médico? (s/N): n

👤 USUÁRIO ADMINISTRADOR:
Nome do usuário: Maria Secretária
Email de login: secretaria@saolucas.com.br
Senha: saolucas123

✅ Usuário criado:
   Nome: Maria Secretária
   Email: secretaria@saolucas.com.br
   Tipo: secretaria
   Senha: saolucas123

==================================================================
🎉 ONBOARDING CONCLUÍDO COM SUCESSO!
==================================================================

🌐 URL de Acesso:
   https://saolucas.horariointeligente.com.br

👤 Login:
   Email: secretaria@saolucas.com.br
   Senha: saolucas123

📝 Próximos Passos:
   1. Configurar WhatsApp Evolution API (se necessário)
   2. Fazer upload da logo (se tiver)
   3. Testar acesso e funcionalidades
   4. Treinar equipe do cliente

==================================================================
```

**Tempo total:** ⚡ **5-7 minutos**

---

## ⚡ Método 2: Modo Rápido (Linha de Comando)

Para criar um cliente rapidamente com argumentos:

```bash
cd /root/sistema_agendamento
source venv/bin/activate

python scripts/onboard_cliente.py \
  --nome "Clínica São Lucas" \
  --subdomain "saolucas" \
  --email "contato@saolucas.com.br" \
  --cor-primaria "#10b981" \
  --cor-secundaria "#059669" \
  --logo-icon "fa-clinic-medical" \
  --medico-nome "Dr. João Silva" \
  --medico-email "joao@saolucas.com.br" \
  --medico-especialidade "Cardiologista" \
  --medico-crm "CRM-SP 123456" \
  --medico-telefone "11999998888" \
  --admin-nome "Maria Secretária" \
  --admin-email "secretaria@saolucas.com.br" \
  --admin-senha "saolucas123"
```

**Tempo total:** ⚡ **2-3 minutos**

---

## 🎨 Método 3: Script SQL Direto (Mais Rápido)

Para quem prefere SQL:

```sql
-- 1. Criar cliente
INSERT INTO clientes (
    nome, subdomain, email, logo_icon,
    cor_primaria, cor_secundaria, whatsapp_instance,
    plano, ativo, criado_em, atualizado_em
) VALUES (
    'Clínica São Lucas',
    'saolucas',
    'contato@saolucas.com.br',
    'fa-clinic-medical',
    '#10b981',
    '#059669',
    'SaoLucas',
    'profissional',
    true,
    NOW(),
    NOW()
) RETURNING id;

-- Resultado: id = 2

-- 2. Criar médico
INSERT INTO medicos (
    nome, email, especialidade, crm, telefone,
    cliente_id, criado_em, atualizado_em
) VALUES (
    'Dr. João Silva',
    'joao@saolucas.com.br',
    'Cardiologista',
    'CRM-SP 123456',
    '11999998888',
    2,
    NOW(),
    NOW()
) RETURNING id;

-- Resultado: medico_id = 3

-- 3. Criar configuração de agenda
INSERT INTO configuracoes (
    medico_id, cliente_id, intervalo_consulta,
    horario_inicio, horario_fim, dias_atendimento
) VALUES (
    3,  -- ID do médico
    2,  -- ID do cliente
    30,
    '08:00',
    '18:00',
    '1,2,3,4,5'
);

-- 4. Criar usuário (senha criptografada com bcrypt)
-- Senha: saolucas123
-- Hash bcrypt: $2b$12$... (gerar com bcrypt.hash)

INSERT INTO usuarios (
    nome, email, senha, tipo, cliente_id,
    ativo, criado_em, atualizado_em
) VALUES (
    'Maria Secretária',
    'secretaria@saolucas.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5kosgVIi/ZY3O',  -- saolucas123
    'secretaria',
    2,
    true,
    NOW(),
    NOW()
);
```

**Tempo total:** ⚡ **1-2 minutos** (se souber os comandos)

---

## 🧪 Testar Novo Cliente

Após criar o cliente, teste imediatamente:

### 1. Teste de Branding API

```bash
curl https://saolucas.horariointeligente.com.br/api/tenant/branding | python3 -m json.tool
```

**Resultado esperado:**
```json
{
  "nome": "Clínica São Lucas",
  "subdomain": "saolucas",
  "logo_url": null,
  "logo_icon": "fa-clinic-medical",
  "cor_primaria": "#10b981",
  "cor_secundaria": "#059669",
  "favicon_url": null,
  "whatsapp_numero": null
}
```

### 2. Teste de Acesso Web

Abrir no navegador:
```
https://saolucas.horariointeligente.com.br
```

**Verificar:**
- ✅ Nome da clínica aparece: "Clínica São Lucas"
- ✅ Ícone correto (hospital)
- ✅ Cor verde (#10b981)
- ✅ Login funciona

### 3. Fazer Login

```
Email: secretaria@saolucas.com.br
Senha: saolucas123
```

**Verificar:**
- ✅ Login bem-sucedido
- ✅ Redireciona para calendário
- ✅ Branding correto em todas as páginas

---

## 📊 Tabela de Cores Sugeridas

Para facilitar a escolha de cores para novos clientes:

| Cliente | Cor Primária | Cor Secundária | Ícone | Vibe |
|---------|-------------|---------------|-------|------|
| **ProSaude** | `#3b82f6` | `#1e40af` | `fa-heartbeat` | Azul profissional |
| **São Lucas** | `#10b981` | `#059669` | `fa-clinic-medical` | Verde saúde |
| **Santa Casa** | `#ef4444` | `#b91c1c` | `fa-hospital` | Vermelho institucional |
| **Vida Nova** | `#8b5cf6` | `#6d28d9` | `fa-hand-holding-heart` | Roxo acolhedor |
| **Bem Estar** | `#f59e0b` | `#d97706` | `fa-leaf` | Laranja energia |
| **Saúde Total** | `#06b6d4` | `#0891b2` | `fa-stethoscope` | Ciano moderno |

---

## 🎯 Ícones FontAwesome Populares

Para o campo `logo_icon`:

### Saúde Geral
- `fa-heartbeat` - Batimento cardíaco
- `fa-stethoscope` - Estetoscópio
- `fa-hospital` - Hospital
- `fa-clinic-medical` - Clínica médica
- `fa-user-md` - Médico

### Especialidades
- `fa-tooth` - Odontologia
- `fa-eye` - Oftalmologia
- `fa-heart` - Cardiologia
- `fa-brain` - Neurologia
- `fa-baby` - Pediatria

### Wellness
- `fa-leaf` - Naturalidade
- `fa-spa` - Spa/Bem-estar
- `fa-hand-holding-heart` - Cuidado
- `fa-smile` - Felicidade

**Ver todos:** https://fontawesome.com/icons?d=gallery&c=medical

---

## 🔄 Atualizar Cliente Existente

Se precisar atualizar branding de um cliente:

```sql
-- Atualizar cores e ícone
UPDATE clientes
SET
    logo_icon = 'fa-hospital',
    cor_primaria = '#ef4444',
    cor_secundaria = '#b91c1c',
    logo_url = '/static/logos/santa-casa.png'
WHERE subdomain = 'santacasa';
```

**As mudanças são INSTANTÂNEAS** - basta recarregar a página!

---

## 📝 Checklist Pós-Onboarding

Após criar o cliente, verificar:

- [ ] URL funciona: `https://{subdomain}.horariointeligente.com.br`
- [ ] Branding correto (nome, logo, cores)
- [ ] Login funciona
- [ ] Pelo menos 1 médico cadastrado
- [ ] Agenda configurada (horários, dias)
- [ ] WhatsApp conectado (opcional)
- [ ] Cliente notificado com credenciais
- [ ] Treinamento agendado

---

## 💡 Dicas Pro

### 1. Criar Múltiplos Clientes em Lote

```bash
# Arquivo: clientes.txt
SaoLucas|saolucas|#10b981|fa-clinic-medical
SantaCasa|santacasa|#ef4444|fa-hospital
VidaNova|vidanova|#8b5cf6|fa-hand-holding-heart

# Script
while IFS='|' read -r nome subdomain cor icon; do
    python scripts/onboard_cliente.py \
        --nome "$nome" \
        --subdomain "$subdomain" \
        --email "contato@$subdomain.com.br" \
        --cor-primaria "$cor" \
        --logo-icon "$icon"
done < clientes.txt
```

### 2. Gerar Senha Segura

```python
import secrets
import string

def gerar_senha(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(length))

print(gerar_senha())  # Ex: aB3$k9Lm2@Qp
```

### 3. Backup Antes de Adicionar Cliente

```bash
# Backup do banco
pg_dump agendamento_saas > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

**Última atualização:** 2 de dezembro de 2025
**Criado por:** Marco + Claude Code
