# 🌐 Configuração DNS Hostinger - Horário Inteligente

**Provedor:** Hostinger (VPS + Domínio)
**Domínio:** horariointeligente.com.br
**Data:** 30/11/2025

---

## ✅ Vantagens de Ter Tudo na Hostinger

- ✅ DNS e VPS no mesmo lugar
- ✅ Não precisa mudar nameservers
- ✅ Propagação mais rápida (mesma rede)
- ✅ Interface simples e intuitiva
- ✅ IP da VPS já está no painel

---

## 📋 Passo a Passo - Hostinger

### **Passo 1: Pegar IP da VPS** (30 segundos)

**Opção A: Via Painel Hostinger**
1. Login: https://hpanel.hostinger.com
2. Menu lateral: **VPS**
3. Clique na sua VPS
4. Copie o **IP Address** (algo como `200.100.50.10`)

**Opção B: Via Terminal (na VPS)**
```bash
curl ifconfig.me
# ou
hostname -I | awk '{print $1}'
```

**Anote o IP:** `___.___.___.___ `

---

### **Passo 2: Configurar DNS** (2 minutos)

1. **Acesse o painel Hostinger:** https://hpanel.hostinger.com

2. **Vá em Domínios:**
   - Menu lateral → **Domínios**
   - Clique em **horariointeligente.com.br**

3. **Clique em "DNS / Nameservers"**

4. **Adicionar/Editar Registros DNS:**

Você vai ver uma lista de registros. Adicione estes:

#### **Registro 1: Domínio Principal (@)**
```
Tipo: A
Nome: @ (ou deixar vazio)
Aponta para: SEU_IP_DA_VPS
TTL: 3600 (ou deixar padrão)
```

#### **Registro 2: WWW**
```
Tipo: A
Nome: www
Aponta para: SEU_IP_DA_VPS
TTL: 3600
```

#### **Registro 3: WILDCARD (ESSENCIAL!)** ⭐
```
Tipo: A
Nome: *
Aponta para: SEU_IP_DA_VPS
TTL: 3600
```

**Exemplo visual na Hostinger:**
```
┌─────┬──────┬─────────────────┬──────┐
│ Tipo│ Nome │ Aponta para     │ TTL  │
├─────┼──────┼─────────────────┼──────┤
│  A  │  @   │ 200.100.50.10   │ 3600 │
│  A  │ www  │ 200.100.50.10   │ 3600 │
│  A  │  *   │ 200.100.50.10   │ 3600 │ ← Wildcard!
└─────┴──────┴─────────────────┴──────┘
```

5. **Salvar alterações**

6. **Aguardar propagação:** 5-15 minutos (Hostinger é rápido!)

---

### **Passo 3: Verificar DNS** (1 minuto)

Após 5-15 minutos:

```bash
# Teste 1: Domínio principal
nslookup horariointeligente.com.br

# Teste 2: WWW
nslookup www.horariointeligente.com.br

# Teste 3: Wildcard (qualquer subdomínio)
nslookup drjoao.horariointeligente.com.br
nslookup drmarco.horariointeligente.com.br
nslookup teste123.horariointeligente.com.br

# Todos devem retornar o MESMO IP!
```

**Esperado:**
```
Server:  8.8.8.8
Address: 8.8.8.8#53

Name: horariointeligente.com.br
Address: 200.100.50.10  ← Seu IP aqui!
```

---

### **Passo 4: Configurar Nginx na VPS** (3 minutos)

Agora vamos configurar o servidor web:

```bash
# 1. Conectar na VPS via SSH
ssh root@SEU_IP

# 2. Verificar se Nginx está instalado
nginx -v

# Se não estiver:
sudo apt update && sudo apt install nginx -y

# 3. Criar configuração
sudo nano /etc/nginx/sites-available/horariointeligente
```

**Cole este conteúdo:**

```nginx
# Multi-Tenant - Horário Inteligente (Hostinger VPS)

server {
    listen 80;
    listen [::]:80;

    # Captura TODOS os subdomínios
    server_name horariointeligente.com.br *.horariointeligente.com.br;

    # Logs
    access_log /var/log/nginx/horariointeligente_access.log;
    error_log /var/log/nginx/horariointeligente_error.log;

    # Tamanho máximo de upload
    client_max_body_size 10M;

    # Proxy para FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }

    # Arquivos estáticos
    location /static/ {
        alias /root/sistema_agendamento/static/;
        expires 30d;
    }
}
```

