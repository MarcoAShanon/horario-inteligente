"""
Serviço de Templates do WhatsApp Business API

Camada de abstração para envio de templates aprovados na Meta.
Cada método corresponde a um template específico com suas variáveis na ordem correta.
"""

from typing import List, Dict, Any
from app.services.whatsapp_official_service import WhatsAppOfficialService
from app.services.whatsapp_interface import SendResult


class WhatsAppTemplateService:
    """
    Serviço para envio de templates do WhatsApp.

    Abstrai a complexidade de montar os components da API da Meta,
    oferecendo métodos tipados e documentados para cada template.
    """

    def __init__(self, whatsapp_service: WhatsAppOfficialService = None):
        """
        Inicializa o serviço de templates.

        Args:
            whatsapp_service: Instância do WhatsAppOfficialService.
                              Se não fornecida, cria uma nova.
        """
        self.whatsapp = whatsapp_service or WhatsAppOfficialService()

    def _build_body_components(self, variables: List[str]) -> List[Dict[str, Any]]:
        """
        Transforma lista de strings em estrutura de components da Meta.

        Args:
            variables: Lista de valores das variáveis na ordem do template.

        Returns:
            Lista de components no formato esperado pela API da Meta.
        """
        return [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(var)} for var in variables
                ]
            }
        ]

    def _build_components_with_url_button(
        self,
        variables: List[str],
        url: str
    ) -> List[Dict[str, Any]]:
        """
        Monta components com variáveis no body + botão URL dinâmica.

        Args:
            variables: Lista de valores das variáveis na ordem do template.
            url: URL dinâmica para o botão (ex: link do boleto/pix).

        Returns:
            Lista de components com body + button URL.
        """
        return [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(var)} for var in variables
                ]
            },
            {
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [
                    {"type": "text", "text": url}
                ]
            }
        ]

    # ==================== TEMPLATE DE TESTE ====================

    async def enviar_hello_world(self, telefone: str) -> SendResult:
        """
        Envia template de teste hello_world.

        Template: hello_world (sem variáveis)

        Args:
            telefone: Número do destinatário

        Returns:
            SendResult com status do envio
        """
        return await self.whatsapp.send_template(
            to=telefone,
            template_name="hello_world",
            language_code="en_US",
            components=None
        )

    # ==================== TEMPLATES DE LEMBRETE ====================

    async def enviar_lembrete_24h(
        self,
        telefone: str,
        paciente: str,
        medico: str,
        data: str,
        hora: str
    ) -> SendResult:
        """
        Envia lembrete de consulta 24 horas antes.

        Template: lembrete_24h
        Botões: "Confirmar presença", "Preciso remarcar"

        Args:
            telefone: Número do paciente (ex: 5521999999999)
            paciente: Nome do paciente
            medico: Nome do médico (ex: "Dr. João Silva")
            data: Data da consulta (formato: DD/MM/AAAA)
            hora: Horário da consulta (formato: HH:MM)

        Returns:
            SendResult com status do envio
        """
        variables = [paciente, medico, data, hora]
        components = self._build_body_components(variables)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="lembrete_24h",
            language_code="pt_BR",
            components=components
        )

    async def enviar_lembrete_2h(
        self,
        telefone: str,
        paciente: str,
        medico: str,
        hora: str
    ) -> SendResult:
        """
        Envia lembrete de consulta 2 horas antes.

        Template: lembrete_2h
        Botões: "Estou a caminho", "Preciso remarcar"

        Args:
            telefone: Número do paciente
            paciente: Nome do paciente
            medico: Nome do médico
            hora: Horário da consulta (formato: HH:MM)

        Returns:
            SendResult com status do envio
        """
        variables = [paciente, medico, hora]
        components = self._build_body_components(variables)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="lembrete_2h",
            language_code="pt_BR",
            components=components
        )

    # ==================== TEMPLATES DE CONFIRMAÇÃO ====================

    async def enviar_consulta_confirmada(
        self,
        telefone: str,
        paciente: str,
        medico: str,
        data: str,
        hora: str,
        local: str
    ) -> SendResult:
        """
        Envia confirmação de consulta agendada.

        Template: consulta_confirmada

        Args:
            telefone: Número do paciente
            paciente: Nome do paciente
            medico: Nome do médico
            data: Data da consulta (formato: DD/MM/AAAA)
            hora: Horário da consulta (formato: HH:MM)
            local: Endereço ou local da consulta

        Returns:
            SendResult com status do envio
        """
        variables = [paciente, medico, data, hora, local]
        components = self._build_body_components(variables)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="consulta_confirmada",
            language_code="pt_BR",
            components=components
        )

    # ==================== TEMPLATES DE CANCELAMENTO ====================

    async def enviar_consulta_cancelada(
        self,
        telefone: str,
        paciente: str,
        medico: str,
        data: str,
        hora: str,
        motivo: str
    ) -> SendResult:
        """
        Envia notificação de cancelamento pela clínica.

        Template: consulta_cancelada_clinica
        Botões: "Reagendar consulta", "Entendi"

        Args:
            telefone: Número do paciente
            paciente: Nome do paciente
            medico: Nome do médico
            data: Data da consulta cancelada (formato: DD/MM/AAAA)
            hora: Horário da consulta cancelada (formato: HH:MM)
            motivo: Motivo do cancelamento

        Returns:
            SendResult com status do envio
        """
        variables = [paciente, medico, data, hora, motivo]
        components = self._build_body_components(variables)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="consulta_cancelada_clinica",
            language_code="pt_BR",
            components=components
        )

    # ==================== TEMPLATES DE REAGENDAMENTO ====================

    async def enviar_consulta_reagendada(
        self,
        telefone: str,
        paciente: str,
        medico: str,
        data_antiga: str,
        hora_antiga: str,
        data_nova: str,
        hora_nova: str
    ) -> SendResult:
        """
        Envia notificação de reagendamento pela clínica.

        Template: consulta_reagendada_clinica
        Botões: "Confirmar novo horário", "Preciso de outro horário"

        Args:
            telefone: Número do paciente
            paciente: Nome do paciente
            medico: Nome do médico
            data_antiga: Data original (formato: DD/MM/AAAA)
            hora_antiga: Horário original (formato: HH:MM)
            data_nova: Nova data (formato: DD/MM/AAAA)
            hora_nova: Novo horário (formato: HH:MM)

        Returns:
            SendResult com status do envio
        """
        variables = [paciente, medico, data_antiga, hora_antiga, data_nova, hora_nova]
        components = self._build_body_components(variables)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="consulta_reagendada_clinica",
            language_code="pt_BR",
            components=components
        )

    # ==================== TEMPLATES DE RETORNO ====================

    async def enviar_retorno_agendado(
        self,
        telefone: str,
        paciente: str,
        medico: str,
        data: str,
        hora: str,
        procedimento: str
    ) -> SendResult:
        """
        Envia confirmação de retorno agendado.

        Template: retorno_agendado

        Args:
            telefone: Número do paciente
            paciente: Nome do paciente
            medico: Nome do médico
            data: Data do retorno (formato: DD/MM/AAAA)
            hora: Horário do retorno (formato: HH:MM)
            procedimento: Tipo de retorno ou procedimento

        Returns:
            SendResult com status do envio
        """
        variables = [paciente, medico, data, hora, procedimento]
        components = self._build_body_components(variables)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="retorno_agendado",
            language_code="pt_BR",
            components=components
        )

    # ==================== TEMPLATES DE PAGAMENTO ====================

    async def enviar_pagamento_pendente(
        self,
        telefone: str,
        cliente: str,
        valor: str,
        vencimento: str,
        url_pagamento: str
    ) -> SendResult:
        """
        Envia notificação de pagamento pendente com link.

        Template: pagamento_pendente
        Botão URL: Link do boleto/pix

        Args:
            telefone: Número do cliente
            cliente: Nome do cliente
            valor: Valor a pagar (ex: "99,90")
            vencimento: Data de vencimento (formato: DD/MM/AAAA)
            url_pagamento: URL do boleto ou pix

        Returns:
            SendResult com status do envio
        """
        variables = [cliente, valor, vencimento]
        components = self._build_components_with_url_button(variables, url_pagamento)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="pagamento_pendente",
            language_code="pt_BR",
            components=components
        )

    async def enviar_pagamento_vencido(
        self,
        telefone: str,
        cliente: str,
        valor: str,
        vencimento: str,
        url_pagamento: str
    ) -> SendResult:
        """
        Envia notificação de pagamento vencido com link.

        Template: pagamento_vencido
        Botão URL: Link do boleto/pix

        Args:
            telefone: Número do cliente
            cliente: Nome do cliente
            valor: Valor em atraso (ex: "199,90")
            vencimento: Data que venceu (formato: DD/MM/AAAA)
            url_pagamento: URL do boleto ou pix

        Returns:
            SendResult com status do envio
        """
        variables = [cliente, valor, vencimento]
        components = self._build_components_with_url_button(variables, url_pagamento)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="pagamento_vencido",
            language_code="pt_BR",
            components=components
        )

    async def enviar_pagamento_confirmado(
        self,
        telefone: str,
        cliente: str,
        valor: str,
        data_pagamento: str
    ) -> SendResult:
        """
        Envia confirmação de pagamento recebido.

        Template: pagamento_confirmado (sem botão)

        Args:
            telefone: Número do cliente
            cliente: Nome do cliente
            valor: Valor pago (ex: "99,90")
            data_pagamento: Data do pagamento (formato: DD/MM/AAAA)

        Returns:
            SendResult com status do envio
        """
        variables = [cliente, valor, data_pagamento]
        components = self._build_body_components(variables)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="pagamento_confirmado",
            language_code="pt_BR",
            components=components
        )

    async def enviar_conta_suspensa(
        self,
        telefone: str,
        cliente: str,
        valor: str,
        url_pagamento: str
    ) -> SendResult:
        """
        Envia notificação de conta suspensa por inadimplência.

        Template: conta_suspensa
        Botão URL: Link do boleto/pix

        Args:
            telefone: Número do cliente
            cliente: Nome do cliente
            valor: Valor pendente total (ex: "299,90")
            url_pagamento: URL do boleto ou pix

        Returns:
            SendResult com status do envio
        """
        variables = [cliente, valor]
        components = self._build_components_with_url_button(variables, url_pagamento)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="conta_suspensa",
            language_code="pt_BR",
            components=components
        )

    # ==================== TEMPLATES DE RELACIONAMENTO ====================

    async def enviar_boas_vindas(
        self,
        telefone: str,
        clinica: str,
        paciente: str
    ) -> SendResult:
        """
        Envia mensagem de boas-vindas para novo paciente.

        Template: boas_vindas_clinica

        Args:
            telefone: Número do paciente
            clinica: Nome da clínica
            paciente: Nome do paciente

        Returns:
            SendResult com status do envio
        """
        variables = [clinica, paciente]
        components = self._build_body_components(variables)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="boas_vindas_clinica",
            language_code="pt_BR",
            components=components
        )

    async def enviar_pesquisa_satisfacao(
        self,
        telefone: str,
        paciente: str,
        medico: str,
        data_consulta: str
    ) -> SendResult:
        """
        Envia pesquisa de satisfação pós-consulta.

        Template: pesquisa_satisfacao

        Args:
            telefone: Número do paciente
            paciente: Nome do paciente
            medico: Nome do médico
            data_consulta: Data da consulta realizada (formato: DD/MM/AAAA)

        Returns:
            SendResult com status do envio
        """
        variables = [paciente, medico, data_consulta]
        components = self._build_body_components(variables)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="pesquisa_satisfacao",
            language_code="pt_BR",
            components=components
        )

    async def enviar_paciente_inativo(
        self,
        telefone: str,
        paciente: str,
        clinica: str,
        ultima_consulta: str
    ) -> SendResult:
        """
        Envia mensagem para reativar paciente inativo.

        Template: paciente_inativo

        Args:
            telefone: Número do paciente
            paciente: Nome do paciente
            clinica: Nome da clínica
            ultima_consulta: Data da última consulta (formato: DD/MM/AAAA)

        Returns:
            SendResult com status do envio
        """
        variables = [paciente, clinica, ultima_consulta]
        components = self._build_body_components(variables)

        return await self.whatsapp.send_template(
            to=telefone,
            template_name="paciente_inativo",
            language_code="pt_BR",
            components=components
        )


# ==================== INSTÂNCIA SINGLETON ====================

_template_service_instance = None


def get_template_service() -> WhatsAppTemplateService:
    """
    Retorna instância singleton do serviço de templates.

    Returns:
        WhatsAppTemplateService configurado
    """
    global _template_service_instance

    if _template_service_instance is None:
        _template_service_instance = WhatsAppTemplateService()

    return _template_service_instance
