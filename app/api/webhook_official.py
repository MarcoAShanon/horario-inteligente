"""
Webhook para WhatsApp Business API Oficial (Meta Cloud API)
Endpoint separado para facilitar migração gradual
"""

import os
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.whatsapp_official_service import WhatsAppOfficialService
from app.services.whatsapp_interface import WhatsAppMessage
from app.services.anthropic_service import AnthropicService
from app.services.conversation_manager import ConversationManager

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
    """

    from app.database import SessionLocal

    db = SessionLocal()

    try:
        # Determina o cliente_id
        # Na API oficial, podemos usar um cliente padrão ou buscar pelo número
        cliente_id = get_cliente_id_from_phone(message.sender, db)

        # Obtém contexto da conversa
        contexto = conversation_manager.get_context(
            phone=message.sender,
            limite=10,
            cliente_id=cliente_id
        )

        # Se for resposta de botão/lista, usa o ID como texto
        texto_para_processar = message.text
        if message.button_reply_id:
            texto_para_processar = message.button_reply_id
        elif message.list_reply_id:
            texto_para_processar = message.list_reply_id

        # Processa com IA
        anthropic_service = AnthropicService(db, cliente_id)
        resposta = anthropic_service.processar_mensagem(
            mensagem=texto_para_processar,
            telefone=message.sender,
            contexto_conversa=contexto
        )

        # Salva contexto
        conversation_manager.add_message(
            phone=message.sender,
            tipo="user",
            texto=message.text,
            intencao="",
            dados={},
            cliente_id=cliente_id
        )

        conversation_manager.add_message(
            phone=message.sender,
            tipo="assistant",
            texto=resposta.get("resposta", ""),
            intencao=resposta.get("intencao", ""),
            dados=resposta.get("dados_coletados", {}),
            cliente_id=cliente_id
        )

        # Envia resposta
        texto_resposta = resposta.get("resposta", "Desculpe, não entendi.")

        # Verifica se deve enviar com botões
        proxima_acao = resposta.get("proxima_acao", "")

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
        print(f"[Webhook Official] Erro ao processar: {e}")

        # Envia mensagem de erro amigável
        await whatsapp_service.send_text(
            to=message.sender,
            message="Desculpe, estou com dificuldades técnicas no momento. Por favor, tente novamente em alguns instantes."
        )

    finally:
        db.close()


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