**Salvar:** `Ctrl + O` → `Enter` → `Ctrl + X`

```bash
# 4. Ativar configuração
sudo ln -sf /etc/nginx/sites-available/horariointeligente /etc/nginx/sites-enabled/

# 5. Remover configuração padrão (opcional)
sudo rm -f /etc/nginx/sites-enabled/default

# 6. Testar configuração
sudo nginx -t

# Deve aparecer: "test is successful"

# 7. Reiniciar Nginx
sudo systemctl restart nginx

# 8. Verificar status
sudo systemctl status nginx
```

---

### **Passo 5: Configurar SSL (HTTPS)** (2 minutos)

```bash
# 1. Instalar Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

# 2. Gerar certificado SSL (AUTOMÁTICO!)
sudo certbot --nginx -d horariointeligente.com.br -d www.horariointeligente.com.br -d "*.horariointeligente.com.br"

# Se pedir wildcard, pode ser que precise validação DNS manual
# Nesse caso, use sem wildcard primeiro:
sudo certbot --nginx -d horariointeligente.com.br -d www.horariointeligente.com.br -d drjoao.horariointeligente.com.br

# Durante instalação:
# - Email: seu-email@exemplo.com
# - Termos: A (Agree)
# - Redirect HTTP→HTTPS: 2 (Sim)
```

**Certbot vai:**
- Validar domínio automaticamente
- Gerar certificados SSL (grátis)
- Configurar Nginx para HTTPS
- Criar renovação automática (a cada 90 dias)

---

### **Passo 6: Testar Tudo!** (1 minuto)

#### **Teste 1: HTTP → HTTPS (redirect automático)**
```bash
curl -I http://horariointeligente.com.br

# Deve retornar:
# HTTP/1.1 301 Moved Permanently
# Location: https://horariointeligente.com.br
```

#### **Teste 2: HTTPS funcionando**
```
No navegador:
https://horariointeligente.com.br
https://www.horariointeligente.com.br
https://drjoao.horariointeligente.com.br

# Deve aparecer cadeado verde 🔒
```

#### **Teste 3: Login Multi-Tenant**
```
https://drjoao.horariointeligente.com.br/static/login.html

Login: admin@prosaude.com
Senha: admin123
```

#### **Teste 4: API Status**
```
https://drjoao.horariointeligente.com.br/webhook/whatsapp/test

# Deve retornar JSON com:
{
  "status": "active",
  "multi_tenant": true,
  "cliente_id_teste": 1,
  ...
}
```

---

## 🔥 Troubleshooting Hostinger

### Problema 1: DNS não propaga

**Sintoma:** `nslookup` não retorna IP correto

**Solução:**
```bash
# 1. Verificar no painel Hostinger se registros foram salvos
# 2. Aguardar mais 15 minutos
# 3. Limpar cache DNS local:
sudo systemd-resolve --flush-caches

# 4. Testar com DNS Google:
nslookup horariointeligente.com.br 8.8.8.8
```

### Problema 2: "Connection refused" ou site não carrega

**Sintoma:** Site não abre, erro de conexão

**Causa:** Firewall da Hostinger bloqueando portas 80/443

**Solução via Painel Hostinger:**
1. VPS → Firewall
2. Adicionar regras:
   - Porta 80 (HTTP) - PERMITIR
   - Porta 443 (HTTPS) - PERMITIR
   - Porta 22 (SSH) - PERMITIR

**Solução via UFW (terminal):**
```bash
# Verificar firewall
sudo ufw status

# Se ativo e bloqueando, permitir:
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw reload
```

### Problema 3: SSL não gera certificado wildcard

**Sintoma:** Certbot falha ao gerar certificado para `*.horariointeligente.com.br`

**Causa:** Wildcard precisa validação DNS manual (não HTTP)

**Solução - Opção A (Simples): Sem wildcard**
```bash
# Gerar certificado para subdomínios específicos
sudo certbot --nginx \
  -d horariointeligente.com.br \
  -d www.horariointeligente.com.br \
  -d drjoao.horariointeligente.com.br \
  -d drmarco.horariointeligente.com.br

# Adicionar mais subdomínios conforme criar clínicas
```

