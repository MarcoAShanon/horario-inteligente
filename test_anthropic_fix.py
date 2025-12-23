#!/usr/bin/env python3
"""Teste rápido para verificar se o modelo Anthropic foi corrigido."""

import os
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Verificar configuração
print("=" * 60)
print("🔍 VERIFICAÇÃO DA CONFIGURAÇÃO ANTHROPIC")
print("=" * 60)

anthropic_key = os.getenv("ANTHROPIC_API_KEY")
anthropic_model = os.getenv("ANTHROPIC_MODEL")

print(f"\n✅ API Key configurada: {anthropic_key[:20]}..." if anthropic_key else "❌ API Key NÃO encontrada")
print(f"✅ Modelo configurado: {anthropic_model}" if anthropic_model else "❌ Modelo NÃO configurado")

# Testar com Anthropic
try:
    from anthropic import Anthropic
    print("\n✅ Biblioteca Anthropic instalada")

    client = Anthropic(api_key=anthropic_key)
    print("✅ Cliente Anthropic criado")

    # Fazer uma chamada de teste
    print(f"\n🤖 Testando modelo: {anthropic_model}")
    print("📤 Enviando mensagem de teste...")

    # Tentar com o modelo configurado primeiro
    models_to_try = [
        anthropic_model,
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-latest"
    ]

    for model in models_to_try:
        if not model:
            continue
        print(f"\n🔄 Tentando modelo: {model}")
        try:
            response = client.messages.create(
                model=model,
                max_tokens=100,
                messages=[
                    {"role": "user", "content": "Responda apenas 'OK' se você está funcionando."}
                ]
            )
            resposta = response.content[0].text
            print(f"✅ SUCESSO com modelo: {model}")
            print(f"📥 Resposta recebida: {resposta}")

            # Salvar modelo funcional no .env
            if model != anthropic_model:
                print(f"\n⚠️ Modelo diferente do configurado!")
                print(f"💡 Sugestão: atualizar .env para: ANTHROPIC_MODEL={model}")

            break
        except Exception as e:
            print(f"❌ Falhou: {e}")
            continue
    else:
        raise Exception("Nenhum modelo funcionou!")

    print("\n✅✅✅ SUCESSO! A IA está funcionando corretamente!")

except Exception as e:
    print(f"\n❌ ERRO: {e}")
    print("\n⚠️ A correção não funcionou completamente.")
    sys.exit(1)

print("=" * 60)
