"""
Webhook para WhatsApp Business API Oficial (Meta Cloud API)
Endpoint separado para facilitar migração gradual
"""

import os
import logging
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse
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
from app.models.agendamento import Agendamento
from app.models.paciente import Paciente
from app.models.medico import Medico

logger = logging.getLogger(__name__)

router = APIRouter()

# Instância do serviço
whatsapp_service = WhatsAppOfficialService()
conversation_manager = ConversationManager()


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
            print(f"[Webhook Official] Verificação bem-sucedida!")
            return PlainTextResponse(content=result)
        else:
            print(f"[Webhook Official] Token inválido: {hub_token}")
            raise HTTPException(status_code=403, detail="Token de verificação inválido")

    raise HTTPException(status_code=400, detail="Parâmetros de verificação ausentes")


@router.post("/webhook/whatsapp-official")
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
        # 1. Determina o cliente_id (tenant)
        cliente_id = get_cliente_id_from_phone(message.sender, db)

        # 2. Criar ou recuperar conversa no PostgreSQL
        conversa = ConversaService.criar_ou_recuperar_conversa(
            db=db,
            cliente_id=cliente_id,
            telefone=message.sender
        )
        logger.info(f"[Webhook Official] Conversa {conversa.id} - Status: {conversa.status.value}")

        # 3. Determinar tipo da mensagem
        tipo_mensagem = TipoMensagem.TEXTO
        if message.message_type == "audio":
            tipo_mensagem = TipoMensagem.AUDIO
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
                "timestamp": mensagem_paciente.timestamp.isoformat()
            }
        )

        # 5. Verificar se IA está ativa para esta conversa
        if conversa.status == StatusConversa.HUMANO_ASSUMIU:
            logger.info(f"[Webhook Official] Conversa {conversa.id} está sendo atendida por humano. IA não responderá.")
            # Mensagem já foi notificada acima, atendente verá no painel
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
                "timestamp": mensagem_ia.timestamp.isoformat()
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

        # 11.1 Se a IA sinalizou que deve agendar, criar o agendamento
        if proxima_acao == "agendar":
            agendamento_criado = await criar_agendamento_from_ia(
                db=db,
                cliente_id=cliente_id,
                telefone=message.sender,
                dados_coletados=dados_coletados
            )
            if agendamento_criado:
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
                buttons=buttons
            )
        else:
            # Envia texto simples
            await whatsapp_service.send_text(
                to=message.sender,
                message=texto_resposta
            )

    except Exception as e:
        import traceback
        logger.error(f"[Webhook Official] Erro ao processar: {e}")
        logger.error(f"[Webhook Official] Traceback: {traceback.format_exc()}")

        # Envia mensagem de erro amigável
        await whatsapp_service.send_text(
            to=message.sender,
            message="Desculpe, estou com dificuldades técnicas no momento. Por favor, tente novamente em alguns instantes."
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
        especialidade = dados_coletados.get("especialidade", "")

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

        # Verificar se médico existe
        medico = db.query(Medico).filter(
            Medico.id == medico_id,
            Medico.cliente_id == cliente_id
        ).first()

        if not medico:
            logger.warning(f"[Agendamento] Médico {medico_id} não encontrado para cliente {cliente_id}")
            return None

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

        # Determinar valor (particular = R$ 300)
        valor = 300.00 if convenio.lower() == "particular" else None

        # Criar agendamento
        agendamento = Agendamento(
            cliente_id=cliente_id,
            medico_id=medico_id,
            paciente_id=paciente.id,
            data_hora=data_hora,
            status="agendado",
            tipo_atendimento="consulta",
            valor_consulta=valor,
            motivo_consulta=especialidade,
            observacoes=f"Agendado via WhatsApp IA. Convênio: {convenio}"
        )
        db.add(agendamento)
        db.commit()
        db.refresh(agendamento)

        logger.info(f"[Agendamento] ✅ Criado: ID={agendamento.id}, Paciente={nome}, Médico={medico.nome}, Data={data_hora}")
        return agendamento

    except Exception as e:
        logger.error(f"[Agendamento] Erro ao criar: {e}")
        import traceback
        logger.error(f"[Agendamento] Traceback: {traceback.format_exc()}")
        db.rollback()
        return None


def get_cliente_id_from_phone(phone: str, db: Session) -> int:
    """
    Determina o cliente_id baseado no número.
    Por enquanto retorna cliente padrão (demo).

    TODO: Implementar lógica de roteamento quando houver múltiplos clientes.
    """

    # Cliente demo por padrão
    return int(os.getenv("DEFAULT_CLIENTE_ID", "3"))


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
