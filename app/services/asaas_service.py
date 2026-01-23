"""
Serviço de integração com ASAAS Payment Gateway
Desenvolvido para gerenciar cobranças e assinaturas do SaaS Horário Inteligente
"""

import os
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import date, datetime

logger = logging.getLogger(__name__)


class AsaasService:
    """
    Cliente para API do ASAAS (Gateway de Pagamentos).

    Documentação: https://docs.asaas.com/reference

    Configuração necessária no .env:
        ASAAS_API_KEY=sua_api_key
        ASAAS_ENVIRONMENT=sandbox (ou production)
        ASAAS_WEBHOOK_TOKEN=token_seguro
    """

    def __init__(self):
        self.api_key = os.getenv("ASAAS_API_KEY")
        self.environment = os.getenv("ASAAS_ENVIRONMENT", "sandbox")
        self.webhook_token = os.getenv("ASAAS_WEBHOOK_TOKEN")

        # Define URL base conforme ambiente
        if self.environment == "production":
            self.base_url = "https://api.asaas.com/v3"
        else:
            self.base_url = "https://sandbox.asaas.com/api/v3"

        self.headers = {
            "Content-Type": "application/json",
            "access_token": self.api_key
        }

    # ==================== CLIENTES ====================

    async def criar_cliente(
        self,
        nome: str,
        email: str,
        cpf_cnpj: str,
        telefone: Optional[str] = None,
        endereco: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Cria um novo cliente no ASAAS.

        Args:
            nome: Nome completo do cliente
            email: E-mail do cliente
            cpf_cnpj: CPF ou CNPJ (apenas números)
            telefone: Telefone opcional
            endereco: Dicionário com address, addressNumber, province, postalCode, etc.

        Returns:
            Dicionário com dados do cliente criado, incluindo 'id' (asaas_customer_id)
        """
        payload = {
            "name": nome,
            "email": email,
            "cpfCnpj": cpf_cnpj
        }

        if telefone:
            payload["phone"] = telefone
            payload["mobilePhone"] = telefone

        if endereco:
            payload.update(endereco)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/customers",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"Cliente ASAAS criado: {data.get('id')} - {nome}")
                return {"success": True, "data": data}
            else:
                logger.error(f"Erro ao criar cliente ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def buscar_cliente(self, customer_id: str) -> Dict[str, Any]:
        """
        Busca um cliente pelo ID do ASAAS.

        Args:
            customer_id: ID do cliente no ASAAS (cus_xxx)

        Returns:
            Dicionário com dados do cliente
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/customers/{customer_id}",
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao buscar cliente ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def buscar_cliente_por_cpf(self, cpf_cnpj: str) -> Dict[str, Any]:
        """
        Busca um cliente pelo CPF/CNPJ.

        Args:
            cpf_cnpj: CPF ou CNPJ (apenas números)

        Returns:
            Dicionário com lista de clientes encontrados
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/customers",
                params={"cpfCnpj": cpf_cnpj},
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data.get("data", [])}
            else:
                logger.error(f"Erro ao buscar cliente por CPF: {response.text}")
                return {"success": False, "error": response.json()}

    async def atualizar_cliente(
        self,
        customer_id: str,
        dados: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atualiza dados de um cliente no ASAAS.

        Args:
            customer_id: ID do cliente no ASAAS
            dados: Dicionário com campos a atualizar

        Returns:
            Dicionário com dados do cliente atualizado
        """
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/customers/{customer_id}",
                json=dados,
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao atualizar cliente ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    # ==================== COBRANÇAS ====================

    async def criar_cobranca(
        self,
        customer_id: str,
        valor: float,
        vencimento: date,
        descricao: str,
        forma_pagamento: str = "UNDEFINED",
        parcelas: int = 1
    ) -> Dict[str, Any]:
        """
        Cria uma nova cobrança no ASAAS.

        Args:
            customer_id: ID do cliente no ASAAS
            valor: Valor da cobrança
            vencimento: Data de vencimento
            descricao: Descrição da cobrança
            forma_pagamento: BOLETO, PIX, CREDIT_CARD, ou UNDEFINED (cliente escolhe)
            parcelas: Número de parcelas (apenas para cartão)

        Returns:
            Dicionário com dados da cobrança criada
        """
        payload = {
            "customer": customer_id,
            "billingType": forma_pagamento,
            "value": float(valor),
            "dueDate": vencimento.isoformat() if isinstance(vencimento, date) else vencimento,
            "description": descricao
        }

        if forma_pagamento == "CREDIT_CARD" and parcelas > 1:
            payload["installmentCount"] = parcelas
            payload["installmentValue"] = float(valor) / parcelas

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/payments",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"Cobranca ASAAS criada: {data.get('id')} - R$ {valor}")
                return {"success": True, "data": data}
            else:
                logger.error(f"Erro ao criar cobranca ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def buscar_cobranca(self, payment_id: str) -> Dict[str, Any]:
        """
        Busca uma cobrança pelo ID do ASAAS.

        Args:
            payment_id: ID da cobrança no ASAAS (pay_xxx)

        Returns:
            Dicionário com dados da cobrança
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao buscar cobranca ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def listar_cobrancas_cliente(
        self,
        customer_id: str,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Lista cobranças de um cliente.

        Args:
            customer_id: ID do cliente no ASAAS
            status: Filtro por status (PENDING, RECEIVED, CONFIRMED, OVERDUE, etc.)
            offset: Paginação - início
            limit: Paginação - quantidade

        Returns:
            Dicionário com lista de cobranças
        """
        params = {
            "customer": customer_id,
            "offset": offset,
            "limit": limit
        }

        if status:
            params["status"] = status

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/payments",
                params=params,
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data.get("data", []), "total": data.get("totalCount", 0)}
            else:
                logger.error(f"Erro ao listar cobrancas ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def cancelar_cobranca(self, payment_id: str) -> Dict[str, Any]:
        """
        Cancela uma cobrança no ASAAS.

        Args:
            payment_id: ID da cobrança no ASAAS

        Returns:
            Dicionário com resultado da operação
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/payments/{payment_id}",
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                logger.info(f"Cobranca ASAAS cancelada: {payment_id}")
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao cancelar cobranca ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def obter_linha_digitavel(self, payment_id: str) -> Dict[str, Any]:
        """
        Obtém a linha digitável do boleto.

        Args:
            payment_id: ID da cobrança no ASAAS

        Returns:
            Dicionário com identificationField (linha digitável)
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/payments/{payment_id}/identificationField",
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao obter linha digitavel ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def obter_qrcode_pix(self, payment_id: str) -> Dict[str, Any]:
        """
        Obtém o QR Code PIX da cobrança.

        Args:
            payment_id: ID da cobrança no ASAAS

        Returns:
            Dicionário com payload (copia e cola) e encodedImage (base64)
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/payments/{payment_id}/pixQrCode",
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao obter QR Code PIX ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    # ==================== ASSINATURAS ====================

    async def criar_assinatura(
        self,
        customer_id: str,
        valor: float,
        ciclo: str,
        descricao: str,
        forma_pagamento: str = "UNDEFINED",
        data_proxima_cobranca: Optional[date] = None,
        dados_cartao: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria uma nova assinatura no ASAAS.

        Args:
            customer_id: ID do cliente no ASAAS
            valor: Valor da assinatura
            ciclo: WEEKLY, BIWEEKLY, MONTHLY, QUARTERLY, SEMIANNUALLY, YEARLY
            descricao: Descrição da assinatura
            forma_pagamento: BOLETO, PIX, CREDIT_CARD, ou UNDEFINED
            data_proxima_cobranca: Data da primeira/próxima cobrança
            dados_cartao: Dados do cartão para cobrança recorrente (se aplicável)

        Returns:
            Dicionário com dados da assinatura criada
        """
        payload = {
            "customer": customer_id,
            "billingType": forma_pagamento,
            "value": float(valor),
            "cycle": ciclo,
            "description": descricao
        }

        if data_proxima_cobranca:
            payload["nextDueDate"] = data_proxima_cobranca.isoformat() if isinstance(data_proxima_cobranca, date) else data_proxima_cobranca

        if forma_pagamento == "CREDIT_CARD" and dados_cartao:
            payload["creditCard"] = dados_cartao.get("creditCard")
            payload["creditCardHolderInfo"] = dados_cartao.get("creditCardHolderInfo")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/subscriptions",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"Assinatura ASAAS criada: {data.get('id')} - R$ {valor}/{ciclo}")
                return {"success": True, "data": data}
            else:
                logger.error(f"Erro ao criar assinatura ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def buscar_assinatura(self, subscription_id: str) -> Dict[str, Any]:
        """
        Busca uma assinatura pelo ID do ASAAS.

        Args:
            subscription_id: ID da assinatura no ASAAS (sub_xxx)

        Returns:
            Dicionário com dados da assinatura
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/subscriptions/{subscription_id}",
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao buscar assinatura ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def listar_assinaturas_cliente(
        self,
        customer_id: str,
        offset: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Lista assinaturas de um cliente.

        Args:
            customer_id: ID do cliente no ASAAS
            offset: Paginação - início
            limit: Paginação - quantidade

        Returns:
            Dicionário com lista de assinaturas
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/subscriptions",
                params={"customer": customer_id, "offset": offset, "limit": limit},
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data.get("data", []), "total": data.get("totalCount", 0)}
            else:
                logger.error(f"Erro ao listar assinaturas ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def atualizar_assinatura(
        self,
        subscription_id: str,
        dados: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atualiza uma assinatura no ASAAS.

        Args:
            subscription_id: ID da assinatura no ASAAS
            dados: Dicionário com campos a atualizar (value, cycle, nextDueDate, etc.)

        Returns:
            Dicionário com dados da assinatura atualizada
        """
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/subscriptions/{subscription_id}",
                json=dados,
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                logger.info(f"Assinatura ASAAS atualizada: {subscription_id}")
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao atualizar assinatura ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def cancelar_assinatura(self, subscription_id: str) -> Dict[str, Any]:
        """
        Cancela uma assinatura no ASAAS.

        Args:
            subscription_id: ID da assinatura no ASAAS

        Returns:
            Dicionário com resultado da operação
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/subscriptions/{subscription_id}",
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                logger.info(f"Assinatura ASAAS cancelada: {subscription_id}")
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao cancelar assinatura ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    async def listar_cobrancas_assinatura(
        self,
        subscription_id: str,
        offset: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Lista cobranças de uma assinatura.

        Args:
            subscription_id: ID da assinatura no ASAAS
            offset: Paginação - início
            limit: Paginação - quantidade

        Returns:
            Dicionário com lista de cobranças
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/subscriptions/{subscription_id}/payments",
                params={"offset": offset, "limit": limit},
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data.get("data", []), "total": data.get("totalCount", 0)}
            else:
                logger.error(f"Erro ao listar cobrancas da assinatura ASAAS: {response.text}")
                return {"success": False, "error": response.json()}

    # ==================== UTILITÁRIOS ====================

    def validar_webhook_token(self, token: str) -> bool:
        """
        Valida o token de webhook recebido.

        Args:
            token: Token recebido no header do webhook

        Returns:
            True se o token é válido
        """
        return token == self.webhook_token

    def mapear_status_pagamento(self, status_asaas: str) -> str:
        """
        Mapeia status do ASAAS para status interno.

        Args:
            status_asaas: Status retornado pelo ASAAS

        Returns:
            Status interno do sistema
        """
        mapeamento = {
            "PENDING": "PENDING",
            "RECEIVED": "RECEIVED",
            "CONFIRMED": "CONFIRMED",
            "OVERDUE": "OVERDUE",
            "REFUNDED": "REFUNDED",
            "RECEIVED_IN_CASH": "RECEIVED",
            "REFUND_REQUESTED": "REFUNDED",
            "REFUND_IN_PROGRESS": "REFUNDED",
            "CHARGEBACK_REQUESTED": "REFUNDED",
            "CHARGEBACK_DISPUTE": "REFUNDED",
            "AWAITING_CHARGEBACK_REVERSAL": "REFUNDED",
            "DUNNING_REQUESTED": "OVERDUE",
            "DUNNING_RECEIVED": "RECEIVED",
            "AWAITING_RISK_ANALYSIS": "PENDING"
        }
        return mapeamento.get(status_asaas, status_asaas)

    def mapear_ciclo_assinatura(self, ciclo_interno: str) -> str:
        """
        Mapeia ciclo interno para ciclo do ASAAS.

        Args:
            ciclo_interno: mensal, trimestral, semestral, anual

        Returns:
            Ciclo no formato ASAAS
        """
        mapeamento = {
            "mensal": "MONTHLY",
            "trimestral": "QUARTERLY",
            "semestral": "SEMIANNUALLY",
            "anual": "YEARLY"
        }
        return mapeamento.get(ciclo_interno.lower(), "MONTHLY")
