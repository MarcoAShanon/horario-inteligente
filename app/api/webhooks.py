"""
Webhook com IA Anthropic integrada - VERSÃO FINAL + ÁUDIO
Arquivo: app/api/webhooks.py
Sistema Pro-Saúde com Claude 3.5 Sonnet + OpenAI Whisper/TTS
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
import json
import aiohttp
import tempfile
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
from sqlalchemy import text

# Configurar logging
logger = logging.getLogger(__name__)

# Configuração da Evolution API
EVOLUTION_API_URL = "http://localhost:8080"
EVOLUTION_API_KEY = "evolution-api-prosaude-123"
# INSTANCE_NAME será dinâmico baseado no cliente

# Importar database e serviços
from app.database import SessionLocal
from app.services.anthropic_service import AnthropicService
from app.services.conversation_manager import conversation_manager
from app.services.calendario_service import CalendarioService
from app.services.whatsapp_service import whatsapp_service
from app.services.openai_audio_service import get_audio_service
from app.services.whatsapp_decrypt import decrypt_whatsapp_media

router = APIRouter()

# Cache de mapeamento instance → cliente_id
INSTANCE_TO_CLIENTE_CACHE = {}

def get_cliente_id_from_instance(instance_name: str) -> int:
    """
    Resolve cliente_id a partir do nome da instância WhatsApp
    Usa cache para performance

    Exemplos:
    - "ProSaude" → 1
    - "DrMarco" → 2
    - "ClinicaX" → 3
    """
    # Verificar cache
    if instance_name in INSTANCE_TO_CLIENTE_CACHE:
        return INSTANCE_TO_CLIENTE_CACHE[instance_name]

    # Buscar no banco
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT id FROM clientes WHERE whatsapp_instance = :inst AND ativo = true"),
            {"inst": instance_name}
        ).fetchone()

        if result:
            cliente_id = result[0]
        else:
            # Fallback: se não encontrar, usa cliente padrão (desenvolvimento)
            logger.warning(f"⚠️ Instância não encontrada: {instance_name}, usando cliente_id=1")
            cliente_id = 1

        # Cachear
        INSTANCE_TO_CLIENTE_CACHE[instance_name] = cliente_id
        logger.info(f"✅ Instância mapeada: {instance_name} → cliente_id={cliente_id}")

        return cliente_id
    finally:
        db.close()

@router.post("/whatsapp/{instance_name}")
async def webhook_whatsapp(instance_name: str, request: Request):
    """
    Webhook principal com IA Claude 3.5 Sonnet integrada
    """
    try:
        # Receber dados
        webhook_data = await request.json()
        logger.info(f"📨 Webhook recebido para {instance_name}")
        logger.info(f"🔍 DEBUG - Dados recebidos: {json.dumps(webhook_data, indent=2)}")

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
        cliente_id = get_cliente_id_from_instance(instance_name)
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
            # Criar sessão do banco para buscar agendamento
            from app.database import SessionLocal
            db = SessionLocal()
            try:
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
            finally:
                db.close()
        # ==================================================

        logger.info(f"🔍 DEBUG - Chamando process_with_anthropic_ai...")

        # Processar com IA Anthropic (passa cliente_id)
        response_message = await process_with_anthropic_ai(message_text, sender, push_name, cliente_id)
        logger.info(f"🔍 DEBUG - Resposta da IA recebida: {response_message[:100] if response_message else 'NENHUMA'}")

        if response_message:
            # Enviar resposta via WhatsApp
            success = await send_whatsapp_response(instance_name, sender, response_message)

            if success:
                logger.info(f"✅ Resposta IA enviada para {push_name}")
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success",
                        "response_sent": True,
                        "ai_used": True,
                        "model": "claude-3.5-sonnet"
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

async def process_with_anthropic_ai(message_text: str, sender: str, push_name: str, cliente_id: int) -> str:
    """
    Processa mensagem usando AnthropicService existente
    Multi-tenant: recebe cliente_id para processar mensagem do cliente correto
    """
    logger.info(f"🔍 INICIANDO process_with_anthropic_ai")
    logger.info(f"🔍 Parâmetros: message_text='{message_text[:50]}...', sender='{sender}', push_name='{push_name}', cliente_id={cliente_id}")

    db = SessionLocal()
    logger.info("🔍 Conexão com banco criada")

    try:
        logger.info(f"🔍 Criando AnthropicService com cliente_id={cliente_id}")

        # Inicializar serviço Anthropic com o banco
        ai_service = AnthropicService(db=db, cliente_id=cliente_id)
        logger.info("🔍 AnthropicService criado com sucesso")

        # Verificar se IA está ativa
        logger.info(f"🔍 use_real_ai = {ai_service.use_real_ai}")

        # Obter contexto da conversa usando ConversationManager (MULTI-TENANT)
        contexto_conversa = conversation_manager.get_context(sender, limit=10, cliente_id=cliente_id)
        logger.info(f"🔍 Contexto carregado para {sender} (cliente_{cliente_id}): {len(contexto_conversa)} mensagens")

        # Processar mensagem com IA
        logger.info(f"🤖 Processando com Claude 3.5 Sonnet...")
        logger.info(f"🔍 Chamando ai_service.processar_mensagem...")

        resultado = ai_service.processar_mensagem(
            mensagem=message_text,
            telefone=sender,
            contexto_conversa=contexto_conversa
        )
        
        logger.info(f"🔍 Resultado recebido: {type(resultado)}")
        logger.info(f"🔍 Chaves do resultado: {list(resultado.keys()) if isinstance(resultado, dict) else 'NÃO É DICT'}")

        # Extrair resposta
        resposta = resultado.get("resposta", "Como posso ajudá-lo?")
        intencao = resultado.get("intencao", "outros")
        proxima_acao = resultado.get("proxima_acao", "informar")
        dados_coletados = resultado.get("dados_coletados", {})

        logger.info(f"🔍 Resposta extraída: '{resposta[:100]}...'")
        logger.info(f"🎯 Intenção detectada: {intencao}")
        logger.info(f"🔄 Próxima ação: {proxima_acao}")
        logger.info(f"📋 Dados coletados: {dados_coletados}")

        # ========== VALIDAÇÃO DE CONTEXTO - REMOVIDA ==========
        # Nota: A validação de contexto foi removida pois estava sendo muito restritiva
        # e removia nomes válidos de conversas em andamento.
        # A proteção contra nomes incorretos já é feita por:
        # 1. Remoção do fallback pushName (linha 300)
        # 2. Validação de nome obrigatório antes de agendar (linha 306)
        # 3. Expiração automática do Redis em 24 horas
        # =====================================================================

        # ========== DETECTAR PERGUNTA POR HORÁRIOS DISPONÍVEIS ==========
        pergunta_horarios = any(palavra in message_text.lower() for palavra in [
            "quais horários", "que horas", "horários disponíveis", "horários livres",
            "horários tem", "horários você tem", "tem horário", "horários estão disponíveis",
            "horarios disponiveis", "horarios livres"
        ])

        if pergunta_horarios and proxima_acao == "solicitar_dados":
            logger.info("🔍 Usuário perguntou por horários disponíveis")

            # Verificar se já temos data e médico
            medico_id_raw = dados_coletados.get("medico_id")
            data_preferida_raw = dados_coletados.get("data_preferida", "")

            if medico_id_raw and data_preferida_raw:
                try:
                    # Converter data
                    if "/" in data_preferida_raw:
                        partes = data_preferida_raw.split()
                        data_br = partes[0]
                        dia, mes, ano = data_br.split("/")
                        data_str = f"{ano}-{mes}-{dia}"
                    else:
                        data_str = data_preferida_raw

                    # Buscar horários disponíveis
                    from datetime import datetime as dt, timedelta
                    data_inicio = dt.strptime(data_str, "%Y-%m-%d")
                    data_fim = data_inicio + timedelta(days=1)

                    calendario_service_temp = CalendarioService()

                    # Resolver medico_id se for string
                    if isinstance(medico_id_raw, str):
                        especialidade = dados_coletados.get("especialidade", "")
                        medico_result = db.execute(text("""
                            SELECT id FROM medicos
                            WHERE cliente_id = :cli_id AND ativo = true
                            AND (LOWER(especialidade) LIKE LOWER(:esp) OR LOWER(nome) LIKE LOWER(:esp))
                            LIMIT 1
                        """), {"cli_id": cliente_id, "esp": f"%{especialidade}%"}).fetchone()
                        medico_id_final = medico_result[0] if medico_result else 1
                    else:
                        medico_id_final = int(medico_id_raw)

                    horarios_disponiveis = calendario_service_temp.listar_horarios_disponiveis(
                        medico_id=medico_id_final,
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                        duracao_consulta=60
                    )

                    logger.info(f"📅 Encontrados {len(horarios_disponiveis)} horários para {data_str}")

                    if horarios_disponiveis:
                        resposta += f"\n\n✅ *Horários disponíveis para {dia}/{mes}/{ano}:*\n"
                        for h in horarios_disponiveis[:10]:
                            resposta += f"• {h['hora_formatada']}\n"
                        resposta += "\n📅 Qual horário você prefere?"
                    else:
                        resposta += f"\n\n😔 Infelizmente não temos horários disponíveis para {dia}/{mes}/{ano}."

                except Exception as e:
                    logger.error(f"❌ Erro ao buscar horários disponíveis: {e}")
        # ================================================================

        # Extrair e converter data de data_preferida
        data_preferida = dados_coletados.get("data_preferida", "")
        if data_preferida and "/" in data_preferida:
            try:
                partes = data_preferida.split()
                data_br = partes[0]

                # IMPORTANTE: Só processar se o usuário forneceu HORA explicitamente
                if len(partes) >= 2:
                    hora = partes[1]
                    dia, mes, ano = data_br.split("/")
                    dados_coletados["data"] = f"{ano}-{mes}-{dia}"
                    dados_coletados["hora"] = hora
                    logger.info(f"✅ Data e hora convertidas: {dados_coletados.get('data')} {dados_coletados.get('hora')}")
                else:
                    # Só converter a data, deixar hora vazia para IA pedir
                    dia, mes, ano = data_br.split("/")
                    dados_coletados["data"] = f"{ano}-{mes}-{dia}"
                    logger.info(f"📅 Data convertida: {dados_coletados.get('data')} (hora ainda não fornecida)")
            except Exception as e:
                logger.error(f"❌ Erro ao converter data '{data_preferida}': {e}")

        # Atualizar contexto da conversa usando ConversationManager (MULTI-TENANT)
        conversation_manager.add_message(
            phone=sender,
            message_type="user",
            text=message_text,
            cliente_id=cliente_id
        )
        conversation_manager.add_message(
            phone=sender,
            message_type="assistant",
            text=resposta,
            intencao=intencao,
            dados_coletados=dados_coletados,
            cliente_id=cliente_id
        )

        # ========== LÓGICA UNIFICADA DE AGENDAMENTO ==========
        # REGRA IMPORTANTE: Só agenda se TODOS os dados obrigatórios estão presentes
        # Não basta ter intenção, precisa ter TODOS os dados!
        tem_nome = bool(dados_coletados.get("nome"))
        tem_data = bool(dados_coletados.get("data"))
        tem_hora = bool(dados_coletados.get("hora"))
        tem_especialidade_ou_medico = bool(dados_coletados.get("especialidade") or dados_coletados.get("medico_id"))

        # Só agenda se:
        # 1. Usuário demonstrou intenção de agendar E
        # 2. Tem TODOS os dados obrigatórios (nome, data, hora, especialidade/médico)
        deve_agendar = (
            (intencao == "agendamento" or proxima_acao == "agendar") and
            tem_nome and
            tem_data and
            tem_hora and
            tem_especialidade_ou_medico
        )

        logger.info(f"🔍 Verificação de agendamento: deve_agendar={deve_agendar}")
        logger.info(f"   - intencao={intencao}")
        logger.info(f"   - proxima_acao={proxima_acao}")
        logger.info(f"   - tem_nome={tem_nome}")
        logger.info(f"   - tem_data={tem_data}")
        logger.info(f"   - tem_hora={tem_hora}")
        logger.info(f"   - tem_especialidade_ou_medico={tem_especialidade_ou_medico}")

        if deve_agendar:
            logger.info("💾 INICIANDO salvamento de agendamento no banco...")
            logger.info(f"🔍 DEBUG - Tipo de resposta ANTES do try: {type(resposta)}")
            logger.info(f"🔍 DEBUG - Valor de resposta: {resposta[:200] if isinstance(resposta, str) else resposta}")

            try:
                # ============================================================
                # IMPORTANTE: Usar APENAS o nome fornecido explicitamente
                # pelo usuário na conversa. NUNCA usar pushName do WhatsApp
                # pois pode conter apelidos, nomes artísticos, etc.
                # ============================================================
                nome_paciente = dados_coletados.get("nome")

                # Telefone é extraído automaticamente do WhatsApp
                telefone = sender.replace("@s.whatsapp.net", "")

                # Validação crítica: nome é obrigatório
                if not nome_paciente:
                    logger.error("❌ ERRO CRÍTICO: Tentativa de agendamento sem nome!")
                    logger.error(f"❌ pushName do WhatsApp era: '{push_name}' (NÃO usado)")
                    resposta += "\n\n⚠️ Não foi possível confirmar o agendamento. Por favor, informe seu nome completo."
                    # Envia resposta solicitando nome e encerra
                    await send_whatsapp_message(sender, resposta)
                    return resposta

                logger.info(f"📝 Dados: nome={nome_paciente}, telefone={telefone}")

                # Criar ou buscar/atualizar paciente
                paciente = db.execute(text("""
                    SELECT id FROM pacientes WHERE telefone = :tel LIMIT 1
                """), {"tel": telefone}).fetchone()

                if not paciente:
                    logger.info("➕ Criando novo paciente...")
                    convenio = dados_coletados.get("convenio", "Particular")

                    # TELEFONE é salvo automaticamente na tabela pacientes
                    # Campo: telefone (String, único, obrigatório)
                    # Fonte: Extraído do WhatsApp (remoteJid)
                    result = db.execute(text("""
                        INSERT INTO pacientes (nome, telefone, cliente_id, convenio, criado_em, atualizado_em)
                        VALUES (:nome, :tel, :cli_id, :conv, NOW(), NOW())
                        RETURNING id
                    """), {"nome": nome_paciente, "tel": telefone, "cli_id": cliente_id, "conv": convenio})
                    paciente_id = result.scalar()
                    logger.info(f"✅ Paciente criado com ID: {paciente_id}")
                else:
                    paciente_id = paciente[0]  # Acesso por índice, pois fetchone() retorna Row
                    logger.info(f"✅ Paciente existente encontrado: ID {paciente_id}")

                    # ATUALIZAR o nome do paciente se for diferente
                    convenio = dados_coletados.get("convenio", "Particular")
                    db.execute(text("""
                        UPDATE pacientes
                        SET nome = :nome, convenio = :conv, atualizado_em = NOW()
                        WHERE id = :pac_id
                    """), {"nome": nome_paciente, "conv": convenio, "pac_id": paciente_id})
                    logger.info(f"✅ Nome do paciente atualizado para: {nome_paciente}")

                # Resolver medico_id (pode vir como string com CRM ou nome)
                medico_id_raw = dados_coletados.get("medico_id", 1)
                logger.info(f"🔍 medico_id_raw recebido: {medico_id_raw} (tipo: {type(medico_id_raw)})")

                # Se for string, buscar o ID real do médico
                if isinstance(medico_id_raw, str):
                    especialidade = dados_coletados.get("especialidade", "")
                    logger.info(f"🔍 Buscando médico por especialidade: {especialidade}")

                    # Buscar médico por especialidade ou nome
                    medico_result = db.execute(text("""
                        SELECT id FROM medicos
                        WHERE cliente_id = :cli_id
                        AND ativo = true
                        AND (
                            LOWER(especialidade) LIKE LOWER(:esp)
                            OR LOWER(nome) LIKE LOWER(:esp)
                            OR crm LIKE :crm
                        )
                        LIMIT 1
                    """), {
                        "cli_id": cliente_id,
                        "esp": f"%{especialidade}%",
                        "crm": f"%{medico_id_raw}%"
                    }).fetchone()

                    if medico_result:
                        medico_id = medico_result[0]
                        logger.info(f"✅ Médico encontrado com ID: {medico_id}")
                    else:
                        logger.warning(f"⚠️ Médico não encontrado, usando ID padrão: 1")
                        medico_id = 1
                else:
                    medico_id = int(medico_id_raw)

                data_hora = f"{dados_coletados['data']} {dados_coletados['hora']}:00"
                motivo = dados_coletados.get("especialidade") or dados_coletados.get("motivo") or "Consulta via WhatsApp"

                logger.info(f"📅 Criando agendamento: medico_id={medico_id}, data_hora={data_hora}, motivo={motivo}")

                # ========== VERIFICAR DISPONIBILIDADE ANTES DE SALVAR ==========
                calendario_service = CalendarioService()
                data_hora_obj = datetime.strptime(data_hora, "%Y-%m-%d %H:%M:%S")

                logger.info(f"🔍 Verificando disponibilidade do médico {medico_id} para {data_hora_obj}")
                disponibilidade = calendario_service.verificar_disponibilidade_medico(
                    medico_id=medico_id,
                    data_consulta=data_hora_obj,
                    duracao_minutos=60
                )

                if not disponibilidade.get('disponivel', False):
                    motivo_indisponivel = disponibilidade.get('motivo', 'Horário não disponível')
                    logger.warning(f"⚠️ Horário indisponível: {motivo_indisponivel}")

                    # Formatar data para exibição (de YYYY-MM-DD para DD/MM/YYYY)
                    data_display = dados_coletados.get('data', '')
                    if '-' in data_display:
                        ano, mes, dia = data_display.split('-')
                        data_display = f"{dia}/{mes}/{ano}"

                    # ========== BUSCAR HORÁRIOS DISPONÍVEIS ==========
                    logger.info(f"🔍 Buscando horários disponíveis para o dia {data_display}")

                    # Buscar horários disponíveis para o mesmo dia
                    from datetime import datetime as dt, timedelta
                    data_inicio = dt.strptime(dados_coletados['data'], "%Y-%m-%d")
                    data_fim = data_inicio + timedelta(days=1)

                    horarios_disponiveis = calendario_service.listar_horarios_disponiveis(
                        medico_id=medico_id,
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                        duracao_consulta=60
                    )

                    logger.info(f"📅 Encontrados {len(horarios_disponiveis)} horários disponíveis")

                    # Informar ao usuário que o horário não está disponível
                    resposta = f"❌ Desculpe, mas o horário *{dados_coletados.get('hora')}* do dia *{data_display}* não está disponível.\n\n"
                    resposta += f"💡 Motivo: {motivo_indisponivel}\n\n"

                    # Adicionar horários disponíveis se existirem
                    if horarios_disponiveis:
                        resposta += f"✅ *Horários disponíveis para {data_display}:*\n"
                        for h in horarios_disponiveis[:10]:  # Limitar a 10 horários
                            resposta += f"• {h['hora_formatada']}\n"
                        resposta += "\n📅 Qual desses horários você prefere?"
                    else:
                        resposta += "😔 Infelizmente não temos mais horários disponíveis neste dia.\n"
                        resposta += "Poderia escolher outra data?"

                    # Retornar sem salvar e pedir novo horário
                    return resposta

                logger.info(f"✅ Horário disponível! Prosseguindo com agendamento...")
                # ================================================================

                db.execute(text("""
                    INSERT INTO agendamentos (
                        paciente_id, medico_id, data_hora, status,
                        tipo_atendimento, motivo_consulta, criado_em, atualizado_em
                    )
                    VALUES (
                        :pac_id, :med_id, :dt, 'confirmado',
                        'consulta', :motivo, NOW(), NOW()
                    )
                """), {
                    "pac_id": paciente_id,
                    "med_id": medico_id,
                    "dt": data_hora,
                    "motivo": motivo
                })

                db.commit()
                logger.info(f"✅✅✅ AGENDAMENTO SALVO COM SUCESSO! Paciente: {nome_paciente}, Data: {data_hora}")

                # SUBSTITUIR qualquer mensagem anterior por confirmação definitiva
                if isinstance(resposta, str) and '\n\n' in resposta:
                    resposta = resposta.split('\n\n')[0]
                elif not isinstance(resposta, str):
                    resposta = str(resposta)

                resposta += f"\n\n✅ *Seu agendamento foi confirmado com sucesso!*\n\n📋 *Resumo:*\n"
                resposta += f"👤 Paciente: {nome_paciente}\n"
                resposta += f"📅 Data: {dados_coletados.get('data', 'N/A')}\n"
                resposta += f"⏰ Horário: {dados_coletados.get('hora', 'N/A')}\n"
                if motivo and motivo != "Consulta via WhatsApp":
                    resposta += f"🏥 Motivo: {motivo}\n"
                resposta += f"\n💡 *Lembrete:* Por favor, chegue com 15 minutos de antecedência e traga seus documentos (RG, carteirinha do convênio se houver).\n\n"
                resposta += f"Qualquer dúvida, estamos à disposição! 😊"

            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"❌❌❌ ERRO ao criar agendamento: {e}")
                logger.error(f"❌ TRACEBACK COMPLETO:\n{error_trace}")
                logger.error(f"❌ Dados coletados: {dados_coletados}")
                logger.error(f"❌ Push name: {push_name}")
                logger.error(f"❌ Sender: {sender}")
                db.rollback()
                # SUBSTITUIR resposta anterior por mensagem de erro clara
                if isinstance(resposta, str) and '\n\n' in resposta:
                    resposta = resposta.split('\n\n')[0]
                elif not isinstance(resposta, str):
                    resposta = str(resposta) if resposta else "Processando seu agendamento"

                resposta += f"\n\n❌ *Desculpe, ocorreu um erro ao salvar seu agendamento.*\n\n"
                resposta += f"⚠️ Erro técnico: {str(e)[:100]}\n\n"
                resposta += f"Por favor, tente novamente ou entre em contato conosco pelo telefone."

        # Adicionar outras ações baseadas na intenção
        elif proxima_acao == "verificar_agenda" and dados_coletados.get("medico_id"):
            # Aqui poderia integrar com calendario_service
            resposta += "\n\n📅 _Verificando agenda disponível..._"

        # Formatar resposta para WhatsApp
        resposta_formatada = formatar_para_whatsapp(resposta)
        logger.info(f"🔍 Resposta formatada: '{resposta_formatada[:100]}...'")

        return resposta_formatada

    except Exception as e:
        logger.error(f"❌ ERRO ao processar com IA: {e}", exc_info=True)
        logger.info(f"🔍 Usando fallback response...")
        # Fallback para resposta simples
        return get_fallback_response(message_text, push_name)
    finally:
        logger.info(f"🔍 Fechando conexão com banco")
        db.close()

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

@router.post("/whatsapp")
async def webhook_global(request: Request):
    """
    Webhook alternativo sem instance_name
    Usa instância padrão 'Clinica2024' para desenvolvimento
    """
    return await webhook_whatsapp("Clinica2024", request)

@router.get("/whatsapp/test")
async def test_webhook():
    """Endpoint de teste - usa cliente padrão"""
    cliente_id_teste = 1  # Cliente padrão para testes

    # Testar conexão com banco
    db = SessionLocal()
    try:
        ai_service = AnthropicService(db=db, cliente_id=cliente_id_teste)
        ai_available = ai_service.use_real_ai
    except:
        ai_available = False
    finally:
        db.close()

    return {
        "status": "active",
        "multi_tenant": True,
        "ai_configured": bool(os.getenv('ANTHROPIC_API_KEY')),
        "ai_available": ai_available,
        "model": "claude-3.5-sonnet-20241022",
        "cliente_id_teste": cliente_id_teste,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/whatsapp/clear/{phone}")
async def clear_conversation(phone: str):
    """Limpa histórico de conversa de um número"""
    success = conversation_manager.clear_context(phone)
    if success:
        return {"status": "cleared", "phone": phone, "storage": "redis" if conversation_manager.redis_client else "memory"}
    return {"status": "error", "phone": phone}

@router.get("/whatsapp/conversations")
async def list_conversations():
    """Lista todas as conversas ativas"""
    phones = conversation_manager.get_all_active_conversations()
    return {
        "status": "success",
        "count": len(phones),
        "conversations": phones,
        "storage": "redis" if conversation_manager.redis_client else "memory"
    }

@router.get("/whatsapp/refresh-qr")
async def refresh_qr_code():
    """Gera novo QR Code para reconexão do WhatsApp - Retorna HTML"""
    from fastapi.responses import HTMLResponse
    try:
        import base64

        url = f"{EVOLUTION_API_URL}/instance/connect/Clinica2024"
        headers = {"apikey": EVOLUTION_API_KEY}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    if 'base64' in data:
                        qr_base64 = data['base64']

                        # Salvar imagem PNG também
                        img_data = qr_base64.split(',')[1]
                        png_path = '/root/sistema_agendamento/static/whatsapp_qr.png'

                        with open(png_path, 'wb') as f:
                            f.write(base64.b64decode(img_data))

                        logger.info(f"✅ Novo QR Code gerado e salvo em {png_path}")

                        # Retornar HTML ao invés de JSON
                        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>QR Code - WhatsApp ProSaude</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
            padding: 20px;
        }}
        .container {{
            text-align: center;
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            animation: fadeIn 0.5s ease-in;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        h1 {{
            color: #128C7E;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }}
        .instructions {{
            margin: 20px 0;
            line-height: 1.8;
            text-align: left;
        }}
        .instructions ol {{
            padding-left: 20px;
        }}
        .instructions li {{
            margin: 10px 0;
            color: #333;
        }}
        .qr-container {{
            background: white;
            padding: 20px;
            border-radius: 15px;
            display: inline-block;
            margin: 20px 0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        img {{
            max-width: 350px;
            width: 100%;
            height: auto;
            border-radius: 10px;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
            color: #856404;
            text-align: left;
        }}
        .success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
            color: #155724;
            text-align: left;
        }}
        .refresh-btn {{
            background: #25D366;
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin-top: 20px;
            transition: all 0.3s;
            box-shadow: 0 4px 10px rgba(37, 211, 102, 0.3);
        }}
        .refresh-btn:hover {{
            background: #1fb855;
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(37, 211, 102, 0.4);
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 14px;
        }}
        .countdown {{
            font-size: 18px;
            font-weight: bold;
            color: #128C7E;
            margin: 15px 0;
        }}
        @media (max-width: 600px) {{
            .container {{ padding: 20px; }}
            h1 {{ font-size: 24px; }}
            img {{ max-width: 280px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 Conectar WhatsApp</h1>
        <p class="subtitle">Sistema ProSaude - Horário Inteligente</p>

        <div class="success">
            <strong>✅ QR Code gerado com sucesso!</strong>
        </div>

        <div class="instructions">
            <p><strong>📋 Siga os passos:</strong></p>
            <ol>
                <li>Abra o <strong>WhatsApp</strong> no celular que responde aos clientes</li>
                <li>Toque em <strong>Mais opções (⋮)</strong> ou <strong>Configurações</strong></li>
                <li>Toque em <strong>Aparelhos conectados</strong></li>
                <li>Toque em <strong>Conectar um aparelho</strong></li>
                <li>Aponte a câmera para o QR Code abaixo:</li>
            </ol>
        </div>

        <div class="qr-container">
            <img src="{qr_base64}" alt="QR Code WhatsApp">
        </div>

        <div class="countdown" id="countdown">Atualizando em 25 segundos...</div>

        <div class="warning">
            <strong>⚠️ Importante:</strong><br>
            • Este QR Code expira rapidamente<br>
            • A página atualiza automaticamente a cada 25 segundos<br>
            • Se não conseguir escanear, aguarde a atualização automática
        </div>

        <button class="refresh-btn" onclick="location.reload()">🔄 Atualizar QR Code Agora</button>

        <div class="footer">
            ProSaude - Agendamento Inteligente com IA<br>
            Gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M:%S")}
        </div>
    </div>

    <script>
        // Countdown timer
        let seconds = 25;
        const countdownEl = document.getElementById('countdown');

        setInterval(() => {{
            seconds--;
            if (seconds > 0) {{
                countdownEl.textContent = `Atualizando em ${{seconds}} segundos...`;
            }} else {{
                countdownEl.textContent = 'Atualizando...';
            }}
        }}, 1000);

        // Auto-refresh após 25 segundos
        setTimeout(() => {{
            location.reload();
        }}, 25000);
    </script>
</body>
</html>'''

                        return HTMLResponse(content=html_content)
                    else:
                        return HTMLResponse(content=f'''
                        <html>
                        <body style="font-family: Arial; text-align: center; padding: 50px;">
                            <h1 style="color: red;">❌ Erro</h1>
                            <p>QR Code não disponível na resposta da API</p>
                            <button onclick="location.reload()" style="padding: 10px 20px; font-size: 16px;">Tentar Novamente</button>
                        </body>
                        </html>
                        ''')
                else:
                    error = await response.text()
                    return HTMLResponse(content=f'''
                    <html>
                    <body style="font-family: Arial; text-align: center; padding: 50px;">
                        <h1 style="color: red;">❌ Erro na Evolution API</h1>
                        <p>{error}</p>
                        <button onclick="location.reload()" style="padding: 10px 20px; font-size: 16px;">Tentar Novamente</button>
                    </body>
                    </html>
                    ''')

    except Exception as e:
        logger.error(f"❌ Erro ao gerar QR Code: {e}")
        return HTMLResponse(content=f'''
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ Erro</h1>
            <p>{str(e)}</p>
            <button onclick="location.reload()" style="padding: 10px 20px; font-size: 16px;">Tentar Novamente</button>
        </body>
        </html>
        ''')

@router.get("/whatsapp/status")
async def whatsapp_status():
    """Retorna status da conexão WhatsApp de todas as instâncias"""
    try:
        from app.services.whatsapp_monitor import whatsapp_monitor

        stats = await whatsapp_monitor.verificar_todas_instancias()

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        logger.error(f"❌ Erro ao verificar status: {e}")
        return {
            "success": False,
            "error": str(e)
        }
