# 🔧 Correção de Download de Áudio - Evolution API v2.0.10

**Data:** 8 de dezembro de 2025
**Versão:** 3.5.2
**Status:** ✅ **IMPLEMENTADO - AGUARDANDO TESTE**

---

## 🐛 Problema Identificado

Após a primeira correção (detecção de áudio), um **segundo problema** foi encontrado:

### Erro Recebido:
```
❌ Erro ao processar áudio: Erro ao baixar da Evolution API: 400 -
{"status":400,"error":"Bad Request","response":{"message":["Message not found"]}}
```

### Análise:
- ✅ Sistema **detecta o áudio** corretamente
- ✅ Identifica que é **criptografado** (.enc)
- ❌ **Falha ao baixar** via Evolution API
- ❌ Endpoint `/chat/getBase64FromMediaMessage` retorna "Message not found"

**Causa:** A Evolution API v2.0.10 mudou a forma como lida com mídias criptografadas ou o endpoint não funciona da mesma forma.

---

## ✅ Solução Implementada

### Nova Estratégia de Download (Fallback Duplo)

**ANTES (Estratégia Única):**
```python
if ".enc" in audio_url:
    # Sempre usar Evolution API para descriptografar
    baixar_via_evolution_api()
else:
    # Download direto
    baixar_direto()
```

**DEPOIS (Estratégia com Fallback):**
```python
# 1. Tentar download direto SEMPRE primeiro
tentar_download_direto()

# 2. Se falhar E for criptografado, tentar Evolution API
if falhou and is_encrypted:
    tentar_evolution_api()
```

### Benefícios:
1. ✅ **Mais robusto** - Tenta duas formas
2. ✅ **Mais rápido** - Download direto é mais rápido
3. ✅ **Compatível** - Funciona se Evolution já descriptografou
4. ✅ **Fallback** - Se direto falhar, usa Evolution API

---

## 📋 Código Modificado

### Arquivo: `app/api/webhooks.py`
**Linhas:** 139-204

### Mudanças:

```python
# NOVA LÓGICA
logger.info(f"🎤 URL do áudio: {audio_url}")
audio_data = None
is_encrypted = ".enc" in audio_url

# ESTRATÉGIA V2.0.10: Tentar download direto primeiro
logger.info(f"📥 Tentando download direto do áudio{' (criptografado)' if is_encrypted else ''}...")

try:
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(audio_url) as response:
            if response.status == 200:
                audio_data = await response.read()
                logger.info(f"✅ Áudio baixado diretamente ({len(audio_data)} bytes)")
            else:
                logger.warning(f"⚠️ Download direto falhou: HTTP {response.status}")
except Exception as e:
    logger.warning(f"⚠️ Download direto falhou: {e}")

# Se download direto falhou E áudio é criptografado, tentar via Evolution API
if (not audio_data or len(audio_data) == 0) and is_encrypted:
    logger.info("🔐 Tentando baixar via Evolution API (áudio criptografado)...")
    # Tenta via Evolution API...
```

### Logs Esperados (Caso de Sucesso):
```
🔍 'messageType' field: audioMessage
🎤 Áudio detectado! (messageType=audioMessage, has_audioMessage=True)
🎤 URL do áudio: https://mmg.whatsapp.net/.../file.enc
📥 Tentando download direto do áudio (criptografado)...
✅ Áudio baixado diretamente (9629 bytes)
💾 Áudio salvo em: /tmp/tmpXXXXX.ogg (9629 bytes)
🎤 Enviando áudio diretamente para Whisper (OGG é suportado)
✅ Áudio transcrito: "sua mensagem aqui"
🎤 Entendi: "sua mensagem aqui"
```

---

## 🧹 Limpeza de Dados de Teste

### Telefone: 5524988493257 (Marco)

**Dados Limpos:**
- ✅ 3 agendamentos deletados
- ✅ Paciente mantido (ID: 1, Nome: Marco José)
- ✅ 1 conversa deletada do Redis

### Comandos Usados:
```sql
DELETE FROM agendamentos WHERE paciente_id = 1;
```