**Solução - Opção B (Avançado): Com wildcard (DNS challenge)**
```bash
# Usar DNS challenge
sudo certbot certonly --manual --preferred-challenges dns \
  -d horariointeligente.com.br \
  -d "*.horariointeligente.com.br"

# Certbot vai pedir para adicionar registro TXT no DNS:
# _acme-challenge.horariointeligente.com.br → "valor-aleatorio-123"

# Adicionar no painel Hostinger:
# Tipo: TXT
# Nome: _acme-challenge
# Valor: (copiar do Certbot)

# Aguardar 2 minutos e continuar no Certbot
```

### Problema 4: FastAPI não está rodando

**Sintoma:** Nginx retorna 502 Bad Gateway

**Solução:**
```bash
# Verificar status
sudo systemctl status horariointeligente.service

# Se não estiver rodando:
sudo systemctl start horariointeligente.service

# Ver logs
sudo journalctl -u horariointeligente.service -n 50

# Verificar porta 8000
sudo netstat -tlnp | grep 8000
```

### Problema 5: Tenant não identificado

**Sintoma:** Erro "Clínica não encontrada: subdominio.horariointeligente.com.br"

**Causa:** Subdomínio não existe no banco

**Solução:**
```bash
# Conectar no PostgreSQL
sudo -u postgres psql -d agendamento_saas

# Verificar clientes
SELECT id, nome, subdomain, whatsapp_instance FROM clientes;

# Se não existir, criar:
INSERT INTO clientes (nome, subdomain, whatsapp_instance, plano, ativo, criado_em, atualizado_em)
VALUES ('Nome da Clínica', 'subdominio', 'ProSaude', 'profissional', true, NOW(), NOW());

# Sair: \q

# Reiniciar FastAPI para limpar cache
sudo systemctl restart horariointeligente.service
```

---

## ✅ Checklist Final Hostinger

- [ ] IP da VPS anotado
- [ ] DNS configurado no painel Hostinger (A, www, *)
- [ ] DNS propagado (teste com `nslookup`)
- [ ] Nginx instalado e rodando
- [ ] Configuração Nginx criada e ativada
- [ ] FastAPI rodando (`systemctl status horariointeligente.service`)
- [ ] Firewall permite portas 80, 443, 22
- [ ] SSL instalado e funcionando (cadeado verde)
- [ ] Login funciona em https://drjoao.horariointeligente.com.br
- [ ] Logs sem erros

---

## 🎯 Comandos Resumidos (Copy/Paste)

```bash
# === VER IP DA VPS ===
curl ifconfig.me

# === CONFIGURAR NGINX ===
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/horariointeligente
# (colar conteúdo)
sudo ln -sf /etc/nginx/sites-available/horariointeligente /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# === INSTALAR SSL ===
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d horariointeligente.com.br -d www.horariointeligente.com.br -d drjoao.horariointeligente.com.br

# === VERIFICAR STATUS ===
sudo systemctl status nginx
sudo systemctl status horariointeligente.service

# === VER LOGS ===
sudo tail -f /var/log/nginx/horariointeligente_access.log
sudo journalctl -u horariointeligente.service -f

# === FIREWALL (se necessário) ===
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
```

---

## 🚀 Próximos Passos

Após configurar DNS + Nginx + SSL:

1. **Criar clínicas de teste:**
```sql
INSERT INTO clientes (nome, subdomain, whatsapp_instance, plano, ativo, criado_em, atualizado_em)
VALUES
('Clínica Pro-Saúde', 'prosaude', 'ProSaude', 'profissional', true, NOW(), NOW()),
('Dr. Marco Consultório', 'drmarco', 'ProSaude', 'basico', true, NOW(), NOW());
```

2. **Testar login em diferentes subdomínios**

3. **Configurar médicos para cada clínica**

4. **Testar WhatsApp (já funciona com número compartilhado!)**

---

## 📞 Suporte Hostinger

Se tiver problemas:

- **Chat 24/7:** https://hpanel.hostinger.com (botão de chat)
- **Tutoriais:** https://support.hostinger.com
- **Status:** https://www.hostingerstatus.com

---

**Tudo pronto! Agora é só seguir os passos! 🎉**
