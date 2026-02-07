import os
import base64
import tempfile
import logging
from typing import Optional

from app.services.whatsapp_interface import WhatsAppMessage
from app.services.openai_audio_service import get_audio_service
from app.services.audio_preference_service import deve_enviar_audio
from app.services.conversa_service import ConversaService
from app.models.mensagem import DirecaoMensagem, RemetenteMensagem, TipoMensagem

logger = logging.getLogger(__name__)

ENABLE_AUDIO_INPUT = os.getenv("ENABLE_AUDIO_INPUT", "true").lower() == "true"
ENABLE_AUDIO_OUTPUT = os.getenv("ENABLE_AUDIO_OUTPUT", "true").lower() == "true"
AUDIO_OUTPUT_MODE = os.getenv("AUDIO_OUTPUT_MODE", "hybrid")  # text, audio, hybrid


async def transcribe_incoming_audio(message: WhatsAppMessage, whatsapp_service) -> bool:
    """Baixa e transcreve áudio. Muta message.text in-place. Retorna True se era áudio."""
    if message.message_type != "audio":
        return False

    if not ENABLE_AUDIO_INPUT or not message.audio_url:
        return True

    try:
        logger.info(f"[Webhook Official] 🎤 Processando áudio recebido (media_id: {message.audio_url})")

        # Baixar áudio da API oficial (media_id → bytes)
        audio_bytes = await whatsapp_service.download_media(message.audio_url)

        if audio_bytes:
            # Salvar em arquivo temporário
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(audio_bytes)
                audio_path = f.name

            logger.info(f"[Webhook Official] 📁 Áudio salvo: {audio_path} ({len(audio_bytes)} bytes)")

            # Transcrever com Whisper
            audio_service = get_audio_service()
            if audio_service:
                texto_transcrito = await audio_service.transcrever_audio(audio_path)
                message.text = texto_transcrito
                logger.info(f"[Webhook Official] ✅ Áudio transcrito: {texto_transcrito[:100]}...")

                # Limpar arquivo temporário
                audio_service.limpar_audio(audio_path)
            else:
                logger.warning("[Webhook Official] ⚠️ Serviço de áudio não disponível")
                message.text = "[Áudio recebido - transcrição não disponível]"
        else:
            logger.warning("[Webhook Official] ⚠️ Falha ao baixar áudio")
            message.text = "[Áudio recebido - erro ao baixar]"

    except Exception as e:
        logger.error(f"[Webhook Official] ❌ Erro ao processar áudio: {e}")
        message.text = "[Áudio recebido - erro na transcrição]"

    return True


async def handle_audio_response(
    db, conversa_id, cliente_id, message, texto_resposta,
    mensagem_foi_audio, whatsapp_service
) -> Optional[str]:
    """Verifica preferência de áudio e envia TTS se aplicável.
    Retorna mensagem_preferencia ou None."""
    enviar_audio = False
    mensagem_preferencia = None

    if ENABLE_AUDIO_OUTPUT:
        enviar_audio, mensagem_preferencia = deve_enviar_audio(
            db=db,
            telefone=message.sender,
            mensagem_foi_audio=mensagem_foi_audio,
            mensagem_texto=message.text
        )
        logger.info(f"[Webhook Official] 🔊 Enviar áudio: {enviar_audio} (modo: {AUDIO_OUTPUT_MODE})")

    # Enviar áudio se habilitado e preferência permitir
    if enviar_audio and AUDIO_OUTPUT_MODE in ["audio", "hybrid"]:
        try:
            audio_service = get_audio_service()
            if audio_service:
                logger.info(f"[Webhook Official] 🎤 Gerando áudio TTS para resposta...")

                # Gerar áudio com TTS
                audio_path = await audio_service.texto_para_audio(texto_resposta)

                if audio_path:
                    # Ler arquivo e converter para base64
                    with open(audio_path, "rb") as f:
                        audio_base64 = base64.b64encode(f.read()).decode()

                    # Enviar áudio
                    result = await whatsapp_service.send_audio(
                        to=message.sender,
                        audio_base64=audio_base64,
                        phone_number_id=message.phone_number_id
                    )

                    if result.success:
                        logger.info(f"[Webhook Official] ✅ Áudio enviado com sucesso")

                        # Salvar mensagem de áudio no PostgreSQL
                        ConversaService.adicionar_mensagem(
                            db=db,
                            conversa_id=conversa_id,
                            direcao=DirecaoMensagem.SAIDA,
                            remetente=RemetenteMensagem.IA,
                            conteudo="[Áudio]",
                            tipo=TipoMensagem.AUDIO
                        )
                    else:
                        logger.warning(f"[Webhook Official] ⚠️ Falha ao enviar áudio: {result.error}")

                    # Limpar arquivo temporário
                    audio_service.limpar_audio(audio_path)

        except Exception as e:
            logger.error(f"[Webhook Official] ❌ Erro ao gerar/enviar áudio: {e}")

    # Enviar mensagem de confirmação de preferência se houver
    if mensagem_preferencia:
        await whatsapp_service.send_text(
            to=message.sender,
            message=mensagem_preferencia,
            phone_number_id=message.phone_number_id
        )

    return mensagem_preferencia
