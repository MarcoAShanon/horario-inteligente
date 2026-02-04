"""
Webhook para WhatsApp Business API Oficial (Meta Cloud API)
Endpoint separado para facilitar migração gradual
"""

import os
import logging
import tempfile
import base64
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.services.whatsapp_official_service import WhatsAppOfficialService
from app.services.whatsapp_interface import WhatsAppMessage
from app.services.anthropic_service import AnthropicService
from app.services.conversation_manager import ConversationManager

# Imports para persistência de conversas no PostgreSQL
from app.services.conversa_service import ConversaService
from app.models.conversa import Conversa, StatusConversa
from app.models.mensagem import DirecaoMensagem, RemetenteMensagem, TipoMensagem

# Import para notificações WebSocket em tempo real
from app.services.websocket_manager import websocket_manager

# Imports para criação de agendamentos
from datetime import datetime
import re
import pytz

# Timezone Brasil
TZ_BRAZIL = pytz.timezone('America/Sao_Paulo')

def converter_para_brasil(dt):
    """Converte datetime UTC para horário de Brasília."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(TZ_BRAZIL).isoformat()
from app.models.agendamento import Agendamento
from app.models.paciente import Paciente
from app.models.medico import Medico
from app.utils.timezone_helper import make_aware_brazil
from app.services.agendamento_service import AgendamentoService

# Imports para áudio (OpenAI Whisper + TTS)
from app.services.openai_audio_service import get_audio_service
from app.services.audio_preference_service import deve_enviar_audio, detectar_preferencia_na_mensagem

# Imports para lembretes inteligentes
from app.services.lembrete_service import lembrete_service

# Imports para tratamento de botões interativos
from app.services.button_handler_service import get_button_handler

logger = logging.getLogger(__name__)

# Rate Limiter para webhooks
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# Instância do serviço
whatsapp_service = WhatsAppOfficialService()
conversation_manager = ConversationManager()

# Configurações de áudio
ENABLE_AUDIO_INPUT = os.getenv("ENABLE_AUDIO_INPUT", "true").lower() == "true"
ENABLE_AUDIO_OUTPUT = os.getenv("ENABLE_AUDIO_OUTPUT", "true").lower() == "true"
AUDIO_OUTPUT_MODE = os.getenv("AUDIO_OUTPUT_MODE", "hybrid")  # text, audio, hybrid


@router.get("/webhook/whatsapp-official")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    """
    Verificação do webhook pela Meta.

    A Meta envia uma requisição GET para verificar o webhook:
    GET /webhook/whatsapp-official?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=CHALLENGE

    Devemos retornar o challenge se o token for válido.
    """

    if hub_mode and hub_token:
        result = whatsapp_service.verify_webhook_token(hub_mode, hub_token, hub_challenge)

        if result:
            # Log sem expor dados sensíveis
            print(f"[Webhook Official] Verificação bem-sucedida!")
            return PlainTextResponse(content=result)
        else:
            # SEGURANÇA: Não logar tokens - apenas indicar falha
            print(f"[Webhook Official] Token de verificação inválido")
            raise HTTPException(status_code=403, detail="Token de verificação inválido")

    raise HTTPException(status_code=400, detail="Parâmetros de verificação ausentes")


@router.post("/webhook/whatsapp-official")
@limiter.limit("200/minute")
async def receive_webhook(request: Request):
    """
    Recebe webhooks de mensagens da Meta.

    Este endpoint processa mensagens recebidas do WhatsApp Business API Oficial.
    """

    try:
        # Parse do body
        webhook_data = await request.json()

        print(f"[Webhook Official] Recebido: {webhook_data.get('object', 'unknown')}")

        # Verifica se é webhook válido
        if not whatsapp_service.is_valid_webhook(webhook_data):
            # Retorna 200 mesmo para webhooks inválidos (exigência da Meta)
            return {"status": "ignored"}

        # Parse para formato padronizado
        message = whatsapp_service.parse_webhook(webhook_data)

        if not message:
            return {"status": "no_message"}

        print(f"[Webhook Official] Mensagem de {message.sender}: {message.text[:50]}...")

        # Processa a mensagem
        await process_message(message)

        return {"status": "processed"}

    except Exception as e:
        print(f"[Webhook Official] Erro: {e}")
        # Sempre retorna 200 para a Meta não reenviar
        return {"status": "error", "message": str(e)}


async def process_message(message: WhatsAppMessage):
    """
    Processa mensagem recebida usando IA.
    Persiste conversas no PostgreSQL e mantém contexto no Redis.
    """

    db = SessionLocal()

    try:
        # 1. Determina o cliente_id (tenant) baseado no phone_number_id
        cliente_id = get_cliente_id_from_phone_number_id(message.phone_number_id, db)

        # 1.1 Definir contexto de billing para logging de mensagens WhatsApp
        try:
            from app.services.whatsapp_billing_service import set_billing_context
            set_billing_context(cliente_id)
        except Exception:
            pass

        # 2. Criar ou recuperar conversa no PostgreSQL
        conversa, is_nova_conversa = ConversaService.criar_ou_recuperar_conversa(
            db=db,
            cliente_id=cliente_id,
            telefone=message.sender
        )
        logger.info(f"[Webhook Official] Conversa {conversa.id} - Status: {conversa.status.value} - Nova: {is_nova_conversa}")

        # 2.1 Se for nova conversa, notificar via WebSocket para atualizar lista lateral
        if is_nova_conversa:
            try:
                await websocket_manager.send_nova_conversa(cliente_id, {
                    "id": conversa.id,
                    "paciente_telefone": conversa.paciente_telefone,
                    "paciente_nome": conversa.paciente_nome,
                    "status": conversa.status.value,
                    "ultima_mensagem": message.text[:50] if message.text else "",
                    "ultima_mensagem_at": conversa.criado_em.isoformat() if conversa.criado_em else None,
                    "nao_lidas": 1
                })
                logger.info(f"[Webhook Official] 📢 Nova conversa notificada via WebSocket: {conversa.id}")
            except Exception as ws_error:
                logger.warning(f"[Webhook Official] Erro ao notificar nova conversa: {ws_error}")

        # 3. Determinar tipo da mensagem e processar áudio se necessário
        tipo_mensagem = TipoMensagem.TEXTO
        mensagem_foi_audio = False
        texto_original = message.text

        if message.message_type == "audio":
            tipo_mensagem = TipoMensagem.AUDIO
            mensagem_foi_audio = True

            # Transcrever áudio se habilitado
            if ENABLE_AUDIO_INPUT and message.audio_url:
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

        elif message.message_type == "image":
            tipo_mensagem = TipoMensagem.IMAGEM
        elif message.message_type == "document":
            tipo_mensagem = TipoMensagem.DOCUMENTO

        # 4. Salvar mensagem do paciente no PostgreSQL
        logger.info(f"[Webhook Official] Salvando mensagem: text='{message.text}', type={message.message_type}")

        # Garantir que temos conteúdo válido
        conteudo = message.text or "[Mensagem sem texto]"

        mensagem_paciente = ConversaService.adicionar_mensagem(
            db=db,
            conversa_id=conversa.id,
            direcao=DirecaoMensagem.ENTRADA,
            remetente=RemetenteMensagem.PACIENTE,
            conteudo=conteudo,
            tipo=tipo_mensagem,
            midia_url=message.media_url if hasattr(message, 'media_url') else None
        )
        logger.info(f"[Webhook Official] Mensagem do paciente salva no PostgreSQL (ID: {mensagem_paciente.id})")

        # 4.1 Notificar via WebSocket (nova mensagem do paciente)
        await websocket_manager.send_nova_mensagem(
            cliente_id=cliente_id,
            conversa_id=conversa.id,
            mensagem={
                "id": mensagem_paciente.id,
                "direcao": "entrada",
                "remetente": "paciente",
                "tipo": tipo_mensagem.value,
                "conteudo": message.text,
                "timestamp": converter_para_brasil(mensagem_paciente.timestamp)
            }
        )

        # 5. Verificar se IA está ativa para esta conversa
        if conversa.status == StatusConversa.HUMANO_ASSUMIU:
            logger.info(f"[Webhook Official] Conversa {conversa.id} está sendo atendida por humano. IA não responderá.")
            # Mensagem já foi notificada acima, atendente verá no painel
            return

        # 5.1 Verificar se é resposta a um lembrete de consulta
        resultado_lembrete = await lembrete_service.processar_resposta_lembrete(
            db=db,
            telefone=message.sender,
            texto_resposta=message.text,
            cliente_id=cliente_id
        )

        if resultado_lembrete.get("tem_lembrete_pendente"):
            logger.info(f"[Webhook Official] 🔔 Resposta de lembrete detectada: {resultado_lembrete.get('intencao')}")

            texto_resposta = resultado_lembrete.get("resposta", "")

            if texto_resposta:
                # Salvar resposta no PostgreSQL
                mensagem_ia = ConversaService.adicionar_mensagem(
                    db=db,
                    conversa_id=conversa.id,
                    direcao=DirecaoMensagem.SAIDA,
                    remetente=RemetenteMensagem.IA,
                    conteudo=texto_resposta,
                    tipo=TipoMensagem.TEXTO
                )

                # Notificar via WebSocket
                await websocket_manager.send_nova_mensagem(
                    cliente_id=cliente_id,
                    conversa_id=conversa.id,
                    mensagem={
                        "id": mensagem_ia.id,
                        "direcao": "saida",
                        "remetente": "ia",
                        "tipo": "texto",
                        "conteudo": texto_resposta,
                        "timestamp": converter_para_brasil(mensagem_ia.timestamp)
                    }
                )

                # Enviar resposta pelo WhatsApp
                await whatsapp_service.send_text(
                    to=message.sender,
                    message=texto_resposta,
                    phone_number_id=message.phone_number_id
                )

                # Salvar no contexto Redis
                conversation_manager.add_message(
                    phone=message.sender,
                    message_type="user",
                    text=message.text,
                    intencao="resposta_lembrete",
                    dados_coletados={},
                    cliente_id=cliente_id
                )
                conversation_manager.add_message(
                    phone=message.sender,
                    message_type="assistant",
                    text=texto_resposta,
                    intencao=resultado_lembrete.get("intencao", ""),
                    dados_coletados={},
                    cliente_id=cliente_id
                )

            # Se ação é aguardar resposta, não processa mais
            # Se for confirmar/cancelar, já processou
            return

        # 5.2 Verificar se é clique em botão de template
        if message.message_type == "button":
            logger.info(f"[Webhook Official] 🔘 Botão clicado: '{message.text}'")

            button_handler = get_button_handler()
            resultado_botao = await button_handler.processar_botao(
                db=db,
                telefone=message.sender,
                button_text=message.text,
                cliente_id=cliente_id
            )

            if resultado_botao.get("handled"):
                texto_resposta = resultado_botao.get("response", "")

                if texto_resposta:
                    # Salvar resposta no PostgreSQL
                    mensagem_ia = ConversaService.adicionar_mensagem(
                        db=db,
                        conversa_id=conversa.id,
                        direcao=DirecaoMensagem.SAIDA,
                        remetente=RemetenteMensagem.IA,
                        conteudo=texto_resposta,
                        tipo=TipoMensagem.TEXTO
                    )

                    # Notificar via WebSocket
                    await websocket_manager.send_nova_mensagem(
                        cliente_id=cliente_id,
                        conversa_id=conversa.id,
                        mensagem={
                            "id": mensagem_ia.id,
                            "direcao": "saida",
                            "remetente": "ia",
                            "tipo": "texto",
                            "conteudo": texto_resposta,
                            "timestamp": converter_para_brasil(mensagem_ia.timestamp)
                        }
                    )

                    # Enviar resposta pelo WhatsApp
                    await whatsapp_service.send_text(
                        to=message.sender,
                        message=texto_resposta,
                        phone_number_id=message.phone_number_id
                    )

                    # Salvar no contexto Redis
                    conversation_manager.add_message(
                        phone=message.sender,
                        message_type="user",
                        text=message.text,
                        intencao=f"botao_{resultado_botao.get('action', '')}",
                        dados_coletados={},
                        cliente_id=cliente_id
                    )
                    conversation_manager.add_message(
                        phone=message.sender,
                        message_type="assistant",
                        text=texto_resposta,
                        intencao=resultado_botao.get("action", ""),
                        dados_coletados={},
                        cliente_id=cliente_id
                    )

                logger.info(
                    f"[Webhook Official] ✅ Botão processado: "
                    f"ação={resultado_botao.get('action')}, "
                    f"notificar_clinica={resultado_botao.get('notify_clinic')}"
                )

                # ButtonHandler já enviou resposta, não chamar IA novamente
                # A próxima mensagem do paciente será processada normalmente pela IA
                return

        # 6. Obtém contexto da conversa do Redis
        contexto = conversation_manager.get_context(
            phone=message.sender,
            limit=10,
            cliente_id=cliente_id
        )

        # 7. Se for resposta de botão/lista, usa o ID como texto
        texto_para_processar = message.text
        if message.button_reply_id:
            texto_para_processar = message.button_reply_id
        elif message.list_reply_id:
            texto_para_processar = message.list_reply_id

        # 8. Processa com IA
        anthropic_service = AnthropicService(db, cliente_id)
        resposta = anthropic_service.processar_mensagem(
            mensagem=texto_para_processar,
            telefone=message.sender,
            contexto_conversa=contexto
        )

        texto_resposta = resposta.get("resposta", "Desculpe, não entendi.")

        # 9. Salvar resposta da IA no PostgreSQL
        mensagem_ia = ConversaService.adicionar_mensagem(
            db=db,
            conversa_id=conversa.id,
            direcao=DirecaoMensagem.SAIDA,
            remetente=RemetenteMensagem.IA,
            conteudo=texto_resposta,
            tipo=TipoMensagem.TEXTO
        )
        logger.info(f"[Webhook Official] Resposta da IA salva no PostgreSQL")

        # 9.1 Notificar via WebSocket (resposta da IA)
        await websocket_manager.send_nova_mensagem(
            cliente_id=cliente_id,
            conversa_id=conversa.id,
            mensagem={
                "id": mensagem_ia.id,
                "direcao": "saida",
                "remetente": "ia",
                "tipo": "texto",
                "conteudo": texto_resposta,
                "timestamp": converter_para_brasil(mensagem_ia.timestamp)
            }
        )

        # 10. Salva contexto no Redis (para a IA ter histórico rápido)
        conversation_manager.add_message(
            phone=message.sender,
            message_type="user",
            text=message.text,
            intencao="",
            dados_coletados={},
            cliente_id=cliente_id
        )

        conversation_manager.add_message(
            phone=message.sender,
            message_type="assistant",
            text=texto_resposta,
            intencao=resposta.get("intencao", ""),
            dados_coletados=resposta.get("dados_coletados", {}),
            cliente_id=cliente_id
        )

        # 11. Processar ações especiais baseadas na resposta da IA
        proxima_acao = resposta.get("proxima_acao", "")
        dados_coletados = resposta.get("dados_coletados", {})

        logger.info(f"[Webhook Official] proxima_acao={proxima_acao}, dados_coletados={dados_coletados}")

        # 11.1 Se a IA sinalizou que deve agendar, criar o agendamento
        if proxima_acao == "agendar":
            agendamento_criado = await criar_agendamento_from_ia(
                db=db,
                cliente_id=cliente_id,
                telefone=message.sender,
                dados_coletados=dados_coletados
            )

            # Verificar se retornou erro de horário indisponível
            if isinstance(agendamento_criado, dict) and agendamento_criado.get("erro") == "horario_indisponivel":
                data_hora_conflito = agendamento_criado.get("data_hora")
                medico_nome = agendamento_criado.get("medico_nome", "o médico")
                medico_id = dados_coletados.get("medico_id")
                data_formatada = data_hora_conflito.strftime("%d/%m/%Y às %H:%M") if data_hora_conflito else "este horário"

                # Buscar horários disponíveis para o mesmo dia
                horarios_disponiveis_msg = ""
                if data_hora_conflito and medico_id:
                    try:
                        agendamento_service = AgendamentoService(db)
                        horarios_livres = agendamento_service.obter_horarios_disponiveis(
                            medico_id=medico_id,
                            data_consulta=data_hora_conflito.date(),
                            duracao_minutos=30
                        )
                        if horarios_livres:
                            # Limitar a 5 horários para não poluir
                            horarios_exibir = horarios_livres[:5]
                            horarios_disponiveis_msg = f"\n\n📋 Horários disponíveis para {data_hora_conflito.strftime('%d/%m/%Y')}:\n"
                            horarios_disponiveis_msg += ", ".join(horarios_exibir)
                            if len(horarios_livres) > 5:
                                horarios_disponiveis_msg += f" (e mais {len(horarios_livres) - 5})"
                        else:
                            horarios_disponiveis_msg = "\n\n⚠️ Infelizmente não há mais horários disponíveis neste dia."
                    except Exception as e:
                        logger.warning(f"[Webhook Official] Erro ao buscar horários disponíveis: {e}")

                # Substituir resposta da IA por mensagem de horário indisponível
                texto_resposta = f"😔 Desculpe, mas o horário de {data_formatada} não está mais disponível para {medico_nome}."
                texto_resposta += horarios_disponiveis_msg
                texto_resposta += "\n\nQual horário você prefere?"

                logger.warning(f"[Webhook Official] ⚠️ Horário indisponível: {data_formatada}")
                agendamento_criado = None  # Limpar para não confundir

            elif agendamento_criado and hasattr(agendamento_criado, 'id'):
                logger.info(f"[Webhook Official] ✅ Agendamento criado: ID {agendamento_criado.id}")
            else:
                logger.warning(f"[Webhook Official] ⚠️ Falha ao criar agendamento com dados: {dados_coletados}")

        # 11.2 Verificar preferência de áudio e enviar resposta
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

        # 11.3 Envia resposta pelo WhatsApp
        if proxima_acao == "escolher_especialidade":
            # Envia com botões de especialidade
            from app.services.whatsapp_interface import InteractiveButton

            buttons = [
                InteractiveButton(id="cardio", title="Cardiologia"),
                InteractiveButton(id="orto", title="Ortopedia"),
                InteractiveButton(id="clinico", title="Clínico Geral")
            ]

            await whatsapp_service.send_interactive_buttons(
                to=message.sender,
                text=texto_resposta,
                buttons=buttons,
                phone_number_id=message.phone_number_id
            )
        else:
            # Envia texto simples
            await whatsapp_service.send_text(
                to=message.sender,
                message=texto_resposta,
                phone_number_id=message.phone_number_id
            )

        # 11.4 Enviar áudio se habilitado e preferência permitir
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
                                conversa_id=conversa.id,
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

        # 11.5 Enviar mensagem de confirmação de preferência se houver
        if mensagem_preferencia:
            await whatsapp_service.send_text(
                to=message.sender,
                message=mensagem_preferencia,
                phone_number_id=message.phone_number_id
            )

    except Exception as e:
        import traceback
        logger.error(f"[Webhook Official] Erro ao processar: {e}")
        logger.error(f"[Webhook Official] Traceback: {traceback.format_exc()}")

        # Envia mensagem de erro amigável
        await whatsapp_service.send_text(
            to=message.sender,
            message="Desculpe, estou com dificuldades técnicas no momento. Por favor, tente novamente em alguns instantes.",
            phone_number_id=message.phone_number_id
        )

    finally:
        db.close()


async def criar_agendamento_from_ia(
    db: Session,
    cliente_id: int,
    telefone: str,
    dados_coletados: dict
) -> Agendamento:
    """
    Cria um agendamento a partir dos dados coletados pela IA.

    Espera dados_coletados com:
    - nome: str (nome do paciente)
    - especialidade: str (opcional)
    - medico_id: int (ID do médico)
    - convenio: str (nome do convênio ou "particular")
    - data_preferida: str (formato "DD/MM/YYYY HH:MM" ou "DD/MM/YYYY")
    """
    try:
        nome = dados_coletados.get("nome")
        medico_id = dados_coletados.get("medico_id")
        convenio = dados_coletados.get("convenio", "particular")
        data_str = dados_coletados.get("data_preferida")
        # Prioriza motivo_consulta, senão usa especialidade como fallback
        motivo_consulta = dados_coletados.get("motivo_consulta") or dados_coletados.get("especialidade", "")

        # Validar dados mínimos
        if not nome or not medico_id or not data_str:
            logger.warning(f"[Agendamento] Dados insuficientes: nome={nome}, medico_id={medico_id}, data={data_str}")
            return None

        # Parsear data/hora
        data_hora = None
        formatos = [
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y %Hh",
            "%d/%m/%Y %H",
            "%d/%m/%Y"
        ]

        for fmt in formatos:
            try:
                data_hora = datetime.strptime(data_str.strip(), fmt)
                break
            except ValueError:
                continue

        if not data_hora:
            # Tentar extrair data e hora separadamente
            match = re.search(r'(\d{2}/\d{2}/\d{4})', data_str)
            if match:
                data_hora = datetime.strptime(match.group(1), "%d/%m/%Y")
                # Procurar hora
                hora_match = re.search(r'(\d{1,2})[h:]?(\d{0,2})?', data_str.replace(match.group(1), ''))
                if hora_match:
                    hora = int(hora_match.group(1))
                    minuto = int(hora_match.group(2)) if hora_match.group(2) else 0
                    data_hora = data_hora.replace(hour=hora, minute=minuto)

        if not data_hora:
            logger.warning(f"[Agendamento] Não foi possível parsear data: {data_str}")
            return None

        # Se não tem hora, definir 9h como padrão
        if data_hora.hour == 0 and data_hora.minute == 0:
            data_hora = data_hora.replace(hour=9, minute=0)

        # Converter para timezone de Brasília (UTC-3)
        data_hora = make_aware_brazil(data_hora)
        logger.info(f"[Agendamento] Data/hora com timezone: {data_hora}")

        # Verificar se médico existe
        medico = db.query(Medico).filter(
            Medico.id == medico_id,
            Medico.cliente_id == cliente_id
        ).first()

        if not medico:
            logger.warning(f"[Agendamento] Médico {medico_id} não encontrado para cliente {cliente_id}")
            return None

        # ========== VERIFICAR DISPONIBILIDADE DO HORÁRIO ==========
        agendamento_service = AgendamentoService(db)
        disponivel = agendamento_service.verificar_disponibilidade_medico(
            medico_id=medico_id,
            data_hora=data_hora,
            duracao_minutos=30
        )

        if not disponivel:
            logger.warning(f"[Agendamento] ❌ Horário INDISPONÍVEL: {data_hora} para médico {medico_id}")
            # Retornar dict com erro para que a IA possa informar o paciente
            return {"erro": "horario_indisponivel", "data_hora": data_hora, "medico_nome": medico.nome}

        logger.info(f"[Agendamento] ✅ Horário disponível: {data_hora} para médico {medico_id}")
        # ==========================================================

        # Buscar ou criar paciente
        telefone_limpo = re.sub(r'[^\d]', '', telefone)
        paciente = db.query(Paciente).filter(
            Paciente.cliente_id == cliente_id,
            Paciente.telefone.like(f"%{telefone_limpo[-8:]}%")
        ).first()

        if not paciente:
            # Criar novo paciente
            paciente = Paciente(
                cliente_id=cliente_id,
                nome=nome,
                telefone=telefone_limpo,
                convenio=convenio if convenio.lower() != "particular" else None
            )
            db.add(paciente)
            db.flush()  # Para obter o ID
            logger.info(f"[Agendamento] Novo paciente criado: {paciente.id} - {nome}")
        else:
            # Atualizar nome se necessário
            if paciente.nome != nome:
                paciente.nome = nome

        # ========== CANCELAR AGENDAMENTOS ANTERIORES (REAGENDAMENTO) ==========
        # Buscar agendamentos futuros do paciente com este médico que ainda não foram realizados
        from datetime import datetime as dt
        import pytz
        tz_brazil = pytz.timezone('America/Sao_Paulo')
        agora = dt.now(tz_brazil)

        agendamentos_anteriores = db.query(Agendamento).filter(
            Agendamento.paciente_id == paciente.id,
            Agendamento.medico_id == medico_id,
            Agendamento.status.in_(['agendado', 'confirmado']),
            Agendamento.data_hora > agora  # Apenas futuros
        ).all()

        if agendamentos_anteriores:
            for ag_anterior in agendamentos_anteriores:
                # IMPORTANTE: Usar "remarcado" (NÃO "cancelado") para manter métricas corretas
                # "remarcado" = paciente mudou data, receita MANTIDA (não é perda)
                # "cancelado" = paciente desistiu, PERDA de receita
                ag_anterior.status = 'remarcado'
                ag_anterior.observacoes = (ag_anterior.observacoes or '') + f' | Remarcado para nova data via WhatsApp em {agora.strftime("%d/%m/%Y %H:%M")}'
                logger.info(f"[Agendamento] 🔄 Remarcação: Marcando como 'remarcado' o agendamento anterior ID={ag_anterior.id} ({ag_anterior.data_hora.strftime('%d/%m/%Y %H:%M')})")

            # Notificar via WebSocket sobre remarcações
            try:
                for ag_anterior in agendamentos_anteriores:
                    await websocket_manager.send_agendamento_atualizado(cliente_id, {
                        "id": ag_anterior.id,
                        "status": "remarcado",
                        "motivo": "Paciente remarcou para nova data"
                    })
            except Exception as ws_error:
                logger.warning(f"[WebSocket] Erro ao notificar remarcação: {ws_error}")
        # ======================================================================

        # Determinar valor e forma de pagamento
        valor = None
        forma_pagamento = 'particular'

        if convenio.lower() == "particular":
            # Buscar valor configurado do médico
            valor = medico.valor_consulta_particular if medico.valor_consulta_particular else 150.00
        else:
            # Buscar índice do convênio no array convenios_aceitos do médico
            convenios = medico.convenios_aceitos or []
            convenio_lower = convenio.lower().strip()
            for i, conv in enumerate(convenios):
                conv_nome = conv.get('nome', '').lower().strip()
                if conv_nome == convenio_lower or convenio_lower in conv_nome or conv_nome in convenio_lower:
                    forma_pagamento = f'convenio_{i}'
                    valor = conv.get('valor')
                    logger.info(f"[Agendamento] Convênio encontrado: {conv.get('nome')} (index={i}, valor={valor})")
                    break
            else:
                # Convênio não encontrado no cadastro, salvar como genérico
                forma_pagamento = 'convenio_0'
                logger.warning(f"[Agendamento] Convênio '{convenio}' não encontrado no cadastro do médico")

        # Criar agendamento (cliente_id é inferido pelo medico/paciente)
        # Indicar se é reagendamento na observação
        is_reagendamento = bool(agendamentos_anteriores)
        observacao_base = "Reagendado" if is_reagendamento else "Agendado"
        observacao = f"{observacao_base} via WhatsApp IA. Convênio: {convenio}"

        agendamento = Agendamento(
            medico_id=medico_id,
            paciente_id=paciente.id,
            data_hora=data_hora,
            status="agendado",
            tipo_atendimento=convenio.lower() if convenio.lower() != "particular" else "particular",
            forma_pagamento=forma_pagamento,
            valor_consulta=str(valor) if valor else None,
            motivo_consulta=motivo_consulta,
            observacoes=observacao
        )
        db.add(agendamento)
        db.commit()
        db.refresh(agendamento)

        logger.info(f"[Agendamento] ✅ Criado: ID={agendamento.id}, Paciente={nome}, Médico={medico.nome}, Data={data_hora}")

        # Notificar via WebSocket para atualizar calendários em tempo real
        try:
            await websocket_manager.send_novo_agendamento(cliente_id, {
                "id": agendamento.id,
                "paciente_nome": nome,
                "medico_id": medico_id,
                "medico_nome": medico.nome,
                "data_hora": data_hora.isoformat(),
                "status": "agendado",
                "tipo_atendimento": agendamento.tipo_atendimento
            })
        except Exception as ws_error:
            logger.warning(f"[WebSocket] Erro ao notificar novo agendamento: {ws_error}")

        return agendamento

    except Exception as e:
        logger.error(f"[Agendamento] Erro ao criar: {e}")
        import traceback
        logger.error(f"[Agendamento] Traceback: {traceback.format_exc()}")
        db.rollback()
        return None


def get_cliente_id_from_phone_number_id(phone_number_id: str, db: Session) -> int:
    """
    Identifica o cliente pelo phone_number_id do WhatsApp.
    Este é o identificador único do número que RECEBEU a mensagem.
    Busca na tabela configuracoes onde o Setup salva os dados de WhatsApp.
    """
    from app.models.configuracao import Configuracao
    from app.models.cliente import Cliente

    if phone_number_id:
        # Busca na tabela configuracoes (onde o Setup salva os dados)
        config = db.query(Configuracao).filter(
            Configuracao.whatsapp_phone_number_id == phone_number_id,
            Configuracao.whatsapp_ativo == True
        ).first()

        if config:
            cliente = db.query(Cliente).filter(Cliente.id == config.cliente_id, Cliente.ativo == True).first()
            if cliente:
                logger.info(f"[Multi-tenant] Cliente {cliente.id} ({cliente.nome}) identificado pelo phone_number_id {phone_number_id}")
                return cliente.id

    # Fallback para cliente padrão
    default_id = int(os.getenv("DEFAULT_CLIENTE_ID", "3"))
    logger.warning(f"[Multi-tenant] phone_number_id '{phone_number_id}' não encontrado, usando cliente padrão {default_id}")
    return default_id


# ==================== ENDPOINTS AUXILIARES ====================

@router.get("/webhook/whatsapp-official/status")
async def get_status():
    """Verifica status da conexão com a API oficial."""

    status = await whatsapp_service.get_connection_status()
    return status


@router.get("/webhook/whatsapp-official/templates")
async def get_templates():
    """Lista templates disponíveis."""

    templates = await whatsapp_service.get_templates()
    return {"templates": templates}


@router.post("/webhook/whatsapp-official/send-test")
async def send_test_message(to: str, message: str):
    """Envia mensagem de teste."""

    result = await whatsapp_service.send_text(to=to, message=message)
    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error
    }


@router.post("/webhook/whatsapp-official/test-template")
async def test_template(to: str):
    """
    Endpoint temporário para testar envio de template hello_world.
    Valida que a infraestrutura de templates está funcionando.
    """

    result = await whatsapp_service.send_template(
        to=to,
        template_name="hello_world",
        language_code="en_US",
        components=None
    )

    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
        "template": "hello_world",
        "raw_response": result.raw_response
    }


@router.post("/webhook/whatsapp-official/test-lembrete-24h")
async def test_lembrete_24h(
    to: str,
    paciente: str = "Marco",
    medico: str = "Dr. João Silva",
    data: str = "27/01/2026",
    horario: str = "14:30"
):
    """
    Testa o template lembrete_24h com variáveis.
    Os botões 'Confirmar presença' e 'Preciso remarcar' são definidos no template.
    """

    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": paciente},
                {"type": "text", "text": medico},
                {"type": "text", "text": data},
                {"type": "text", "text": horario}
            ]
        }
    ]

    result = await whatsapp_service.send_template(
        to=to,
        template_name="lembrete_24h",
        language_code="pt_BR",
        components=components
    )

    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
        "template": "lembrete_24h",
        "variables": {
            "paciente": paciente,
            "medico": medico,
            "data": data,
            "horario": horario
        },
        "raw_response": result.raw_response
    }


@router.post("/webhook/whatsapp-official/test-template-service")
async def test_template_service(
    telefone: str = "5524988493257",
    paciente: str = "Marco",
    medico: str = "Dra. Ana Costa",
    data: str = "28/01/2026",
    hora: str = "10:00"
):
    """
    Testa o WhatsAppTemplateService com enviar_lembrete_24h.
    Valida que a camada de abstração está funcionando.
    """
    from app.services.whatsapp_template_service import get_template_service

    template_service = get_template_service()

    result = await template_service.enviar_lembrete_24h(
        telefone=telefone,
        paciente=paciente,
        medico=medico,
        data=data,
        hora=hora
    )

    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
        "service": "WhatsAppTemplateService",
        "method": "enviar_lembrete_24h",
        "variables": {
            "telefone": telefone,
            "paciente": paciente,
            "medico": medico,
            "data": data,
            "hora": hora
        },
        "raw_response": result.raw_response
    }


@router.post("/webhook/whatsapp-official/test-pagamento")
async def test_pagamento_pendente(
    telefone: str = "5524988493257",
    cliente: str = "Marco",
    valor: str = "199,90",
    vencimento: str = "30/01/2026",
    url_pagamento: str = "https://www.google.com"
):
    """
    Testa o template pagamento_pendente com botão URL dinâmica.
    Valida que a estrutura de botão URL está funcionando.
    """
    from app.services.whatsapp_template_service import get_template_service

    template_service = get_template_service()

    result = await template_service.enviar_pagamento_pendente(
        telefone=telefone,
        cliente=cliente,
        valor=valor,
        vencimento=vencimento,
        url_pagamento=url_pagamento
    )

    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
        "service": "WhatsAppTemplateService",
        "method": "enviar_pagamento_pendente",
        "variables": {
            "telefone": telefone,
            "cliente": cliente,
            "valor": valor,
            "vencimento": vencimento,
            "url_pagamento": url_pagamento
        },
        "raw_response": result.raw_response
    }


@router.post("/webhook/whatsapp-official/test-lembrete-service")
async def test_lembrete_service(
    tipo: str = "24h",
    telefone: str = "5524988493257",
    paciente: str = "Marco Teste",
    medico: str = "Dr. Scheduler",
    data: str = "27/01/2026",
    hora: str = "15:00"
):
    """
    Testa o LembreteService modificado com envio direto via WhatsAppTemplateService.

    Tipos disponíveis: 24h, 2h
    """
    from app.services.whatsapp_template_service import get_template_service

    template_service = get_template_service()

    if tipo == "24h":
        result = await template_service.enviar_lembrete_24h(
            telefone=telefone,
            paciente=paciente,
            medico=medico,
            data=data,
            hora=hora
        )
        template_name = "lembrete_24h"
        variables = {
            "paciente": paciente,
            "medico": medico,
            "data": data,
            "hora": hora
        }
    elif tipo == "2h":
        result = await template_service.enviar_lembrete_2h(
            telefone=telefone,
            paciente=paciente,
            medico=medico,
            hora=hora
        )
        template_name = "lembrete_2h"
        variables = {
            "paciente": paciente,
            "medico": medico,
            "hora": hora
        }
    else:
        return {
            "success": False,
            "error": f"Tipo '{tipo}' não suportado. Use '24h' ou '2h'."
        }

    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
        "service": "LembreteService (via WhatsAppTemplateService)",
        "template": template_name,
        "tipo": tipo,
        "telefone": telefone,
        "variables": variables,
        "raw_response": result.raw_response
    }


@router.post("/webhook/whatsapp-official/test-consulta-confirmada")
async def test_consulta_confirmada(
    to: str = "5524988493257",
    paciente: str = "Marco Teste",
    medico: str = "Dr. Cardoso",
    data: str = "28/01/2026",
    hora: str = "15:00",
    local: str = "Rua das Flores, 123"
):
    """
    Testa o template consulta_confirmada.
    Botões: "Confirmar" e "Cancelar"
    """
    from app.services.whatsapp_template_service import get_template_service

    template_service = get_template_service()
    result = await template_service.enviar_consulta_confirmada(
        telefone=to,
        paciente=paciente,
        medico=medico,
        data=data,
        hora=hora,
        local=local
    )

    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
        "template": "consulta_confirmada",
        "variables": {
            "paciente": paciente,
            "medico": medico,
            "data": data,
            "hora": hora,
            "local": local
        },
        "raw_response": result.raw_response
    }


@router.post("/webhook/whatsapp-official/test-pesquisa-satisfacao")
async def test_pesquisa_satisfacao(
    to: str = "5524988493257",
    paciente: str = "Marco Teste",
    medico: str = "Dr. Cardoso",
    data_consulta: str = "26/01/2026"
):
    """
    Testa o template pesquisa_satisfacao.
    Botões: "1-2", "3", "4-5"
    """
    from app.services.whatsapp_template_service import get_template_service

    template_service = get_template_service()
    result = await template_service.enviar_pesquisa_satisfacao(
        telefone=to,
        paciente=paciente,
        medico=medico,
        data_consulta=data_consulta
    )

    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
        "template": "pesquisa_satisfacao",
        "variables": {
            "paciente": paciente,
            "medico": medico,
            "data_consulta": data_consulta
        },
        "raw_response": result.raw_response
    }