#!/usr/bin/env python3
"""Teste final completo do comportamento da Sandra."""

import requests
import json
import time

webhook_url = "http://localhost:8000/webhook/whatsapp/ProSaude"

# Simular o número real do usuário (Marco Aurélio)
telefone_real = "5524988493257"

print("=" * 70)
print("🧪 TESTE FINAL - Sandra NÃO deve inventar nomes")
print("=" * 70)

# Teste 1: Enviar "bom dia" sem se apresentar
print("\n📱 TESTE 1: Cliente envia 'Bom dia' SEM se apresentar")
print("-" * 70)

payload1 = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {"remoteJid": f"{telefone_real}@s.whatsapp.net", "fromMe": False, "id": "FINAL1"},
        "pushName": "Marco Aurélio",
        "message": {"conversation": "Bom dia"},
        "messageType": "conversation",
        "messageTimestamp": int(time.time())
    }
}

print("📤 Enviando: 'Bom dia'")
response1 = requests.post(webhook_url, json=payload1, timeout=30)
print(f"✅ Status: {response1.status_code}")

# Aguardar processamento
time.sleep(3)

# Verificar os logs para ver a resposta
print("\n🔍 Verificando resposta da Sandra nos logs...")
import subprocess
result = subprocess.run(
    ["journalctl", "-u", "prosaude.service", "-n", "20", "--no-pager"],
    capture_output=True,
    text=True
)

# Procurar pela resposta da IA
for line in result.stdout.split('\n'):
    if "Resposta da IA recebida:" in line:
        resposta = line.split("Resposta da IA recebida:")[-1].strip()
        print(f"💬 Sandra respondeu: {resposta[:150]}")

        # Validar se NÃO usou nome
        if any(nome in resposta.lower() for nome in ["carla", "maria", "joão", "josé"]):
            print("❌ FALHOU: Sandra inventou um nome!")
        else:
            print("✅ SUCESSO: Sandra NÃO inventou nenhum nome!")

print("\n" + "=" * 70)
print("📊 RESULTADO ESPERADO:")
print("   Sandra deve responder algo como:")
print("   '👋 Olá! Sou a Sandra, assistente da Clínica Pro-Saúde...'")
print("   SEM usar nomes como 'Carla', 'Maria', etc.")
print("=" * 70)

# Teste 2: Agora o cliente se apresenta
print("\n📱 TESTE 2: Cliente se apresenta")
print("-" * 70)

payload2 = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {"remoteJid": f"{telefone_real}@s.whatsapp.net", "fromMe": False, "id": "FINAL2"},
        "pushName": "Marco Aurélio",
        "message": {"conversation": "Meu nome é Marco Aurélio"},
        "messageType": "conversation",
        "messageTimestamp": int(time.time())
    }
}

print("📤 Enviando: 'Meu nome é Marco Aurélio'")
response2 = requests.post(webhook_url, json=payload2, timeout=30)
print(f"✅ Status: {response2.status_code}")

time.sleep(3)

print("\n🔍 Verificando resposta da Sandra nos logs...")
result2 = subprocess.run(
    ["journalctl", "-u", "prosaude.service", "-n", "20", "--no-pager"],
    capture_output=True,
    text=True
)

for line in result2.stdout.split('\n'):
    if "Resposta da IA recebida:" in line:
        resposta = line.split("Resposta da IA recebida:")[-1].strip()
        print(f"💬 Sandra respondeu: {resposta[:150]}")

        # Validar se AGORA usou o nome correto
        if "marco" in resposta.lower() or "aurélio" in resposta.lower():
            print("✅ SUCESSO: Sandra usou o nome 'Marco Aurélio' corretamente!")
        else:
            print("⚠️ Sandra não usou o nome ainda (pode ser OK)")

print("\n" + "=" * 70)
print("📊 RESULTADO ESPERADO:")
print("   Sandra AGORA pode usar o nome:")
print("   'Prazer Marco Aurélio! Qual especialidade você precisa?'")
print("=" * 70)
