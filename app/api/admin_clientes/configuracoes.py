"""
Endpoints de configurações: WhatsApp config, geral, testar conexão.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.database import get_db
from app.api.admin import get_current_admin
from app.api.admin_clientes.schemas import (
    ConfiguracaoWhatsAppUpdate, ConfiguracaoGeralUpdate, TesteWhatsAppRequest
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/clientes/{cliente_id}/configuracoes")
async def get_configuracoes_cliente(
    cliente_id: int,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Retorna as configuracoes de um cliente"""
    try:
        config = db.execute(
            text("""
                SELECT cliente_id, whatsapp_numero, whatsapp_token, whatsapp_ativo,
                       whatsapp_phone_number_id, whatsapp_business_account_id, whatsapp_display_name,
                       mensagem_boas_vindas, mensagem_despedida, horario_funcionamento,
                       timezone, sistema_ativo
                FROM configuracoes
                WHERE cliente_id = :cliente_id
            """),
            {"cliente_id": cliente_id}
        ).fetchone()

        if not config:
            return {
                "cliente_id": cliente_id,
                "whatsapp_numero": None,
                "whatsapp_token": None,
                "whatsapp_ativo": False,
                "whatsapp_phone_number_id": None,
                "whatsapp_business_account_id": None,
                "whatsapp_display_name": None,
                "mensagem_boas_vindas": None,
                "mensagem_despedida": None,
                "horario_funcionamento": None,
                "timezone": "America/Sao_Paulo",
                "sistema_ativo": False
            }

        return {
            "cliente_id": config[0],
            "whatsapp_numero": config[1],
            "whatsapp_token": config[2],
            "whatsapp_ativo": config[3],
            "whatsapp_phone_number_id": config[4],
            "whatsapp_business_account_id": config[5],
            "whatsapp_display_name": config[6],
            "mensagem_boas_vindas": config[7],
            "mensagem_despedida": config[8],
            "horario_funcionamento": config[9],
            "timezone": config[10],
            "sistema_ativo": config[11]
        }

    except Exception as e:
        logger.error(f"[Setup] Erro ao buscar configuracoes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar configuracoes")


