#!/usr/bin/env python3
"""Teste para validar correção do pushName e captura de telefone."""

import requests
import json
import time
import subprocess

webhook_url = "http://localhost:8000/webhook/whatsapp/ProSaude"

print("=" * 80)
print("🧪 TESTE: Correção pushName + Captura de Telefone")
print("=" * 80)

# Teste 1: Simular conversa completa com agendamento
print("\n📱 TESTE 1: Conversa completa com nome fornecido")
print("-" * 80)

telefone_teste = "5511987654321"

# Mensagem 1: Saudação
payload1 = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {"remoteJid": f"{telefone_teste}@s.whatsapp.net", "fromMe": False, "id": "T1"},
        "pushName": "Zé Bonitão",  # Nome do WhatsApp (apelido)
        "message": {"conversation": "Olá, quero agendar"},
        "messageType": "conversation",
        "messageTimestamp": int(time.time())
    }
}

print("📤 Enviando: 'Olá, quero agendar'")
print(f"   pushName do WhatsApp: 'Zé Bonitão' (apelido)")
print(f"   Telefone: {telefone_teste}")
response1 = requests.post(webhook_url, json=payload1, timeout=30)
print(f"✅ Status: {response1.status_code}")
time.sleep(3)

# Mensagem 2: Fornecendo nome REAL
payload2 = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {"remoteJid": f"{telefone_teste}@s.whatsapp.net", "fromMe": False, "id": "T2"},
        "pushName": "Zé Bonitão",  # Ainda com apelido no WhatsApp
        "message": {"conversation": "Meu nome é José Carlos Silva"},
        "messageType": "conversation",
        "messageTimestamp": int(time.time())
    }
}

print("\n📤 Enviando: 'Meu nome é José Carlos Silva'")
print(f"   pushName continua: 'Zé Bonitão'")
response2 = requests.post(webhook_url, json=payload2, timeout=30)
print(f"✅ Status: {response2.status_code}")
time.sleep(3)

# Mensagem 3: Especialidade
payload3 = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {"remoteJid": f"{telefone_teste}@s.whatsapp.net", "fromMe": False, "id": "T3"},
        "pushName": "Zé Bonitão",
        "message": {"conversation": "Preciso de cardiologista"},
        "messageType": "conversation",
        "messageTimestamp": int(time.time())
    }
}

print("\n📤 Enviando: 'Preciso de cardiologista'")
response3 = requests.post(webhook_url, json=payload3, timeout=30)
print(f"✅ Status: {response3.status_code}")
time.sleep(3)

# Mensagem 4: Convênio
payload4 = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {"remoteJid": f"{telefone_teste}@s.whatsapp.net", "fromMe": False, "id": "T4"},
        "pushName": "Zé Bonitão",
        "message": {"conversation": "Unimed"},
        "messageType": "conversation",
        "messageTimestamp": int(time.time())
    }
}

print("\n📤 Enviando: 'Unimed'")
response4 = requests.post(webhook_url, json=payload4, timeout=30)
print(f"✅ Status: {response4.status_code}")
time.sleep(3)

# Mensagem 5: Data
payload5 = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {"remoteJid": f"{telefone_teste}@s.whatsapp.net", "fromMe": False, "id": "T5"},
        "pushName": "Zé Bonitão",
        "message": {"conversation": "15/11/2025"},
        "messageType": "conversation",
        "messageTimestamp": int(time.time())
    }
}

print("\n📤 Enviando: '15/11/2025'")
response5 = requests.post(webhook_url, json=payload5, timeout=30)
print(f"✅ Status: {response5.status_code}")
time.sleep(3)

# Mensagem 6: Horário
payload6 = {
    "event": "messages.upsert",
    "instance": "ProSaude",
    "data": {
        "key": {"remoteJid": f"{telefone_teste}@s.whatsapp.net", "fromMe": False, "id": "T6"},
        "pushName": "Zé Bonitão",
        "message": {"conversation": "14:00"},
        "messageType": "conversation",
        "messageTimestamp": int(time.time())
    }
}

print("\n📤 Enviando: '14:00'")
response6 = requests.post(webhook_url, json=payload6, timeout=30)
print(f"✅ Status: {response6.status_code}")
time.sleep(3)

print("\n" + "=" * 80)
print("📊 VERIFICANDO BANCO DE DADOS")
print("=" * 80)

# Verificar no banco de dados
result = subprocess.run(
    ["sudo", "-u", "postgres", "psql", "-d", "agendamento_saas", "-c",
     f"SELECT nome, telefone, convenio FROM pacientes WHERE telefone = '{telefone_teste}';"],
    capture_output=True,
    text=True
)

print("\n🔍 Resultado da consulta ao banco:")
print(result.stdout)

# Validações
if "José Carlos Silva" in result.stdout:
    print("✅ SUCESSO: Nome REAL foi salvo (José Carlos Silva)")
    print("✅ pushName 'Zé Bonitão' NÃO foi usado!")
elif "Zé Bonitão" in result.stdout:
    print("❌ FALHOU: pushName 'Zé Bonitão' foi salvo (errado!)")
else:
    print("⚠️  Paciente não encontrado no banco")

if telefone_teste in result.stdout:
    print("✅ SUCESSO: Telefone foi capturado e salvo corretamente!")
else:
    print("❌ FALHOU: Telefone não foi salvo")

print("\n" + "=" * 80)
print("📋 RESUMO DO TESTE")
print("=" * 80)
print("✅ pushName do WhatsApp: 'Zé Bonitão' (apelido)")
print("✅ Nome fornecido pelo usuário: 'José Carlos Silva'")
print("✅ Telefone: 5511987654321")
print("")
print("💡 O sistema deve salvar:")
print("   - Nome: José Carlos Silva (não 'Zé Bonitão')")
print("   - Telefone: 5511987654321")
print("=" * 80)
