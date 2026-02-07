import logging
import pytz
from sqlalchemy.orm import Session

from app.services.whatsapp_official_service import WhatsAppOfficialService
from app.services.whatsapp_interface import WhatsAppMessage
from app.services.anthropic_service import AnthropicService
from app.services.conversation_manager import ConversationManager

# Imports para persistência de conversas no PostgreSQL
from app.services.conversa_service import ConversaService
from app.models.conversa import StatusConversa
from app.models.mensagem import DirecaoMensagem, RemetenteMensagem, TipoMensagem
from app.models.agendamento import Agendamento

# Import para notificações WebSocket em tempo real
from app.services.websocket_manager import websocket_manager

# Imports para lembretes inteligentes
from app.services.lembrete_service import lembrete_service

# Imports para tratamento de botões interativos
from app.services.button_handler_service import get_button_handler

# Imports para agendamentos
from app.services.agendamento_service import AgendamentoService

# Imports dos módulos irmãos
from app.services.webhook.tenant_resolver import get_cliente_id_from_phone_number_id
from app.services.webhook.audio_handler import transcribe_incoming_audio, handle_audio_response
from app.services.webhook.agendamento_ia import criar_agendamento_from_ia

logger = logging.getLogger(__name__)

# Timezone Brasil
TZ_BRAZIL = pytz.timezone('America/Sao_Paulo')

# Singletons
whatsapp_service = WhatsAppOfficialService()
conversation_manager = ConversationManager()


def converter_para_brasil(dt):
    """Converte datetime UTC para horário de Brasília."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(TZ_BRAZIL).isoformat()


async def process_message(message: WhatsAppMessage, db: Session):
    """
    Processa mensagem recebida usando IA.
    Persiste conversas no PostgreSQL e mantém contexto no Redis.

    Args:
        message: Mensagem do WhatsApp
        db: Sessão do banco de dados
    """

    try:
        # 1. Determina o cliente_id (tenant) baseado no phone_number_id
        cliente_id = get_cliente_id_from_phone_number_id(message.phone_number_id, db)

        if cliente_id is None:
            logger.error(
                f"[Webhook Official] MENSAGEM IGNORADA: phone_number_id '{message.phone_number_id}' "
                f"não pertence a nenhum cliente. Remetente: {message.sender}. "
                f"Verifique a configuração do WhatsApp no painel admin."
            )
            return

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
        mensagem_foi_audio = await transcribe_incoming_audio(message, whatsapp_service)

        tipo_mensagem = TipoMensagem.AUDIO if mensagem_foi_audio else (
            TipoMensagem.IMAGEM if message.message_type == "image" else (
            TipoMensagem.DOCUMENTO if message.message_type == "document" else TipoMensagem.TEXTO
        ))

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

        # 11.2 Envia resposta pelo WhatsApp
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

        # 11.3 Verificar preferência de áudio e enviar resposta TTS
        await handle_audio_response(
            db, conversa.id, cliente_id, message, texto_resposta,
            mensagem_foi_audio, whatsapp_service
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
