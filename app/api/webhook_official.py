"""
Webhook para WhatsApp Business API Oficial (Meta Cloud API)
Endpoint separado para facilitar migração gradual
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.services.whatsapp_official_service import WhatsAppOfficialService
from app.services.webhook.message_processor import process_message

logger = logging.getLogger(__name__)

# Rate Limiter para webhooks
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# Instância do serviço (para endpoints de teste)
whatsapp_service = WhatsAppOfficialService()


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
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
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
        await process_message(message, db)

        return {"status": "processed"}

    except Exception as e:
        print(f"[Webhook Official] Erro: {e}")
        # Sempre retorna 200 para a Meta não reenviar
        return {"status": "error", "message": str(e)}


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
