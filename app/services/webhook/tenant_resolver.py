import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.configuracao import Configuracao
from app.models.cliente import Cliente

logger = logging.getLogger(__name__)


def get_cliente_id_from_phone_number_id(phone_number_id: str, db: Session) -> Optional[int]:
    """
    Identifica o cliente pelo phone_number_id do WhatsApp.
    Este é o identificador único do número que RECEBEU a mensagem.
    Busca na tabela configuracoes e depois na tabela clientes.
    Retorna None se não encontrar — NUNCA faz fallback para outro tenant.
    """
    if not phone_number_id:
        logger.error("[Multi-tenant] phone_number_id vazio recebido no webhook")
        return None

    # Filtro de cliente ativo: aceita ativo=True OU status='ativo' (evita inconsistências)
    filtro_ativo = or_(Cliente.ativo == True, Cliente.status == 'ativo')

    # 1. Busca na tabela configuracoes (onde o Setup salva os dados)
    config = db.query(Configuracao).filter(
        Configuracao.whatsapp_phone_number_id == phone_number_id,
        Configuracao.whatsapp_ativo == True
    ).first()

    if config:
        cliente = db.query(Cliente).filter(Cliente.id == config.cliente_id, filtro_ativo).first()
        if cliente:
            logger.info(f"[Multi-tenant] Cliente {cliente.id} ({cliente.nome}) identificado via configuracoes pelo phone_number_id {phone_number_id}")
            return cliente.id

    # 2. Fallback: busca direto na tabela clientes (campo whatsapp_phone_number_id)
    cliente = db.query(Cliente).filter(
        Cliente.whatsapp_phone_number_id == phone_number_id,
        filtro_ativo
    ).first()

    if cliente:
        logger.info(f"[Multi-tenant] Cliente {cliente.id} ({cliente.nome}) identificado via tabela clientes pelo phone_number_id {phone_number_id}")
        return cliente.id

    # 3. NÃO encontrou — retorna None (sem fallback para demo)
    logger.error(f"[Multi-tenant] FALHA: phone_number_id '{phone_number_id}' não pertence a nenhum cliente ativo. Mensagem será ignorada.")
    return None
