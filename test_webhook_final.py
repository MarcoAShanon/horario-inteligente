#!/usr/bin/env python3
"""Teste final do webhook com IA."""

import requests
import json

# Simular webhook do WhatsApp
webhook_url = "http://localhost:8000/webhook/whatsapp/ProSaude"

payload = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {
            "remoteJid": "5511999999999@s.whatsapp.net",
            "fromMe": False,
            "id": "TEST123"
        },
        "pushName": "Teste Bot",
        "message": {
            "conversation": "Olá, gostaria de agendar uma consulta"
        },
        "messageType": "conversation",
        "messageTimestamp": 1700000000
    }
}

print("🧪 Testando webhook com IA...")
print(f"📤 Enviando para: {webhook_url}")
print(f"📝 Mensagem: {payload['data']['message']['conversation']}")

try:
    response = requests.post(webhook_url, json=payload, timeout=30)
    print(f"\n✅ Status: {response.status_code}")

    if response.status_code == 200:
        print("✅✅✅ WEBHOOK FUNCIONOU!")
        print("\n💡 Verifique os logs para ver a resposta da IA:")
        print("   tail -20 /root/sistema_agendamento/logs/uvicorn.log")
    else:
        print(f"❌ Erro: {response.text}")

except Exception as e:
    print(f"❌ Erro na requisição: {e}")
