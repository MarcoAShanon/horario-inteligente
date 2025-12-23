#!/usr/bin/env python3
"""
Script de teste da integração de áudio OpenAI
Testa: Whisper (STT) e TTS (Text-to-Speech)
"""
import asyncio
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

from app.services.openai_audio_service import OpenAIAudioService, get_audio_service

async def test_audio_service():
    """Testa o serviço de áudio OpenAI"""

    print("=" * 60)
    print("🧪 TESTE DE INTEGRAÇÃO DE ÁUDIO - OPENAI")
    print("=" * 60)

    # 1. Verificar configuração
    print("\n1️⃣ Verificando configuração...")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY não configurada!")
        return False

    print(f"✅ API Key configurada: {api_key[:20]}...")
    print(f"   TTS_VOICE: {os.getenv('TTS_VOICE', 'nova')}")
    print(f"   TTS_SPEED: {os.getenv('TTS_SPEED', '0.9')}")
    print(f"   ENABLE_AUDIO_INPUT: {os.getenv('ENABLE_AUDIO_INPUT', 'false')}")
    print(f"   ENABLE_AUDIO_OUTPUT: {os.getenv('ENABLE_AUDIO_OUTPUT', 'false')}")
    print(f"   AUDIO_OUTPUT_MODE: {os.getenv('AUDIO_OUTPUT_MODE', 'text')}")

    # 2. Inicializar serviço
    print("\n2️⃣ Inicializando OpenAI Audio Service...")

    try:
        audio_service = get_audio_service()
        if not audio_service:
            print("❌ Falha ao inicializar serviço de áudio")
            return False

        print("✅ Serviço inicializado com sucesso!")

        # Validar configuração
        config = audio_service.validar_configuracao()
        print("\n📋 Configuração atual:")
        for key, value in config.items():
            print(f"   {key}: {value}")

    except Exception as e:
        print(f"❌ Erro ao inicializar serviço: {e}")
        return False

    # 3. Testar TTS (Text-to-Speech)
    print("\n3️⃣ Testando TTS (Text-to-Speech)...")

    try:
        texto_teste = "Olá! Esta é uma mensagem de teste do sistema de áudio. Sua consulta está confirmada para amanhã às 14 horas."

        print(f"   📝 Texto: {texto_teste}")
        print(f"   🎙️ Gerando áudio...")

        audio_path = await audio_service.texto_para_audio(texto_teste)

        # Verificar se arquivo foi criado
        if os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path)
            print(f"✅ Áudio gerado com sucesso!")
            print(f"   📁 Arquivo: {audio_path}")
            print(f"   📊 Tamanho: {file_size} bytes ({file_size/1024:.2f} KB)")

            # Limpar arquivo
            audio_service.limpar_audio(audio_path)
            print(f"   🗑️ Arquivo temporário removido")
        else:
            print(f"❌ Arquivo de áudio não foi criado")
            return False

    except Exception as e:
        print(f"❌ Erro ao gerar áudio: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. Testar Whisper (STT) - apenas se houver arquivo de áudio de teste
    print("\n4️⃣ Teste de Whisper (STT)...")
    print("   ℹ️ Para testar Whisper, envie um áudio real via WhatsApp")
    print("   ℹ️ O áudio será transcrito automaticamente pelo webhook")

    # Resumo final
    print("\n" + "=" * 60)
    print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    print("=" * 60)
    print("\n📋 Próximos passos:")
    print("   1. Enviar áudio via WhatsApp para testar Whisper (STT)")
    print("   2. Verificar se a IA responde em áudio (TTS)")
    print("   3. Validar modo híbrido (texto + áudio)")
    print("\n💡 Configuração atual:")
    print(f"   - Receber áudios: {'✅ ATIVO' if config['audio_input_enabled'] else '❌ DESATIVADO'}")
    print(f"   - Enviar áudios: {'✅ ATIVO' if config['audio_output_enabled'] else '❌ DESATIVADO'}")
    print(f"   - Modo de saída: {config['audio_output_mode']}")
    print()

    return True

if __name__ == "__main__":
    success = asyncio.run(test_audio_service())
    sys.exit(0 if success else 1)
