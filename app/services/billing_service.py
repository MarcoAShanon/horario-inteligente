"""
Servico de Billing Automatizado
Orquestra criacao de clientes, assinaturas e cobrancas no ASAAS
apos ativacao da conta pelo cliente.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.asaas_service import AsaasService
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class BillingService:
    """
    Orquestra o fluxo de billing automatizado:
    1. Garante que o cliente exista no ASAAS
    2. Cria assinatura recorrente no ASAAS
    3. Cobra taxa de ativacao
    """

    def __init__(self):
        self.asaas = AsaasService()

    async def ensure_asaas_customer(self, db: Session, cliente_id: int) -> Optional[str]:
        """
        Garante que o cliente tenha cadastro no ASAAS.
        Se ja tiver asaas_customer_id, retorna o existente.
        Caso contrario, cria no ASAAS e salva no banco.

        Returns:
            asaas_customer_id ou None em caso de erro
        """
        result = db.execute(
            text("""
                SELECT id, nome, email, telefone, cnpj, asaas_customer_id
                FROM clientes WHERE id = :id
            """),
            {"id": cliente_id}
        ).fetchone()

        if not result:
            logger.error(f"[Billing] Cliente {cliente_id} nao encontrado")
            return None

        _id, nome, email, telefone, cnpj, asaas_customer_id = result

        # Ja tem cadastro no ASAAS
        if asaas_customer_id:
            logger.info(f"[Billing] Cliente {cliente_id} ja possui ASAAS ID: {asaas_customer_id}")
            return asaas_customer_id

        # CPF/CNPJ obrigatorio para ASAAS
        if not cnpj:
            logger.error(f"[Billing] Cliente {cliente_id} sem CPF/CNPJ — nao pode criar no ASAAS")
            return None

        # Criar no ASAAS
        response = await self.asaas.criar_cliente(
            nome=nome,
            email=email,
            cpf_cnpj=cnpj,
            telefone=telefone
        )

        if not response.get("success"):
            logger.error(f"[Billing] Erro ao criar cliente {cliente_id} no ASAAS: {response.get('error')}")
            return None

        new_asaas_id = response["data"]["id"]

        db.execute(
            text("UPDATE clientes SET asaas_customer_id = :asaas_id WHERE id = :id"),
            {"asaas_id": new_asaas_id, "id": cliente_id}
        )
        db.commit()

        logger.info(f"[Billing] Cliente ASAAS criado: {new_asaas_id} para cliente interno {cliente_id}")
        return new_asaas_id

    async def create_asaas_subscription(
        self,
        db: Session,
        cliente_id: int,
        asaas_customer_id: str
    ) -> Optional[str]:
        """
        Cria assinatura recorrente no ASAAS a partir da assinatura local.

        Returns:
            asaas_subscription_id ou None em caso de erro
        """
        # Buscar assinatura local ativa/pendente
        assinatura = db.execute(
            text("""
                SELECT
                    a.id, a.valor_mensal, a.periodo_cobranca,
                    a.dia_vencimento, a.asaas_subscription_id,
                    p.nome as plano_nome
                FROM assinaturas a
                JOIN planos p ON p.id = a.plano_id
                WHERE a.cliente_id = :cliente_id
                AND a.status IN ('ativa', 'pendente')
                ORDER BY a.criado_em DESC
                LIMIT 1
            """),
            {"cliente_id": cliente_id}
        ).fetchone()

        if not assinatura:
            logger.warning(f"[Billing] Nenhuma assinatura ativa/pendente para cliente {cliente_id}")
            return None

        assinatura_id, valor_mensal, periodo_cobranca, dia_vencimento, asaas_sub_id, plano_nome = assinatura

        # Ja vinculada ao ASAAS
        if asaas_sub_id:
            logger.info(f"[Billing] Assinatura {assinatura_id} ja vinculada ao ASAAS: {asaas_sub_id}")
            return asaas_sub_id

        # Mapear ciclo interno para ASAAS
        ciclo = self.asaas.mapear_ciclo_assinatura(periodo_cobranca or "mensal")

        # Multiplicar valor mensal pelo número de meses do ciclo
        # ASAAS cobra o valor informado por ciclo (não por mês)
        multiplicador_periodo = {"mensal": 1, "trimestral": 3, "semestral": 6, "anual": 12}
        valor_ciclo = float(valor_mensal) * multiplicador_periodo.get(periodo_cobranca or "mensal", 1)

        # Calcular data da proxima cobranca
        hoje = date.today()
        dia = dia_vencimento or 10
        if hoje.day <= dia:
            proxima_cobranca = hoje.replace(day=dia)
        else:
            # Proximo mes
            if hoje.month == 12:
                proxima_cobranca = hoje.replace(year=hoje.year + 1, month=1, day=dia)
            else:
                proxima_cobranca = hoje.replace(month=hoje.month + 1, day=dia)

        descricao = f"Assinatura {plano_nome} - Horario Inteligente"

        response = await self.asaas.criar_assinatura(
            customer_id=asaas_customer_id,
            valor=valor_ciclo,
            ciclo=ciclo,
            descricao=descricao,
            forma_pagamento="UNDEFINED",
            data_proxima_cobranca=proxima_cobranca
        )

        if not response.get("success"):
            logger.error(f"[Billing] Erro ao criar assinatura ASAAS para cliente {cliente_id}: {response.get('error')}")
            return None

        new_sub_id = response["data"]["id"]

        # Atualizar assinatura local com ID ASAAS e status ativa
        db.execute(
            text("""
                UPDATE assinaturas
                SET asaas_subscription_id = :asaas_id,
                    status = 'ativa',
                    atualizado_em = NOW()
                WHERE id = :id
            """),
            {"asaas_id": new_sub_id, "id": assinatura_id}
        )
        db.commit()

        logger.info(f"[Billing] Assinatura ASAAS criada: {new_sub_id} (assinatura local {assinatura_id})")
        return new_sub_id

    async def charge_activation_fee(
        self,
        db: Session,
        cliente_id: int,
        asaas_customer_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Cria cobranca da taxa de ativacao no ASAAS.

        Returns:
            Dict com dados da cobranca ou None em caso de erro
        """
        # Buscar assinatura e taxa
        result = db.execute(
            text("""
                SELECT a.id, a.taxa_ativacao, a.taxa_ativacao_paga,
                       a.desconto_ativacao_percentual, a.ativacao_cortesia
                FROM assinaturas a
                WHERE a.cliente_id = :cliente_id
                AND a.status IN ('ativa', 'pendente')
                ORDER BY a.criado_em DESC
                LIMIT 1
            """),
            {"cliente_id": cliente_id}
        ).fetchone()

        if not result:
            logger.warning(f"[Billing] Nenhuma assinatura para cobrar taxa de ativacao — cliente {cliente_id}")
            return None

        assinatura_id, taxa_ativacao, taxa_paga, desconto_pct, ativacao_cortesia = result

        if taxa_paga:
            logger.info(f"[Billing] Taxa de ativacao ja paga para cliente {cliente_id}")
            return {"already_paid": True}

        # Calcular valor com desconto
        taxa = float(taxa_ativacao or 150)
        desconto = float(desconto_pct or 0)
        taxa_final = taxa * (1 - desconto / 100)

        if ativacao_cortesia or taxa_final <= 0:
            # Taxa isenta por cortesia ou desconto 100% — marcar como paga sem cobrar
            db.execute(
                text("UPDATE assinaturas SET taxa_ativacao_paga = true WHERE id = :id"),
                {"id": assinatura_id}
            )
            db.commit()
            logger.info(f"[Billing] Taxa de ativacao isenta para cliente {cliente_id} (cortesia={ativacao_cortesia}, desconto={desconto}%)")
            return {"already_paid": True, "waived": True, "cortesia": bool(ativacao_cortesia)}

        response = await self.asaas.criar_cobranca(
            customer_id=asaas_customer_id,
            valor=taxa_final,
            vencimento=date.today(),
            descricao="Taxa de Ativacao - Horario Inteligente",
            forma_pagamento="UNDEFINED"
        )

        if not response.get("success"):
            logger.error(f"[Billing] Erro ao cobrar taxa de ativacao para cliente {cliente_id}: {response.get('error')}")
            return None

        payment_data = response["data"]

        # Buscar PIX copia-cola
        pix_copia_cola = None
        try:
            pix_response = await self.asaas.obter_qrcode_pix(payment_data["id"])
            if pix_response.get("success"):
                pix_copia_cola = pix_response["data"].get("payload")
        except Exception as e:
            logger.warning(f"[Billing] Erro ao obter PIX QR code: {e}")

        # Salvar pagamento no banco
        db.execute(
            text("""
                INSERT INTO pagamentos (
                    cliente_id, assinatura_id, asaas_payment_id, asaas_invoice_url,
                    valor, data_vencimento, forma_pagamento, status, descricao, tipo,
                    link_boleto, pix_copia_cola
                ) VALUES (
                    :cliente_id, :assinatura_id, :asaas_payment_id, :invoice_url,
                    :valor, :data_vencimento, 'UNDEFINED', :status, :descricao, 'ATIVACAO',
                    :link_boleto, :pix_copia_cola
                )
            """),
            {
                "cliente_id": cliente_id,
                "assinatura_id": assinatura_id,
                "asaas_payment_id": payment_data["id"],
                "invoice_url": payment_data.get("invoiceUrl"),
                "valor": taxa_final,
                "data_vencimento": date.today(),
                "status": payment_data.get("status", "PENDING"),
                "descricao": "Taxa de Ativacao - Horario Inteligente",
                "link_boleto": payment_data.get("bankSlipUrl"),
                "pix_copia_cola": pix_copia_cola
            }
        )
        db.commit()

        logger.info(f"[Billing] Taxa de ativacao R${taxa_final:.2f} cobrada para cliente {cliente_id} — ASAAS {payment_data['id']}")

        return {
            "asaas_payment_id": payment_data["id"],
            "valor": taxa_final,
            "invoice_url": payment_data.get("invoiceUrl"),
            "pix_copia_cola": pix_copia_cola,
            "bank_slip_url": payment_data.get("bankSlipUrl")
        }

    async def process_onboarding_billing(self, db: Session, cliente_id: int) -> Dict[str, Any]:
        """
        Orquestra todo o fluxo de billing pos-ativacao:
        1. Cria/garante cliente no ASAAS
        2. Cria assinatura recorrente no ASAAS
        3. Cobra taxa de ativacao

        Chamado apos o cliente aceitar os termos e ativar a conta.

        Returns:
            Dict com resultado de cada etapa
        """
        resultado = {
            "success": False,
            "asaas_customer_id": None,
            "asaas_subscription_id": None,
            "activation_fee": None,
            "errors": []
        }

        # 1. Garantir cliente no ASAAS
        try:
            asaas_customer_id = await self.ensure_asaas_customer(db, cliente_id)
            if not asaas_customer_id:
                resultado["errors"].append("Falha ao criar/buscar cliente no ASAAS")
                logger.error(f"[Billing Onboarding] Falha no step 1 (customer) para cliente {cliente_id}")
                return resultado
            resultado["asaas_customer_id"] = asaas_customer_id
        except Exception as e:
            resultado["errors"].append(f"Erro ao criar cliente ASAAS: {str(e)}")
            logger.error(f"[Billing Onboarding] Excecao no step 1: {e}")
            return resultado

        # 2. Criar assinatura recorrente
        try:
            asaas_subscription_id = await self.create_asaas_subscription(db, cliente_id, asaas_customer_id)
            if asaas_subscription_id:
                resultado["asaas_subscription_id"] = asaas_subscription_id
            else:
                resultado["errors"].append("Falha ao criar assinatura no ASAAS")
                logger.warning(f"[Billing Onboarding] Falha no step 2 (subscription) para cliente {cliente_id}")
        except Exception as e:
            resultado["errors"].append(f"Erro ao criar assinatura ASAAS: {str(e)}")
            logger.error(f"[Billing Onboarding] Excecao no step 2: {e}")

        # 3. Cobrar taxa de ativacao
        try:
            fee_result = await self.charge_activation_fee(db, cliente_id, asaas_customer_id)
            if fee_result:
                resultado["activation_fee"] = fee_result
            else:
                resultado["errors"].append("Falha ao cobrar taxa de ativacao")
                logger.warning(f"[Billing Onboarding] Falha no step 3 (activation fee) para cliente {cliente_id}")
        except Exception as e:
            resultado["errors"].append(f"Erro ao cobrar taxa de ativacao: {str(e)}")
            logger.error(f"[Billing Onboarding] Excecao no step 3: {e}")

        resultado["success"] = len(resultado["errors"]) == 0

        if resultado["success"]:
            logger.info(f"[Billing Onboarding] Fluxo completo para cliente {cliente_id}")
        else:
            logger.warning(f"[Billing Onboarding] Fluxo parcial para cliente {cliente_id}: {resultado['errors']}")

        return resultado

    async def sync_subscription_status(self, db: Session, assinatura_id: int) -> Optional[str]:
        """
        Sincroniza o status de uma assinatura com o ASAAS.

        Returns:
            Status atualizado ou None
        """
        result = db.execute(
            text("SELECT asaas_subscription_id FROM assinaturas WHERE id = :id"),
            {"id": assinatura_id}
        ).fetchone()

        if not result or not result[0]:
            return None

        asaas_sub_id = result[0]

        response = await self.asaas.buscar_assinatura(asaas_sub_id)
        if not response.get("success"):
            logger.error(f"[Billing Sync] Erro ao buscar assinatura {asaas_sub_id}: {response.get('error')}")
            return None

        asaas_status = response["data"].get("status", "ACTIVE")

        # Mapear status ASAAS para interno
        status_map = {
            "ACTIVE": "ativa",
            "INACTIVE": "cancelada",
            "EXPIRED": "cancelada",
        }
        status_interno = status_map.get(asaas_status, "ativa")

        db.execute(
            text("UPDATE assinaturas SET status = :status, atualizado_em = NOW() WHERE id = :id"),
            {"status": status_interno, "id": assinatura_id}
        )
        db.commit()

        return status_interno

    async def check_expired_discounts(self, db: Session) -> int:
        """
        Verifica descontos promocionais expirados e atualiza valores.

        Returns:
            Numero de assinaturas atualizadas
        """
        # Buscar assinaturas com desconto expirado
        result = db.execute(
            text("""
                SELECT a.id, a.valor_original, a.percentual_periodo,
                       a.desconto_percentual, a.desconto_valor_fixo
                FROM assinaturas a
                WHERE a.status = 'ativa'
                AND a.data_fim_desconto IS NOT NULL
                AND a.data_fim_desconto <= CURRENT_DATE
                AND (a.desconto_percentual > 0 OR a.desconto_valor_fixo > 0)
            """)
        ).fetchall()

        count = 0
        for row in result:
            assinatura_id = row[0]
            valor_original = float(row[1] or 0)
            percentual_periodo = float(row[2] or 0)

            # Recalcular: valor_original com desconto de periodo mas SEM desconto promocional
            novo_valor = valor_original * (1 - percentual_periodo / 100)

            db.execute(
                text("""
                    UPDATE assinaturas
                    SET valor_mensal = :valor,
                        valor_com_desconto = :valor,
                        desconto_percentual = 0,
                        desconto_valor_fixo = 0,
                        data_fim_desconto = NULL,
                        atualizado_em = NOW()
                    WHERE id = :id
                """),
                {"valor": novo_valor, "id": assinatura_id}
            )

            # Atualizar no ASAAS se vinculado
            asaas_sub = db.execute(
                text("SELECT asaas_subscription_id FROM assinaturas WHERE id = :id"),
                {"id": assinatura_id}
            ).fetchone()

            if asaas_sub and asaas_sub[0]:
                try:
                    await self.asaas.atualizar_assinatura(asaas_sub[0], {"value": novo_valor})
                    logger.info(f"[Billing] Assinatura ASAAS {asaas_sub[0]} atualizada para R${novo_valor:.2f}")
                except Exception as e:
                    logger.error(f"[Billing] Erro ao atualizar assinatura ASAAS {asaas_sub[0]}: {e}")

            count += 1
            logger.info(f"[Billing] Desconto expirado removido da assinatura {assinatura_id}: novo valor R${novo_valor:.2f}")

        if count > 0:
            db.commit()

        return count


# Instancia global
billing_service = BillingService()
