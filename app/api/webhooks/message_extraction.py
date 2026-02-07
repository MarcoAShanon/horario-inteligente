"""
Message extraction from Evolution API webhook payloads
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def extract_message_info(webhook_data: dict) -> Optional[Dict[str, Any]]:
    """
    Extrai informações da mensagem (Evolution API v2.0.10)
    Suporta: texto e áudio
    """
    try:
        logger.info(f"🔍 Extraindo info da mensagem...")

        if 'data' in webhook_data:
            data = webhook_data['data']
            logger.info(f"🔍 'data' encontrado, chaves: {list(data.keys())}")

            if 'message' in data:
                message = data['message']
                key = data.get('key', {})
                message_type = data.get('messageType', '')  # Novo campo na v2.0.10

                logger.info(f"🔍 'message' encontrado, tipo: {type(message)}")
                logger.info(f"🔍 'messageType' field: {message_type}")  # Log do novo campo

                # Ignorar mensagens do bot
                if key.get('fromMe', False):
                    logger.info(f"🔍 Mensagem ignorada: é do bot (fromMe=True)")
                    return None

                # Extrair informações comuns
                sender = key.get('remoteJid', '').replace('@s.whatsapp.net', '')
                push_name = data.get('pushName', 'Cliente')

                # ========================================
                # 1. DETECTAR ÁUDIO (MELHORADO para v2.0.10)
                # ========================================
                # Método 1: Usar novo campo messageType (v2.0.10)
                is_audio_by_type = message_type in ['audioMessage', 'audio', 'ptt']

                # Método 2: Verificar estrutura antiga (compatibilidade v1.7.4)
                has_audio_message = isinstance(message, dict) and 'audioMessage' in message

                if is_audio_by_type or has_audio_message:
                    logger.info(f"🎤 Áudio detectado! (messageType={message_type}, has_audioMessage={has_audio_message})")

                    audio_msg = message.get('audioMessage', {})
                    audio_url = audio_msg.get('url')

                    # Tentar outros campos possíveis na v2.0.10
                    if not audio_url:
                        audio_url = audio_msg.get('directPath') or audio_msg.get('mediaUrl')

                    logger.info(f"🎤 URL do áudio: {audio_url}")
                    logger.info(f"🎤 audioMessage completo: {audio_msg}")  # Debug

                    return {
                        'sender': sender,
                        'text': None,
                        'push_name': push_name,
                        'message_type': 'audio',
                        'audio_url': audio_url,
                        'audio_msg': audio_msg  # Objeto completo para debug
                    }

                # ========================================
                # 2. DETECTAR TEXTO (comportamento anterior)
                # ========================================
                extracted_text = None
                if isinstance(message, dict):
                    extracted_text = (
                        message.get('conversation') or
                        message.get('text') or
                        (message.get('extendedTextMessage', {}).get('text'))
                    )
                elif isinstance(message, str):
                    extracted_text = message

                logger.info(f"🔍 Texto extraído: '{extracted_text}'")

                if extracted_text:
                    # ============================================================
                    # CAPTURA AUTOMÁTICA DE TELEFONE:
                    # O número do telefone é extraído automaticamente do WhatsApp
                    # Exemplo: '5524988493257@s.whatsapp.net' vira '5524988493257'
                    # Este número é salvo na tabela 'pacientes' (campo único)
                    # E pode ser acessado via: agendamento.paciente.telefone
                    # ============================================================

                    # pushName = Nome configurado no WhatsApp do usuário
                    # IMPORTANTE: Usado APENAS para logs, NUNCA para dados do paciente

                    logger.info(f"🔍 Info extraída: sender={sender}, push_name={push_name}")

                    return {
                        'sender': sender,
                        'text': extracted_text,
                        'push_name': push_name,
                        'message_type': 'text'
                    }

        logger.info(f"🔍 Nenhuma mensagem válida encontrada")
        return None

    except Exception as e:
        logger.error(f"Erro ao extrair mensagem: {e}", exc_info=True)
        return None