@router.put("/clientes/{cliente_id}/configuracoes/whatsapp")
async def update_configuracoes_whatsapp(
    cliente_id: int,
    dados: ConfiguracaoWhatsAppUpdate,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Atualiza as configuracoes de WhatsApp de um cliente"""
    try:
        # Verificar se cliente existe
        cliente = db.execute(
            text("SELECT id FROM clientes WHERE id = :id"),
            {"id": cliente_id}
        ).fetchone()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")

        # Verificar se ja existe configuracao
        config_existe = db.execute(
            text("SELECT id FROM configuracoes WHERE cliente_id = :cliente_id"),
            {"cliente_id": cliente_id}
        ).fetchone()

        agora = datetime.now()

        if config_existe:
            db.execute(
                text("""
                    UPDATE configuracoes SET
                        whatsapp_phone_number_id = COALESCE(:phone_id, whatsapp_phone_number_id),
                        whatsapp_business_account_id = COALESCE(:waba_id, whatsapp_business_account_id),
                        whatsapp_numero = COALESCE(:numero, whatsapp_numero),
                        whatsapp_display_name = COALESCE(:display_name, whatsapp_display_name),
                        whatsapp_token = COALESCE(:token, whatsapp_token),
                        whatsapp_ativo = COALESCE(:ativo, whatsapp_ativo),
                        atualizado_em = :atualizado_em
                    WHERE cliente_id = :cliente_id
                """),
                {
                    "phone_id": dados.whatsapp_phone_number_id,
                    "waba_id": dados.whatsapp_business_account_id,
                    "numero": dados.whatsapp_numero,
                    "display_name": dados.whatsapp_display_name,
                    "token": dados.whatsapp_token,
                    "ativo": dados.whatsapp_ativo,
                    "atualizado_em": agora,
                    "cliente_id": cliente_id
                }
            )
        else:
            db.execute(
                text("""
                    INSERT INTO configuracoes (
                        cliente_id, whatsapp_phone_number_id, whatsapp_business_account_id,
                        whatsapp_numero, whatsapp_display_name, whatsapp_token, whatsapp_ativo,
                        sistema_ativo, timezone, criado_em, atualizado_em
                    ) VALUES (
                        :cliente_id, :phone_id, :waba_id, :numero, :display_name, :token, :ativo,
                        false, 'America/Sao_Paulo', :criado_em, :atualizado_em
                    )
                """),
                {
                    "cliente_id": cliente_id,
                    "phone_id": dados.whatsapp_phone_number_id,
                    "waba_id": dados.whatsapp_business_account_id,
                    "numero": dados.whatsapp_numero,
                    "display_name": dados.whatsapp_display_name,
                    "token": dados.whatsapp_token,
                    "ativo": dados.whatsapp_ativo or False,
                    "criado_em": agora,
                    "atualizado_em": agora
                }
            )

        db.commit()
        logger.info(f"[Setup] Configuracoes WhatsApp atualizadas para cliente {cliente_id}")

        return {"success": True, "message": "Configuracoes do WhatsApp atualizadas com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Setup] Erro ao atualizar WhatsApp: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao atualizar configuracoes")


@router.put("/clientes/{cliente_id}/configuracoes")
async def update_configuracoes_gerais(
    cliente_id: int,
    dados: ConfiguracaoGeralUpdate,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Atualiza as configuracoes gerais de um cliente"""
    try:
        # Verificar se cliente existe
        cliente = db.execute(
            text("SELECT id FROM clientes WHERE id = :id"),
            {"id": cliente_id}
        ).fetchone()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")

        # Verificar se ja existe configuracao
        config_existe = db.execute(
            text("SELECT id FROM configuracoes WHERE cliente_id = :cliente_id"),
            {"cliente_id": cliente_id}
        ).fetchone()

        agora = datetime.now()
        import json

        if config_existe:
            db.execute(
                text("""
                    UPDATE configuracoes SET
                        horario_funcionamento = COALESCE(:horario::json, horario_funcionamento),
                        mensagem_boas_vindas = COALESCE(:msg_boas_vindas, mensagem_boas_vindas),
                        mensagem_despedida = COALESCE(:msg_despedida, mensagem_despedida),
                        timezone = COALESCE(:timezone, timezone),
                        sistema_ativo = COALESCE(:sistema_ativo, sistema_ativo),
                        atualizado_em = :atualizado_em
                    WHERE cliente_id = :cliente_id
                """),
                {
                    "horario": json.dumps(dados.horario_funcionamento) if dados.horario_funcionamento else None,
                    "msg_boas_vindas": dados.mensagem_boas_vindas,
                    "msg_despedida": dados.mensagem_despedida,
                    "timezone": dados.timezone,
                    "sistema_ativo": dados.sistema_ativo,
                    "atualizado_em": agora,
                    "cliente_id": cliente_id
                }
            )
        else:
            db.execute(
                text("""
                    INSERT INTO configuracoes (
                        cliente_id, horario_funcionamento, mensagem_boas_vindas, mensagem_despedida,
                        timezone, sistema_ativo, whatsapp_ativo, criado_em, atualizado_em
                    ) VALUES (
                        :cliente_id, :horario::json, :msg_boas_vindas, :msg_despedida,
                        :timezone, :sistema_ativo, false, :criado_em, :atualizado_em
                    )
                """),
                {
                    "cliente_id": cliente_id,
                    "horario": json.dumps(dados.horario_funcionamento) if dados.horario_funcionamento else None,
                    "msg_boas_vindas": dados.mensagem_boas_vindas,
                    "msg_despedida": dados.mensagem_despedida,
                    "timezone": dados.timezone or "America/Sao_Paulo",
                    "sistema_ativo": dados.sistema_ativo or False,
                    "criado_em": agora,
                    "atualizado_em": agora
                }
            )

        db.commit()
        logger.info(f"[Setup] Configuracoes gerais atualizadas para cliente {cliente_id}")

        return {"success": True, "message": "Configuracoes atualizadas com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Setup] Erro ao atualizar configuracoes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao atualizar configuracoes")


@router.post("/clientes/{cliente_id}/whatsapp/testar")
async def testar_conexao_whatsapp(
    cliente_id: int,
    dados: TesteWhatsAppRequest,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Testa a conexao com a API oficial do WhatsApp"""
    import httpx

    try:
        # Verificar se cliente existe
        cliente = db.execute(
            text("SELECT id, nome FROM clientes WHERE id = :id"),
            {"id": cliente_id}
        ).fetchone()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")

        # Fazer requisicao para a API do Meta para verificar o phone_number_id
        api_version = "v21.0"
        url = f"https://graph.facebook.com/{api_version}/{dados.phone_number_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {dados.access_token}"},
                timeout=10.0
            )

        if response.status_code == 200:
            data = response.json()
            phone_number = data.get("display_phone_number", data.get("verified_name", "N/A"))
            logger.info(f"[Setup] Teste WhatsApp OK para cliente {cliente_id}: {phone_number}")
            return {
                "success": True,
                "message": "Conexao estabelecida com sucesso",
                "phone_number": phone_number,
                "verified_name": data.get("verified_name"),
                "quality_rating": data.get("quality_rating")
            }
        else:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "Erro desconhecido")
            logger.warning(f"[Setup] Teste WhatsApp falhou para cliente {cliente_id}: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Erro na API do Meta: {error_msg}")

    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Timeout ao conectar com a API do Meta")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Setup] Erro ao testar WhatsApp: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao testar conexao")
