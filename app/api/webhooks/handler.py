"""
Main webhook endpoints: POST /whatsapp/{instance_name}, POST /whatsapp
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
import json
import aiohttp
import tempfile
import os
from sqlalchemy import text

from app.database import get_db
from app.services.openai_audio_service import get_audio_service
from app.services.whatsapp_decrypt import decrypt_whatsapp_media
from app.services.audio_preference_service import (
    deve_enviar_audio,
    detectar_preferencia_na_mensagem,
    gerar_resposta_preferencia
)

from app.api.webhooks.utils import (
    limiter,
    EVOLUTION_API_URL,
    EVOLUTION_API_KEY,
    get_cliente_id_from_instance,
    verify_webhook_auth,
)
from app.api.webhooks.message_extraction import extract_message_info
from app.api.webhooks.messaging import send_whatsapp_response
from app.api.webhooks.ai_processing import process_with_anthropic_ai

logger = logging.getLogger(__name__)

router = APIRouter()


async def _process_webhook(instance_name: str, request: Request, db: Session):
    """
    Lógica principal do webhook WhatsApp.
    Extraída para ser reutilizada por ambos endpoints.
    """
    try:
        # SEGURANÇA: Verificar autenticação do webhook
        if not verify_webhook_auth(request):
            logger.warning(f"⚠️ Webhook não autenticado de {request.client.host if request.client else 'unknown'}")
            return JSONResponse(
                status_code=401,
                content={"status": "error", "message": "Unauthorized"}
            )

        # Receber dados
        webhook_data = await request.json()
        logger.info(f"📨 Webhook recebido para {instance_name}")
        # SEGURANÇA: Não logar dados completos em produção
        if os.getenv("DEBUG", "False").lower() == "true":
            logger.debug(f"🔍 DEBUG - Dados recebidos: {json.dumps(webhook_data, indent=2)}")

        # Extrair informações da mensagem
        message_info = extract_message_info(webhook_data)

        if not message_info:
            logger.info("Mensagem ignorada (não é texto ou é do bot)")
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "reason": "not_user_message"}
            )

        sender = message_info['sender']
        push_name = message_info.get('push_name', 'Cliente')
        message_type = message_info.get('message_type', 'text')

        # Resolver cliente_id a partir da instância WhatsApp (MULTI-TENANT)
        cliente_id = get_cliente_id_from_instance(instance_name, db)
        logger.info(f"🏢 Cliente identificado: {instance_name} → cliente_id={cliente_id}")

        # ========================================
        # PROCESSAR ÁUDIO (Whisper STT)
        # ========================================
        message_text = message_info.get('text')

        if message_type == 'audio':
            # Verificar se áudio está habilitado
            enable_audio_input = os.getenv("ENABLE_AUDIO_INPUT", "false").lower() == "true"

            if not enable_audio_input:
                logger.info("⚠️ Áudio recebido mas ENABLE_AUDIO_INPUT=false")
                await send_whatsapp_response(
                    instance_name,
                    sender,
                    "Por favor, envie sua mensagem por texto. 📝"
                )
                return JSONResponse(
                    status_code=200,
                    content={"status": "audio_disabled"}
                )

            # Processar áudio
            audio_url = message_info.get('audio_url')
            if not audio_url:
                logger.error("❌ URL do áudio não encontrada")
                await send_whatsapp_response(
                    instance_name,
                    sender,
                    "Desculpe, não consegui processar o áudio. Pode enviar por texto?"
                )
                return JSONResponse(
                    status_code=200,
                    content={"status": "error", "message": "audio_url_missing"}
                )

            try:
                logger.info(f"🎤 URL do áudio: {audio_url}")
                audio_data = None
                is_encrypted = ".enc" in audio_url

                # ESTRATÉGIA V2.0.10: Tentar download direto primeiro
                # A Evolution API v2.0.10 pode já fornecer URLs descriptografadas
                logger.info(f"📥 Tentando download direto do áudio{' (criptografado)' if is_encrypted else ''}...")

                try:
                    timeout = aiohttp.ClientTimeout(total=30)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(audio_url) as response:
                            if response.status == 200:
                                audio_data = await response.read()
                                logger.info(f"✅ Áudio baixado diretamente ({len(audio_data)} bytes)")
                            else:
                                logger.warning(f"⚠️ Download direto falhou: HTTP {response.status}")
                except Exception as e:
                    logger.warning(f"⚠️ Download direto falhou: {e}")

                # Se download direto falhou E áudio é criptografado, tentar via Evolution API
                if (not audio_data or len(audio_data) == 0) and is_encrypted:
                    logger.info("🔐 Tentando baixar via Evolution API (áudio criptografado)...")

                    # Extrair message ID do webhook
                    message_data = webhook_data.get('data', {})
                    message_key = message_data.get('key', {})
                    message_id = message_key.get('id')

                    if message_id:
                        logger.info(f"📥 Message ID: {message_id}")

                        # Endpoint da Evolution API v2.0.10 para baixar mídia
                        evolution_url = f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{instance_name}"

                        payload = {
                            "message": {
                                "key": message_key
                            },
                            "convertToMp4": False
                        }

                        headers = {
                            "apikey": EVOLUTION_API_KEY,
                            "Content-Type": "application/json"
                        }

                        timeout = aiohttp.ClientTimeout(total=30)
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.post(evolution_url, json=payload, headers=headers) as response:
                                if response.status in [200, 201]:
                                    result = await response.json()
                                    base64_media = result.get('base64')

                                    if base64_media:
                                        import base64
                                        audio_data = base64.b64decode(base64_media)
                                        logger.info(f"✅ Áudio descriptografado via Evolution API ({len(audio_data)} bytes)")
                                    else:
                                        logger.error("❌ Base64 não retornado pela Evolution API")
                                else:
                                    error_text = await response.text()
                                    logger.error(f"❌ Evolution API erro {response.status}: {error_text}")
                    else:
                        logger.error("❌ Message ID não encontrado no webhook")

                if not audio_data or len(audio_data) == 0:
                    raise Exception("Áudio vazio ou não baixado")

                logger.info(f"📊 Tamanho do áudio baixado: {len(audio_data)} bytes")

                # DESCRIPTOGRAFAR se necessário
                if is_encrypted:
                    logger.info("🔐 Descriptografando áudio...")
                    media_key = message_info.get('audio_msg', {}).get('mediaKey')

                    if media_key:
                        try:
                            # Descriptografar usando as chaves do WhatsApp
                            audio_data = decrypt_whatsapp_media(
                                encrypted_data=audio_data,
                                media_key_base64=media_key,
                                media_type="ptt"  # Push-to-Talk (áudio de voz)
                            )
                            logger.info(f"✅ Áudio descriptografado: {len(audio_data)} bytes")
                        except Exception as decrypt_error:
                            logger.error(f"❌ Erro na descriptografia: {decrypt_error}")
                            raise Exception(f"Falha ao descriptografar áudio: {decrypt_error}")
                    else:
                        logger.error("❌ mediaKey não encontrado no audioMessage")
                        raise Exception("mediaKey não disponível para descriptografia")

                # Salvar temporariamente
                with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
                    temp_audio.write(audio_data)
                    temp_audio_path = temp_audio.name

                # Verificar se o arquivo foi salvo corretamente
                file_size = os.path.getsize(temp_audio_path)
                logger.info(f"💾 Áudio salvo em: {temp_audio_path} ({file_size} bytes)")

                if file_size == 0:
                    raise Exception("Arquivo de áudio vazio - download falhou ou áudio criptografado")

                # Whisper aceita OGG diretamente, não precisa converter!
                # Formatos suportados: flac, m4a, mp3, mp4, mpeg, mpga, oga, ogg, wav, webm
                logger.info(f"🎤 Enviando áudio diretamente para Whisper (OGG é suportado)")

                # Transcrever com Whisper
                audio_service = get_audio_service()
                if not audio_service:
                    raise Exception("OpenAI Audio Service não disponível")

                message_text = await audio_service.transcrever_audio(temp_audio_path)

                # Limpar arquivo temporário
                audio_service.limpar_audio(temp_audio_path)

                logger.info(f"✅ Áudio transcrito: {message_text}")

                # Enviar confirmação ao usuário (opcional)
                await send_whatsapp_response(
                    instance_name,
                    sender,
                    f"🎤 Entendi: \"{message_text}\""
                )

            except Exception as e:
                logger.error(f"❌ Erro ao processar áudio: {e}")
                await send_whatsapp_response(
                    instance_name,
                    sender,
                    "Desculpe, não consegui entender o áudio. Pode enviar por texto?"
                )
                return JSONResponse(
                    status_code=200,
                    content={"status": "error", "message": str(e)}
                )

        # Se não há texto (nem de áudio nem de texto), retornar
        if not message_text:
            return JSONResponse(
                status_code=200,
                content={"status": "no_message"}
            )

        logger.info(f"💬 {push_name} ({sender}): {message_text}")

        # ========== DETECTAR RESPOSTA A LEMBRETE ==========
        # Verificar se é uma confirmação/cancelamento de lembrete
        mensagem_lower = message_text.lower().strip()
        palavras_confirmacao = ["sim", "yes", "confirmo", "confirmar", "ok", "s"]
        palavras_cancelamento = ["não", "nao", "no", "cancelar", "cancela", "n"]

        is_confirmacao = any(palavra in mensagem_lower for palavra in palavras_confirmacao)
        is_cancelamento = any(palavra in mensagem_lower for palavra in palavras_cancelamento)

        if is_confirmacao or is_cancelamento:
            # Buscar agendamento próximo para este telefone
            agendamento_proximo = db.execute(text("""
                SELECT a.id, a.data_hora, a.status, m.nome as medico_nome
                FROM agendamentos a
                JOIN pacientes p ON a.paciente_id = p.id
                JOIN medicos m ON a.medico_id = m.id
                WHERE p.telefone = :tel
                AND p.cliente_id = :cli_id
                AND a.data_hora > NOW()
                AND a.data_hora <= NOW() + INTERVAL '48 hours'
                AND a.status IN ('agendado', 'confirmado')
                ORDER BY a.data_hora ASC
                LIMIT 1
            """), {"tel": sender, "cli_id": cliente_id}).fetchone()

            if agendamento_proximo:
                logger.info(f"🔔 Detectada resposta a lembrete - Agendamento ID: {agendamento_proximo.id}")

                if is_confirmacao:
                    # Confirmar agendamento
                    db.execute(text("""
                        UPDATE agendamentos
                        SET status = 'confirmado', atualizado_em = NOW()
                        WHERE id = :ag_id
                    """), {"ag_id": agendamento_proximo.id})
                    db.commit()

                    data_formatada = agendamento_proximo.data_hora.strftime("%d/%m/%Y às %H:%M")
                    response_message = f"✅ *Consulta confirmada com sucesso!*\n\n"
                    response_message += f"📅 *Data:* {data_formatada}\n"
                    response_message += f"👨‍⚕ *Médico:* {agendamento_proximo.medico_nome}\n\n"
                    response_message += f"💡 Por favor, chegue com 15 minutos de antecedência.\n"
                    response_message += f"📍 Traga seus documentos e carteirinha do convênio (se houver).\n\n"
                    response_message += f"Até breve! 😊"

                    logger.info(f"✅ Consulta confirmada - ID {agendamento_proximo.id}")

                elif is_cancelamento:
                    # Cancelar agendamento
                    db.execute(text("""
                        UPDATE agendamentos
                        SET status = 'cancelado', atualizado_em = NOW()
                        WHERE id = :ag_id
                    """), {"ag_id": agendamento_proximo.id})
                    db.commit()

                    response_message = f"❌ *Consulta cancelada.*\n\n"
                    response_message += f"Tudo bem! Seu agendamento foi cancelado.\n\n"
                    response_message += f"Quando quiser reagendar, é só me chamar! 😊\n"
                    response_message += f"Estamos sempre à disposição."

                    logger.info(f"❌ Consulta cancelada - ID {agendamento_proximo.id}")

                # Enviar resposta e retornar
                await send_whatsapp_response(instance_name, sender, response_message)
                return JSONResponse(
                    status_code=200,
                    content={"status": "success", "type": "reminder_response", "action": "confirmacao" if is_confirmacao else "cancelamento"}
                )
        # ==================================================

        logger.info(f"🔍 DEBUG - Chamando process_with_anthropic_ai...")

        # Processar com IA Anthropic (passa cliente_id e db)
        response_message = await process_with_anthropic_ai(message_text, sender, push_name, cliente_id, db)
        logger.info(f"🔍 DEBUG - Resposta da IA recebida: {response_message[:100] if response_message else 'NENHUMA'}")

        if response_message:
            # ========================================
            # SISTEMA HÍBRIDO INTELIGENTE DE ÁUDIO
            # ========================================
            # Determinar se deve enviar áudio baseado em:
            # 1. Preferência explícita na mensagem
            # 2. Modo espelho (áudio→áudio, texto→texto)
            # 3. Preferência salva do paciente

            try:
                mensagem_foi_audio = (message_type == 'audio')
                enviar_audio, msg_confirmacao = deve_enviar_audio(
                    db=db,
                    telefone=sender,
                    mensagem_foi_audio=mensagem_foi_audio,
                    mensagem_texto=message_text or ""
                )

                # Se houve mudança de preferência, adicionar confirmação
                if msg_confirmacao:
                    response_message = f"{msg_confirmacao}\n\n{response_message}"
                    logger.info(f"🔊 Preferência de áudio atualizada para {sender}")

                logger.info(f"🔊 Modo áudio: enviar_audio={enviar_audio}, mensagem_foi_audio={mensagem_foi_audio}")

            except Exception as e:
                logger.error(f"Erro ao verificar preferência de áudio: {e}")
                enviar_audio = False

            # Enviar resposta via WhatsApp (com ou sem áudio)
            success = await send_whatsapp_response(
                instance_name,
                sender,
                response_message,
                send_audio=enviar_audio
            )

            if success:
                logger.info(f"✅ Resposta IA enviada para {push_name} (áudio={enviar_audio})")
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success",
                        "response_sent": True,
                        "ai_used": True,
                        "model": "claude-3.5-sonnet",
                        "audio_sent": enviar_audio
                    }
                )
            else:
                logger.error(f"Erro ao enviar resposta para {sender}")
                return JSONResponse(
                    status_code=200,
                    content={"status": "error", "response_sent": False}
                )

        logger.warning("🔍 DEBUG - Nenhuma resposta da IA, retornando processed")
        return JSONResponse(
            status_code=200,
            content={"status": "processed"}
        )

    except Exception as e:
        logger.error(f"Erro no webhook: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@router.post("/whatsapp/{instance_name}")
@limiter.limit("100/minute")
async def webhook_whatsapp(instance_name: str, request: Request, db: Session = Depends(get_db)):
    """
    Webhook principal com IA Claude 3.5 Sonnet integrada
    """
    return await _process_webhook(instance_name, request, db)


@router.post("/whatsapp")
async def webhook_global(request: Request, db: Session = Depends(get_db)):
    """
    Webhook alternativo sem instance_name
    Usa instância padrão 'Clinica2024' para desenvolvimento
    """
    return await _process_webhook("Clinica2024", request, db)
