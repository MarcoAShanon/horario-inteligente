"""
AI processing with Anthropic Claude: process_with_anthropic_ai
"""
import logging
from datetime import datetime
from sqlalchemy import text

from app.database import SessionLocal
from app.services.anthropic_service import AnthropicService
from app.services.conversation_manager import conversation_manager
from app.services.calendario_service import CalendarioService
from app.services.notification_service import get_notification_service
from app.services.urgencia_service import get_urgencia_service
from app.services.conversa_service import ConversaService

from app.api.webhooks.messaging import formatar_para_whatsapp, get_fallback_response

logger = logging.getLogger(__name__)


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

        # Extrair informações de urgência
        urgencia_data = resultado.get("urgencia", {"nivel": "normal", "motivo": None})
        urgencia_nivel = urgencia_data.get("nivel", "normal")
        urgencia_motivo = urgencia_data.get("motivo")

        logger.info(f"🔍 Resposta extraída: '{resposta[:100]}...'")
        logger.info(f"🎯 Intenção detectada: {intencao}")
        logger.info(f"🔄 Próxima ação: {proxima_acao}")
        logger.info(f"📋 Dados coletados: {dados_coletados}")
        logger.info(f"🚨 Urgência: nivel={urgencia_nivel}, motivo={urgencia_motivo}")

        # ========== PROCESSAR URGÊNCIA ==========
        if urgencia_nivel in ["atencao", "critica"]:
            try:
                logger.warning(f"🚨 URGÊNCIA DETECTADA: {urgencia_nivel} - {urgencia_motivo}")

                # Obter ou criar conversa para registrar urgência
                conversa, _ = ConversaService.criar_ou_recuperar_conversa(
                    db=db,
                    cliente_id=cliente_id,
                    telefone=sender,
                    nome_paciente=push_name
                )

                if conversa:
                    # Processar urgência
                    urgencia_service = get_urgencia_service(db)
                    urgencia_result = await urgencia_service.processar_urgencia(
                        conversa_id=conversa.id,
                        cliente_id=cliente_id,
                        nivel=urgencia_nivel,
                        motivo=urgencia_motivo,
                        mensagem_paciente=message_text,
                        paciente_telefone=sender,
                        paciente_nome=push_name
                    )

                    logger.info(f"🚨 Resultado urgência: {urgencia_result}")

                    # Se for crítica, substituir resposta pela resposta de emergência
                    if urgencia_nivel == "critica" and urgencia_result.get("resposta_emergencia"):
                        resposta = urgencia_result["resposta_emergencia"]
                        logger.info("🚨 Resposta substituída por mensagem de emergência")

            except Exception as urgencia_error:
                logger.error(f"❌ Erro ao processar urgência (não bloqueante): {urgencia_error}")
                # Não falhar o fluxo por erro na urgência
        # ==========================================

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

                # Notificar médico sobre novo agendamento (Push + WhatsApp/Email se configurado)
                try:
                    notification_service = get_notification_service(db)
                    await notification_service.notificar_medico(
                        medico_id=medico_id,
                        cliente_id=cliente_id,
                        evento="novo",
                        dados_agendamento={
                            "paciente_nome": nome_paciente,
                            "data_hora": data_hora
                        }
                    )
                    logger.info(f"📱 Notificação enviada para médico {medico_id}")
                except Exception as notif_error:
                    logger.warning(f"⚠️ Erro ao notificar médico: {notif_error}")

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