```bash
redis-cli KEYS "*5524988493257*" | xargs -r redis-cli DEL
```

---

## 🧪 Como Testar Agora

### 1. Verificar Serviço
```bash
sudo systemctl status horariointeligente.service
```
✅ Deve mostrar: `Active: active (running)`

### 2. Enviar Áudio de Teste
1. Abra o WhatsApp no telefone **5524988493257**
2. Envie um áudio curto (5-10 segundos)
3. Exemplo: "Olá, quero agendar uma consulta"

### 3. Monitorar Logs
```bash
journalctl -u horariointeligente.service -f | grep -E "áudio|Audio|Whisper|transcri"
```

### 4. Comportamento Esperado

**Se funcionar (✅):**
```
📥 Tentando download direto do áudio (criptografado)...
✅ Áudio baixado diretamente (XXXX bytes)
✅ Áudio transcrito: "sua mensagem aqui"
🎤 Entendi: "sua mensagem aqui"
[Claude processa e responde]
```

**Se ainda falhar (❌):**
```
📥 Tentando download direto do áudio (criptografado)...
⚠️ Download direto falhou: HTTP XXX
🔐 Tentando baixar via Evolution API (áudio criptografado)...
[veremos o erro da Evolution API]
```

---

## 🔍 Diagnóstico Adicional

Se o problema persistir, precisaremos:

### 1. Verificar Permissões da Evolution API
```bash
docker logs evolution_prosaude --tail 50 | grep -i media
```

### 2. Testar URL Diretamente
```bash
# Copiar URL do áudio dos logs e testar
curl -I "https://mmg.whatsapp.net/v/t62.7117-24/..."
```

### 3. Verificar Formato do Áudio
```python
# No audioMessage, verificar:
- mimetype: "audio/ogg; codecs=opus"
- fileLength: tamanho do arquivo
- seconds: duração
```

### 4. Possível Solução Alternativa

Se ambos métodos falharem, podemos implementar **descriptografia manual** usando as chaves do WhatsApp (complexo mas possível).

---

## 📊 Checklist de Validação

- [x] Código corrigido (estratégia de fallback)
- [x] Serviço reiniciado
- [x] Dados de teste limpos (agendamentos + Redis)
- [ ] **AGUARDANDO:** Teste com áudio real
- [ ] Verificar logs de sucesso
- [ ] Confirmar transcrição do Whisper
- [ ] Confirmar resposta da IA
- [ ] Confirmar envio ao usuário

---

## 💡 Por Que Isso Deve Funcionar

### Teoria:
A Evolution API v2.0.10 pode estar fornecendo URLs de áudio já **descriptografadas** no webhook, mesmo que o nome termine em `.enc`.

**Evidências:**
1. URL completa está no payload
2. Evolution API pode ter descriptografado automaticamente
3. Download direto é mais comum em APIs modernas
4. Fallback garante compatibilidade

### Se Não Funcionar:
Implementaremos descriptografia manual usando:
- `mediaKey` (fornecido no audioMessage)
- `fileEncSha256` (hash do arquivo)
- Biblioteca de criptografia AES-256

---

## 🎯 Próximos Passos

1. **Testar com áudio** pelo WhatsApp (5524988493257)
2. **Verificar logs** para confirmar sucesso/falha
3. **Se falhar:** Analisar logs detalhados
4. **Se funcionar:** ✅ Correção completa!

---

## 📞 Comandos Úteis

### Ver Logs em Tempo Real
```bash
journalctl -u horariointeligente.service -f
```

### Ver Últimas Mensagens
```bash
journalctl -u horariointeligente.service --since "5 minutes ago" | grep áudio
```

### Status do WhatsApp
```bash
curl http://localhost:8080/instance/connectionState/ProSaude \
  -H "apikey: evolution-api-prosaude-123"
```

### Reiniciar se Necessário
```bash
sudo systemctl restart horariointeligente.service
```

---

**Desenvolvido por:** Marco (com Claude Code)
**Versão:** 3.5.2 - Correção de Download de Áudio
**Status:** ✅ Implementado - Pronto para Teste

🎉 **Sistema pronto para teste! Envie um áudio agora!**
