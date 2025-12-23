#!/usr/bin/env python3
"""Teste da API Key Anthropic."""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
print(f"API Key: {api_key[:20]}...")

# Testar com modelos antigos que certamente existem
models = [
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]

client = Anthropic(api_key=api_key)

for model in models:
    print(f"\n🔄 Testando: {model}")
    try:
        response = client.messages.create(
            model=model,
            max_tokens=50,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"✅ FUNCIONOU! Resposta: {response.content[0].text[:50]}")
        print(f"\n💡 Use este modelo: {model}")
        break
    except Exception as e:
        print(f"❌ Erro: {str(e)[:100]}")
