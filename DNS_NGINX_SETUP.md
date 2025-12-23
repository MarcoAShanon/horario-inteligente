# 🌐 Guia de Configuração DNS + Nginx + SSL - Horário Inteligente

**Domínio:** horariointeligente.com.br
**Data:** 30/11/2025
**Status:** 🚀 Pronto para produção

---

## 📋 Pré-requisitos

✅ Domínio registrado: `horariointeligente.com.br`
✅ Sistema multi-tenant implementado
✅ Servidor rodando: FastAPI na porta 8000
✅ IP do servidor: _[descobriremos]_

---

## 🎯 Passo 1: Descobrir IP do Servidor

```bash
# No servidor, execute:
curl ifconfig.me

# Ou
hostname -I | awk '{print $1}'
```

**Anote o IP:** `___.___.___.___ ` ← Vamos usar esse IP

---

## 🌐 Passo 2: Configurar DNS (Wildcard)

### Opção A: Registro.br (Se domínio foi registrado lá)

1. Acesse: https://registro.br
2. Login com CPF/CNPJ
3. Clique em **"Domínios" → "horariointeligente.com.br"**
4. Vá em **"DNS" → "Editar Zona"**
5. Adicione os seguintes registros:

```dns
# Registro A - Domínio principal
@ IN A SEU_IP_AQUI
TTL: 3600

# Registro A - www
www IN A SEU_IP_AQUI
TTL: 3600

# Registro A - Wildcard (ESSENCIAL PARA MULTI-TENANT!)
* IN A SEU_IP_AQUI
TTL: 3600
```

**Exemplo com IP 200.100.50.10:**
```
@   IN A 200.100.50.10
www IN A 200.100.50.10
*   IN A 200.100.50.10
```

**Resultado:**
- `horariointeligente.com.br` → 200.100.50.10
- `www.horariointeligente.com.br` → 200.100.50.10
- `prosaude.horariointeligente.com.br` → 200.100.50.10 ✅
- `drmarco.horariointeligente.com.br` → 200.100.50.10 ✅
- `qualquercoisa.horariointeligente.com.br` → 200.100.50.10 ✅

---

### Opção B: Cloudflare (Recomendado - Grátis + CDN + DDoS Protection)

1. Acesse: https://dash.cloudflare.com
2. Cadastre-se (grátis)
3. Clique em **"Add a Site"**
4. Digite: `horariointeligente.com.br`
5. Escolha o plano **"Free"**
6. Cloudflare vai escanear DNS atual
7. Adicione os registros:

```
Tipo: A
Nome: @
Conteúdo: SEU_IP
Proxy: ✅ Ativado (nuvem laranja)
TTL: Auto

Tipo: A
Nome: www
Conteúdo: SEU_IP
Proxy: ✅ Ativado
TTL: Auto

Tipo: A
Nome: *
Conteúdo: SEU_IP
Proxy: ✅ Ativado (WILDCARD!)
TTL: Auto
```

8. Cloudflare vai fornecer nameservers:
```
ns1.cloudflare.com
ns2.cloudflare.com
```

9. **IMPORTANTE:** Vá no Registro.br e atualize os nameservers:
   - Acesse Registro.br
   - Domínios → horariointeligente.com.br
   - DNS → Usar outro provedor
   - Cole os nameservers do Cloudflare

10. Aguarde propagação (15min - 48h, geralmente < 1 hora)

---

### Como verificar se DNS está funcionando:

```bash
# Teste 1: Domínio principal
nslookup horariointeligente.com.br

# Teste 2: Subdomínio existente
nslookup prosaude.horariointeligente.com.br

# Teste 3: Subdomínio qualquer (wildcard)
nslookup teste123.horariointeligente.com.br

# Todos devem retornar o mesmo IP!
```

---

## 🔧 Passo 3: Configurar Nginx

### 3.1 Verificar se Nginx está instalado

```bash
nginx -v

# Se não estiver instalado:
sudo apt update
sudo apt install nginx -y
```

### 3.2 Criar configuração para multi-tenant

```bash
# Criar arquivo de configuração
sudo nano /etc/nginx/sites-available/horariointeligente
```

**Cole este conteúdo:**

```nginx
# Configuração Multi-Tenant - Horário Inteligente
# Captura QUALQUER subdomínio (*.horariointeligente.com.br)

server {
    listen 80;
    listen [::]:80;

    # Captura qualquer subdomínio + domínio principal
    server_name horariointeligente.com.br *.horariointeligente.com.br;

    # Logs separados
    access_log /var/log/nginx/horariointeligente_access.log;
    error_log /var/log/nginx/horariointeligente_error.log;

    # Tamanho máximo de upload (para futuras imagens)
    client_max_body_size 10M;

    # Proxy para FastAPI (porta 8000)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # Headers essenciais
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout (ajustar se IA demorar muito)
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }

    # Servir arquivos estáticos diretamente (performance)
    location /static/ {
        alias /root/sistema_agendamento/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        access_log off;
        return 200 "OK";
    }
}
```

