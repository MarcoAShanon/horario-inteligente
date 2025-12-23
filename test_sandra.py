#!/usr/bin/env python3
"""Teste do comportamento da Sandra (IA)."""

import requests
import json
import time

webhook_url = "http://localhost:8000/webhook/whatsapp/ProSaude"

# Teste 1: Cliente envia primeira mensagem (IA NÃO deve chamar por nome)
print("=" * 60)
print("TESTE 1: Cliente se apresenta pela primeira vez")
print("=" * 60)

payload1 = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {"remoteJid": "5511988887777@s.whatsapp.net", "fromMe": False, "id": "TEST1"},
        "pushName": "Cliente Teste",
        "message": {"conversation": "Olá, gostaria de agendar uma consulta"},
        "messageType": "conversation",
        "messageTimestamp": int(time.time())
    }
}

print("\n📤 Cliente: 'Olá, gostaria de agendar uma consulta'")
response1 = requests.post(webhook_url, json=payload1, timeout=30)
print(f"✅ Status: {response1.status_code}")

time.sleep(2)

# Teste 2: Cliente informa o nome
print("\n" + "=" * 60)
print("TESTE 2: Cliente informa o nome")
print("=" * 60)

payload2 = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {"remoteJid": "5511988887777@s.whatsapp.net", "fromMe": False, "id": "TEST2"},
        "pushName": "Cliente Teste",
        "message": {"conversation": "Meu nome é Marco Aurélio"},
        "messageType": "conversation",
        "messageTimestamp": int(time.time())
    }
}

print("\n📤 Cliente: 'Meu nome é Marco Aurélio'")
response2 = requests.post(webhook_url, json=payload2, timeout=30)
print(f"✅ Status: {response2.status_code}")

print("\n" + "=" * 60)
print("💡 Verifique os logs para ver as respostas da Sandra:")
print("   journalctl -u prosaude.service -n 50 --no-pager | grep 'Resposta da IA'")
print("=" * 60)
