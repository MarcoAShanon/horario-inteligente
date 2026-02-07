"""
WhatsApp messaging: send responses, formatting, fallback
"""
import logging
import os
import aiohttp

from app.api.webhooks.utils import EVOLUTION_API_URL, EVOLUTION_API_KEY
from app.services.openai_audio_service import get_audio_service
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)


def formatar_para_whatsapp(texto: str) -> str:
    """
    Formata texto para WhatsApp com melhor aparência
    """
    # Converter ** para * (negrito no WhatsApp)
    texto = texto.replace("**", "*")

    # Adicionar emojis se não tiver
    if "olá" in texto.lower() and "👋" not in texto:
        texto = "👋 " + texto

    if "agenda" in texto.lower() and "📅" not in texto:
        texto = texto.replace("agenda", "📅 agenda")

    if "médico" in texto.lower() and "👨‍⚕️" not in texto:
        texto = texto.replace("médico", "👨‍⚕️ médico")

    # Limitar tamanho
    if len(texto) > 4000:
        texto = texto[:3997] + "..."

    return texto


async def send_whatsapp_response(instance_name: str, to_number: str, message: str, send_audio: bool = None) -> bool:
    """
    Envia resposta via Evolution API v1.7.4
    Suporta: texto, áudio ou híbrido (ambos)
    NOVO: Processa pausas estratégicas [PAUSA_X_SEGUNDOS]

    Args:
        instance_name: Nome da instância
        to_number: Número do destinatário
        message: Mensagem de texto
        send_audio: Se True, envia áudio também. Se None, usa config do .env

    Returns:
        True se enviado com sucesso
    """
    try:
        # ========================================
        # PROCESSAR PAUSAS ESTRATÉGICAS
        # ========================================
        import re
        import asyncio

        # Detectar pausa na mensagem (ex: [PAUSA_3_SEGUNDOS])
        pausa_pattern = r'\[PAUSA_(\d+)_SEGUNDOS\]|⏳\s*\[PAUSA_(\d+)_SEGUNDOS\]'
        pausa_match = re.search(pausa_pattern, message)

        if pausa_match:
            # Extrair tempo de pausa
            tempo_pausa = int(pausa_match.group(1) or pausa_match.group(2))

            # Dividir mensagem em duas partes (antes e depois da pausa)
            partes = re.split(pausa_pattern, message, maxsplit=1)
            mensagem_parte1 = partes[0].strip()
            mensagem_parte2 = partes[-1].strip() if len(partes) > 1 else ""

            logger.info(f"⏳ Pausa estratégica detectada: {tempo_pausa}s")
            logger.info(f"   📤 Parte 1: {mensagem_parte1[:50]}...")
            logger.info(f"   ⏸️ Aguardando {tempo_pausa}s...")
            logger.info(f"   📤 Parte 2: {mensagem_parte2[:50]}...")

            # Enviar primeira parte
            if mensagem_parte1:
                success1 = await send_whatsapp_response(instance_name, to_number, mensagem_parte1, send_audio=False)
                if not success1:
                    logger.error("❌ Erro ao enviar primeira parte da mensagem")
                    return False

            # Aguardar tempo estratégico
            await asyncio.sleep(tempo_pausa)

            # Enviar segunda parte (com áudio se configurado)
            if mensagem_parte2:
                success2 = await send_whatsapp_response(instance_name, to_number, mensagem_parte2, send_audio=send_audio)
                return success2

            return True

        # ========================================
        # ENVIO NORMAL (sem pausa)
        # ========================================

        # Formatar número
        to_number = to_number.replace('@s.whatsapp.net', '')
        if not to_number.startswith('55'):
            to_number = '55' + to_number

        # ========================================
        # DETERMINAR MODO DE ENVIO
        # ========================================
        enable_audio_output = os.getenv("ENABLE_AUDIO_OUTPUT", "false").lower() == "true"
        audio_output_mode = os.getenv("AUDIO_OUTPUT_MODE", "text")  # text, audio, hybrid

        # Se send_audio não foi especificado, usar configuração
        if send_audio is None:
            send_audio = enable_audio_output

        # ========================================
        # ENVIAR TEXTO (sempre, exceto se modo=audio)
        # ========================================
        if audio_output_mode != "audio":
            url = f"{EVOLUTION_API_URL}/message/sendText/{instance_name}"

            payload = {
                "number": to_number,
                "text": message,
                "options": {
                    "delay": 1200,  # Delay natural
                    "presence": "composing"
                }
            }

            headers = {
                "apikey": EVOLUTION_API_KEY,
                "Content-Type": "application/json"
            }

            logger.info(f"📤 Enviando resposta TEXTO para {to_number}")

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status not in [200, 201]:
                        error = await response.text()
                        logger.error(f"❌ Erro ao enviar texto: {response.status} - {error}")
                        return False
                    logger.info("✅ Texto enviado com sucesso!")

        # ========================================
        # ENVIAR ÁUDIO (se habilitado)
        # ========================================
        if send_audio and audio_output_mode in ["audio", "hybrid"]:
            try:
                logger.info(f"🔊 Gerando áudio TTS para envio...")

                # Obter serviço de áudio
                audio_service = get_audio_service()
                if not audio_service:
                    logger.warning("⚠️ OpenAI Audio Service não disponível, enviando apenas texto")
                    return True  # Texto já foi enviado

                # Gerar áudio
                audio_path = await audio_service.texto_para_audio(message)

                # Enviar via WhatsApp Service
                result = await whatsapp_service.enviar_audio(
                    instance_name=instance_name,
                    to_number=to_number,
                    audio_path=audio_path
                )

                # Limpar arquivo temporário
                audio_service.limpar_audio(audio_path)

                if result.get("success"):
                    logger.info("✅ Áudio enviado com sucesso!")
                else:
                    logger.error(f"❌ Erro ao enviar áudio: {result.get('error')}")
                    # Não é erro crítico se texto já foi enviado

            except Exception as e:
                logger.error(f"❌ Erro ao processar/enviar áudio: {e}")
                # Não é erro crítico se texto já foi enviado (modo híbrido)
                if audio_output_mode == "audio":
                    return False  # Modo somente áudio falhou

        return True

    except Exception as e:
        logger.error(f"❌ Erro geral ao enviar resposta: {e}")
        return False


def get_fallback_response(message_text: str, user_name: str) -> str:
    """
    Respostas de fallback caso IA falhe
    """
    logger.info(f"🔍 Gerando fallback response para: {message_text[:50]}")

    text_lower = message_text.lower().strip()

    if any(word in text_lower for word in ['oi', 'olá', 'bom dia', 'boa tarde', 'boa noite']):
        return f"""👋 Olá {user_name}! Bem-vindo à *Clínica Pro-Saúde*!

Sou a assistente virtual com inteligência artificial.

Como posso ajudar você hoje?
• Agendar consultas
• Informações sobre médicos
• Horários disponíveis
• Convênios aceitos

_Digite sua necessidade que vou entender!_"""

    elif any(word in text_lower for word in ['agendar', 'marcar', 'consulta']):
        return """📅 *AGENDAMENTO DE CONSULTAS*

Temos os seguintes médicos:
• *Dr. Marco Silva* - Clínico Geral
• *Dra. Tânia Oliveira* - Cardiologista

Qual médico você prefere?"""

    else:
        return f"""Entendi sua mensagem, {user_name}.

Como posso ajudar?
• Agendar consulta
• Ver médicos disponíveis
• Horários da clínica
• Convênios aceitos

_Pode escrever naturalmente!_"""
