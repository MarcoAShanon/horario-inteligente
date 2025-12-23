#!/usr/bin/env python3
"""
Script para corrigir a função de envio no webhooks.py
Executa correção inline sem precisar editar o arquivo todo
"""

import os

# Novo código da função send_whatsapp_response corrigida
FIXED_FUNCTION = '''
async def send_whatsapp_response(instance_name: str, to_number: str, message: str) -> bool:
    """
    Envia resposta via Evolution API v1.7.4
    """
    try:
        # Garantir que o número está no formato correto (sem @s.whatsapp.net)
        to_number = to_number.replace('@s.whatsapp.net', '').replace('@g.us', '')
        
        # Se não tem código do país, adicionar +55 para Brasil
        if not to_number.startswith('+'):
            if not to_number.startswith('55'):
                to_number = '55' + to_number
        
        url = f"{EVOLUTION_API_URL}/message/sendText/{instance_name}"
        
        # Formato correto para Evolution API v1.7.4
        payload = {
            "number": to_number,
            "textMessage": {
                "text": message
            },
            "options": {
                "delay": 1000,
                "presence": "composing"
            }
        }
        
        headers = {
            "apikey": EVOLUTION_API_KEY,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Enviando mensagem para {to_number}")
        logger.debug(f"Payload: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    logger.info(f"Mensagem enviada com sucesso: {result.get('id', 'OK')}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Erro ao enviar mensagem: {response.status} - {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"Erro ao enviar resposta WhatsApp: {e}", exc_info=True)
        return False
'''

def fix_webhook_file():
    """Corrige o arquivo webhooks.py"""
    webhook_file = "/root/sistema_agendamento/app/api/webhooks.py"
    
    print("📝 Lendo arquivo webhooks.py...")
    with open(webhook_file, 'r') as f:
        content = f.read()
    
    # Encontrar e substituir a função send_whatsapp_response
    import_marker = "async def send_whatsapp_response"
    
    if import_marker in content:
        print("✅ Função encontrada, aplicando correção...")
        
        # Encontrar início e fim da função
        start_idx = content.find(import_marker)
        
        # Encontrar o próximo 'async def' ou 'def' após esta função
        next_func_idx = content.find("\nasync def", start_idx + 1)
        if next_func_idx == -1:
            next_func_idx = content.find("\ndef", start_idx + 1)
        
        # Se não encontrou próxima função, pode ser a última
        if next_func_idx == -1:
            # Procurar por marcadores de fim comuns
            next_func_idx = content.find("\n# Rota adicional", start_idx)
            if next_func_idx == -1:
                next_func_idx = content.find("\n@router", start_idx)
                if next_func_idx == -1:
                    next_func_idx = len(content)
        
        # Substituir a função
        new_content = (
            content[:start_idx] + 
            FIXED_FUNCTION.strip() + 
            "\n\n" +
            content[next_func_idx:]
        )
        
        # Backup
        print("💾 Fazendo backup...")
        with open(webhook_file + ".bak2", 'w') as f:
            f.write(content)
        
        # Salvar correção
        print("💾 Salvando correção...")
        with open(webhook_file, 'w') as f:
            f.write(new_content)
        
        print("✅ Correção aplicada com sucesso!")
        return True
    else:
        print("❌ Função não encontrada no formato esperado")
        print("   Vamos adicionar a função corrigida ao final do arquivo...")
        
        # Adicionar função ao final
        with open(webhook_file, 'a') as f:
            f.write("\n\n" + FIXED_FUNCTION)
        
        print("✅ Função adicionada!")
        return True

def test_fix():
    """Testa se a correção funcionou"""
    import requests
    import json
    
    print("\n🧪 Testando correção...")
    
    # Teste 1: Envio direto via Evolution
    print("1. Testando envio direto...")
    r = requests.post(
        "http://localhost:8082/message/sendText/prosaude-whatsapp",
        headers={"apikey": "evolution-api-prosaude-123"},
        json={
            "number": "5521992086879",
            "textMessage": {
                "text": "✅ Correção aplicada! Mensagem de teste."
            }
        }
    )
    
    if r.status_code in [200, 201]:
        print("   ✅ Envio direto funcionando!")
    else:
        print(f"   ❌ Erro: {r.status_code} - {r.text}")
    
    # Teste 2: Webhook
    print("2. Testando webhook...")
    r = requests.post(
        "http://localhost:8000/webhook/whatsapp/prosaude-whatsapp",
        json={
            "event": "messages.upsert",
            "instance": "prosaude-whatsapp",
            "data": {
                "key": {
                    "remoteJid": "5521992086879@s.whatsapp.net",
                    "fromMe": False
                },
                "message": {
                    "conversation": "oi"
                },
                "pushName": "Teste Correção"
            }
        }
    )
    
    response = r.json()
    if response.get('status') == 'success':
        print("   ✅ Webhook processando e enviando!")
    else:
        print(f"   ⚠️ Status: {response}")

if __name__ == "__main__":
    print("="*60)
    print("  CORREÇÃO AUTOMÁTICA - Evolution API v1.7.4")
    print("="*60)
    
    if fix_webhook_file():
        print("\n⚠️ IMPORTANTE: Reinicie o servidor para aplicar as mudanças!")
        print("   1. No terminal do servidor: Ctrl+C")
        print("   2. Reiniciar: python3 app/main.py")
        print("\nOu use: pkill -f main.py && python3 app/main.py &")
        
        test_fix()