**Salvar:** `Ctrl + O` → `Enter` → `Ctrl + X`

### 3.3 Ativar configuração

```bash
# Criar link simbólico
sudo ln -sf /etc/nginx/sites-available/horariointeligente /etc/nginx/sites-enabled/

# Remover configuração padrão (opcional)
sudo rm -f /etc/nginx/sites-enabled/default

# Testar configuração
sudo nginx -t

# Se aparecer "test is successful", pode prosseguir!

# Reiniciar Nginx
sudo systemctl restart nginx

# Verificar status
sudo systemctl status nginx
```

---

## 🔒 Passo 4: Configurar SSL/HTTPS (Certbot - Let's Encrypt)

### 4.1 Instalar Certbot

```bash
# Instalar certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx -y
```

### 4.2 Gerar certificados SSL

```bash
# Gerar certificados para domínio principal + wildcard
sudo certbot --nginx -d horariointeligente.com.br -d *.horariointeligente.com.br

# OU se quiser especificar subdomínios (sem wildcard):
sudo certbot --nginx -d horariointeligente.com.br -d www.horariointeligente.com.br -d prosaude.horariointeligente.com.br -d drmarco.horariointeligente.com.br
```

**Durante a instalação, responda:**
```
Email: seu-email@exemplo.com
Termos de Serviço: A (Agree)
Compartilhar email com EFF: Y ou N (opcional)
Redirect HTTP → HTTPS: 2 (Sim, redirecionar sempre)
```

**Certbot vai:**
1. Validar que você controla o domínio
2. Gerar certificados SSL (válidos por 90 dias)
3. Atualizar automaticamente a configuração Nginx
4. Configurar renovação automática

### 4.3 Testar renovação automática

```bash
# Testar renovação (dry-run, não renova de verdade)
sudo certbot renew --dry-run

# Se aparecer "Congratulations", está tudo OK!
```

**Renovação automática:** Certbot cria um cron job que renova automaticamente a cada 90 dias.

---

## ✅ Passo 5: Validar Configuração

### 5.1 Verificar Nginx

```bash
# Status do Nginx
sudo systemctl status nginx

# Ver logs em tempo real
sudo tail -f /var/log/nginx/horariointeligente_access.log
```

### 5.2 Verificar FastAPI rodando

```bash
# Status do serviço ProSaude
sudo systemctl status prosaude.service

# Deve estar "active (running)"
```

### 5.3 Testar no navegador

**1. Domínio principal:**
```
https://horariointeligente.com.br
```
**Esperado:** Página de status do sistema ou redirecionamento

**2. Subdomínio existente:**
```
https://prosaude.horariointeligente.com.br/static/login.html
```
**Esperado:** Tela de login

**3. API Test:**
```
https://prosaude.horariointeligente.com.br/webhook/whatsapp/test
```
**Esperado:** JSON com status do sistema

**4. Criar novo subdomínio (teste):**

```sql
-- No banco de dados
INSERT INTO clientes (nome, subdomain, whatsapp_instance, plano, ativo, criado_em, atualizado_em)
VALUES ('Dr. Marco Teste', 'drmarco', 'ProSaude', 'profissional', true, NOW(), NOW());
```

```
https://drmarco.horariointeligente.com.br/static/login.html
```
**Esperado:** Tela de login (mesmo sem ter configurado DNS específico - wildcard funciona!)

---

## 🧪 Passo 6: Testes Multi-Tenant

### Teste 1: Middleware capturando subdomínio

```bash
# Ver logs do FastAPI
sudo journalctl -u prosaude.service -f

# Em outro terminal, acesse:
curl https://prosaude.horariointeligente.com.br/webhook/whatsapp/test

# Nos logs, deve aparecer:
# "🏢 TenantMiddleware ativado - Sistema Multi-Tenant ATIVO"
```

### Teste 2: Subdomínios diferentes = clientes diferentes

```bash
# Teste 1: ProSaude
curl https://prosaude.horariointeligente.com.br/webhook/whatsapp/test | jq

# Teste 2: DrMarco (se criou no banco)
curl https://drmarco.horariointeligente.com.br/webhook/whatsapp/test | jq

# Deve retornar cliente_id diferentes!
```

### Teste 3: Login com isolamento

```bash
# Fazer login na clínica ProSaude
curl -X POST https://prosaude.horariointeligente.com.br/api/auth/login \
  -F "username=admin@prosaude.com" \
  -F "password=admin123"

# Pegar o token e testar agendamentos
TOKEN="cole-o-token-aqui"

curl -H "Authorization: Bearer $TOKEN" \
  https://prosaude.horariointeligente.com.br/api/agendamentos/calendario
```

---

## 🔥 Troubleshooting

### Problema 1: DNS não propaga

**Sintoma:** `nslookup` não retorna o IP correto

