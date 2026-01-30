# 🔧 Correção de Áudio - Evolution API v2.0.10

**Data:** 8 de dezembro de 2025
**Problema:** Sistema não processa áudios recebidos após atualização para Evolution API v2.0.10
**Causa:** Mudança na estrutura do payload do webhook

---

## 📋 Problema Identificado

### Estrutura Evolution API v1.7.4 (Antiga)
```json
{
  "data": {
    "key": {...},
    "message": {
      "audioMessage": {
        "url": "...",
        ...
      }
    }
  }
}
```

### Estrutura Evolution API v2.0.10 (Nova)
```json
{
  "data": {
    "key": {...},
    "pushName": "Nome",
    "message": {
      "audioMessage": {
        "url": "...",
        ...
      }
    },
    "messageType": "audioMessage",  ← NOVO CAMPO!
    "messageTimestamp": 123456,
    "owner": "ProSaude",
    "source": "android"
  }
}
```

**Mudanças principais:**
1. ✅ `audioMessage` ainda existe dentro de `message`
2. ✅ **NOVO:** Campo `messageType` indica o tipo diretamente
3. ✅ Campos adicionais: `owner`, `source`

---

## 🐛 Bug no Código Atual

O código atual detecta áudio corretamente:

```python
# Linha 854-866 de webhooks.py
if isinstance(message, dict) and 'audioMessage' in message:
    audio_msg = message['audioMessage']
    audio_url = audio_msg.get('url')

    return {
        'sender': sender,
        'text': None,
        'push_name': push_name,
        'message_type': 'audio',
        'audio_url': audio_url
    }
```

**PORÉM**, o problema pode estar em:
1. Como `audioMessage` é estruturado na v2.0.10
2. URL do áudio pode estar em lugar diferente
3. Necessidade de usar `messageType` para detecção mais robusta

---

## ✅ Solução

### 1. Melhorar Detecção de Áudio

Usar AMBOS os métodos de detecção:
- Campo `messageType` (novo, mais confiável)
- Campo `audioMessage` (antigo, compatibilidade)

### 2. Código Corrigido

```python
def extract_message_info(webhook_data: dict) -> Optional[Dict[str, Any]]:
    """
    Extrai informações da mensagem (Evolution API v2.0.10)
    Suporta: texto e áudio
    """
    try:
        logger.info(f"🔍 Extraindo info da mensagem...")

        if 'data' in webhook_data:
            data = webhook_data['data']
            logger.info(f"🔍 'data' encontrado, chaves: {list(data.keys())}")

            if 'message' in data:
                message = data['message']
                key = data.get('key', {})
                message_type = data.get('messageType', '')  # ← NOVO!

                logger.info(f"🔍 'message' encontrado, tipo: {type(message)}")
                logger.info(f"🔍 'messageType' field: {message_type}")  # ← NOVO LOG!

                # Ignorar mensagens do bot
                if key.get('fromMe', False):
                    logger.info(f"🔍 Mensagem ignorada: é do bot (fromMe=True)")
                    return None

                # Extrair informações comuns
                sender = key.get('remoteJid', '').replace('@s.whatsapp.net', '')
                push_name = data.get('pushName', 'Cliente')

                # ========================================
                # 1. DETECTAR ÁUDIO (MELHORADO)
                # ========================================
                # Método 1: Usar novo campo messageType (v2.0.10)
                is_audio_by_type = message_type in ['audioMessage', 'audio', 'ptt']

                # Método 2: Verificar estrutura antiga (compatibilidade)
                has_audio_message = isinstance(message, dict) and 'audioMessage' in message

                if is_audio_by_type or has_audio_message:
                    logger.info(f"🎤 Áudio detectado! (messageType={message_type}, has_audioMessage={has_audio_message})")

                    audio_msg = message.get('audioMessage', {})
                    audio_url = audio_msg.get('url')

                    # Tentar outros campos possíveis
                    if not audio_url:
                        audio_url = audio_msg.get('directPath') or audio_msg.get('mediaUrl')

                    logger.info(f"🎤 URL do áudio: {audio_url}")

                    return {
                        'sender': sender,
                        'text': None,
                        'push_name': push_name,
                        'message_type': 'audio',
                        'audio_url': audio_url,
                        'audio_msg': audio_msg  # ← Enviar objeto completo para debug
                    }

                # ========================================
                # 2. DETECTAR TEXTO
                # ========================================
                extracted_text = None
                if isinstance(message, dict):
                    extracted_text = (
                        message.get('conversation') or
                        message.get('text') or
                        (message.get('extendedTextMessage', {}).get('text'))
                    )
                elif isinstance(message, str):
                    extracted_text = message

                logger.info(f"🔍 Texto extraído: '{extracted_text}'")

                if extracted_text:
                    return {
                        'sender': sender,
                        'text': extracted_text,
                        'push_name': push_name,
                        'message_type': 'text'
                    }

        logger.info(f"🔍 Nenhuma mensagem válida encontrada")
        return None

    except Exception as e:
        logger.error(f"Erro ao extrair mensagem: {e}", exc_info=True)
        return None
```

### 3. Logs Melhorados

Adicionar mais logs para debug:
- Mostrar campo `messageType`
- Mostrar estrutura completa de `audioMessage`
- Logar todas as chaves disponíveis

---

## 🧪 Como Testar

### Passo 1: Aplicar Correção
```bash
# Editar arquivo
vim /root/sistema_agendamento/app/api/webhooks.py

# Reiniciar serviço
sudo systemctl restart horariointeligente.service
```

### Passo 2: Enviar Áudio de Teste
1. Enviar áudio curto (5-10s) pelo WhatsApp
2. Verificar logs:
```bash
journalctl -u horariointeligente.service -f | grep -E "áudio|audio|messageType"
```

### Passo 3: Verificar Logs Esperados
```
🔍 'messageType' field: audioMessage
🎤 Áudio detectado! (messageType=audioMessage, has_audioMessage=True)
🎤 URL do áudio: https://...
📥 Baixando áudio...
✅ Áudio transcrito: "texto da transcrição"
```

---

## 🔍 Possíveis Problemas Adicionais

Se após a correção ainda não funcionar, verificar:

### 1. URL do Áudio Criptografada
```python
# audioMessage pode ter:
{
  "url": "https://..../file.enc",  # Criptografada
  "mediaKey": "base64...",
  "directPath": "/v/..."
}
```

**Solução:** Usar endpoint da Evolution API para baixar áudio descriptografado.

### 2. Formato do Áudio
```python
# Verificar mimetype
audio_msg.get('mimetype')  # "audio/ogg; codecs=opus"
```

**Solução:** Whisper aceita OGG nativamente.

### 3. ENABLE_AUDIO_INPUT Desabilitado
```bash
# Verificar .env
grep ENABLE_AUDIO_INPUT .env
# Deve retornar: ENABLE_AUDIO_INPUT=true
```

---

## 📊 Checklist de Validação

- [ ] Código corrigido em `webhooks.py`
- [ ] Serviço reiniciado
- [ ] Áudio de teste enviado
- [ ] Logs mostram detecção de áudio
- [ ] Transcrição funcionando
- [ ] Resposta da IA processada
- [ ] Resposta enviada ao usuário

---

**Status:** ⚠️ Aguardando Implementação
**Próximo Passo:** Aplicar correção e testar