**Solução:**
```bash
# Limpar cache DNS local
sudo systemd-resolve --flush-caches

# Testar com DNS público do Google
nslookup horariointeligente.com.br 8.8.8.8

# Aguardar até 48h (geralmente < 1h)
```

### Problema 2: Nginx 502 Bad Gateway

**Sintoma:** Site carrega mas mostra erro 502

**Causa:** FastAPI não está rodando ou na porta errada

**Solução:**
```bash
# Verificar se FastAPI está rodando
sudo systemctl status prosaude.service

# Se não estiver, iniciar
sudo systemctl start prosaude.service

# Verificar porta
sudo netstat -tlnp | grep 8000

# Deve mostrar Python escutando na porta 8000
```

### Problema 3: SSL não funciona

**Sintoma:** Certificado inválido ou não carrega HTTPS

**Solução:**
```bash
# Verificar certificados
sudo certbot certificates

# Se expirado ou problema, renovar
sudo certbot renew --force-renewal

# Reiniciar Nginx
sudo systemctl restart nginx
```

### Problema 4: Wildcard não funciona

**Sintoma:** `prosaude.horariointeligente.com.br` funciona, mas `drmarco.horariointeligente.com.br` não

**Causa:** Wildcard DNS não configurado ou Nginx não captura

**Solução:**
```bash
# Verificar DNS
nslookup qualquercoisa.horariointeligente.com.br

# Verificar Nginx
sudo nginx -T | grep server_name

# Deve aparecer: server_name horariointeligente.com.br *.horariointeligente.com.br;
```

### Problema 5: Tenant não identificado

**Sintoma:** Erro "Tenant não identificado"

**Causa:** Subdomínio não existe no banco

**Solução:**
```sql
-- Verificar clientes
SELECT id, nome, subdomain FROM clientes;

-- Se subdomínio não existir, criar
INSERT INTO clientes (nome, subdomain, whatsapp_instance, plano, ativo, criado_em, atualizado_em)
VALUES ('Nome da Clínica', 'subdominio', 'InstanciaNome', 'profissional', true, NOW(), NOW());

-- Limpar cache do middleware
# Reiniciar FastAPI
sudo systemctl restart prosaude.service
```

---

## 🎯 Checklist Final

Antes de considerar produção:

- [ ] DNS propagado (teste com `nslookup`)
- [ ] Nginx rodando (`sudo systemctl status nginx`)
- [ ] FastAPI rodando (`sudo systemctl status prosaude.service`)
- [ ] SSL válido (cadeado verde no navegador)
- [ ] Wildcard funcionando (teste subdomínios aleatórios)
- [ ] Login funciona em diferentes subdomínios
- [ ] WhatsApp recebe e responde
- [ ] Logs sem erros (`journalctl -u prosaude.service`)
- [ ] Firewall permite portas 80 e 443
- [ ] Backup configurado

---

## 🔒 Segurança Extra (Recomendado)

### 1. Firewall (UFW)

```bash
# Instalar UFW
sudo apt install ufw -y

# Permitir SSH (IMPORTANTE!)
sudo ufw allow 22/tcp

# Permitir HTTP
sudo ufw allow 80/tcp

# Permitir HTTPS
sudo ufw allow 443/tcp

# Ativar firewall
sudo ufw enable

# Verificar status
sudo ufw status
```

### 2. Fail2Ban (proteção contra brute force)

```bash
# Instalar
sudo apt install fail2ban -y

# Iniciar
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

### 3. Headers de segurança no Nginx

Edite `/etc/nginx/sites-available/horariointeligente`:

```nginx
# Adicionar dentro do bloco server { }

# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
```

Depois reiniciar Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 📊 Monitoramento

### Ver logs em tempo real:

```bash
# Nginx access
sudo tail -f /var/log/nginx/horariointeligente_access.log

# Nginx errors
sudo tail -f /var/log/nginx/horariointeligente_error.log

# FastAPI
sudo journalctl -u prosaude.service -f

# Tudo junto (3 terminais)
```

### Estatísticas:

```bash
# Requests por IP
sudo awk '{print $1}' /var/log/nginx/horariointeligente_access.log | sort | uniq -c | sort -rn | head -10

# Status codes
sudo awk '{print $9}' /var/log/nginx/horariointeligente_access.log | sort | uniq -c | sort -rn
```

---

## 🚀 Está pronto!

Após seguir todos os passos, seu sistema estará:

✅ Acessível via HTTPS
✅ Multi-tenant funcional
✅ SSL automático (renova sozinho)
✅ Protegido com firewall
✅ Logs monitorados
✅ Pronto para produção!

**URLs de exemplo funcionando:**
- https://horariointeligente.com.br
- https://prosaude.horariointeligente.com.br
- https://drmarco.horariointeligente.com.br
- https://qualquercoisa.horariointeligente.com.br (wildcard!)

---

**Próximo passo:** Criar clínicas de teste e validar tudo! 🎉
