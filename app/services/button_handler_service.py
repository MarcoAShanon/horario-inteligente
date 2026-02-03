"""
Serviço de Tratamento de Botões Interativos do WhatsApp

Processa respostas de botões de templates aprovados na Meta.
Cada botão tem uma ação específica associada.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.agendamento import Agendamento
from app.models.cliente import Cliente
from app.utils.timezone_helper import now_brazil
from app.models.paciente import Paciente
from app.models.lembrete import Lembrete, StatusLembrete
from app.services.whatsapp_official_service import WhatsAppOfficialService
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class ButtonHandlerService:
    """
    Serviço para processar cliques em botões de templates WhatsApp.

    Mapeia o texto do botão para a ação correspondente e executa.
    """

    # Mapeamento de texto do botão -> ação
    BUTTON_ACTIONS = {
        # Confirmações
        "Confirmar presença": "confirmar",
        "Confirmar": "confirmar",
        "Estou a caminho": "confirmar",  # Botão do lembrete de 2h

        # Remarcações
        "Preciso remarcar": "remarcar",
        "Reagendar": "remarcar",

        # Cancelamentos
        "Não vou conseguir ir": "cancelar",
        "Cancelar": "cancelar",

        # Confirmações simples (sem ação no agendamento)
        "Ok, entendi": "entendido",

        # Pesquisa de satisfação
        "1-2": "avaliacao_ruim",
        "3": "avaliacao_media",
        "4-5": "avaliacao_boa",

        # Paciente inativo
        "Agendar agora": "iniciar_agendamento",
        "Nao tenho interesse": "sem_interesse",
    }

    def __init__(self):
        self.whatsapp = WhatsAppOfficialService()

    async def processar_botao(
        self,
        db: Session,
        telefone: str,
        button_text: str,
        cliente_id: int
    ) -> Dict[str, Any]:
        """
        Processa o clique em um botão de template.

        Args:
            db: Sessão do banco de dados
            telefone: Número do paciente
            button_text: Texto do botão clicado
            cliente_id: ID do cliente (tenant)

        Returns:
            Dict com:
                - handled: bool - Se foi tratado por este serviço
                - action: str - Ação executada
                - response: str - Mensagem de resposta para o paciente
                - notify_clinic: bool - Se deve notificar a clínica
        """
        # Identificar ação pelo texto do botão
        action = self.BUTTON_ACTIONS.get(button_text)

        if not action:
            logger.info(f"[ButtonHandler] Botão não mapeado: '{button_text}'")
            return {"handled": False}

        logger.info(f"[ButtonHandler] Processando botão '{button_text}' -> ação '{action}'")

        # Buscar paciente pelo telefone
        paciente = self._buscar_paciente(db, telefone, cliente_id)

        if not paciente:
            logger.warning(f"[ButtonHandler] Paciente não encontrado para telefone {telefone}")
            return {
                "handled": True,
                "action": action,
                "response": "Desculpe, não encontrei seu cadastro. Por favor, entre em contato com a clínica.",
                "notify_clinic": False
            }

        # Executar ação correspondente
        if action == "confirmar":
            return await self._handle_confirmar(db, paciente, cliente_id)

        elif action == "remarcar":
            return await self._handle_remarcar(db, paciente, cliente_id)

        elif action == "cancelar":
            return await self._handle_cancelar(db, paciente, cliente_id)

        elif action == "entendido":
            return await self._handle_entendido(db, paciente)

        elif action in ["avaliacao_ruim", "avaliacao_media", "avaliacao_boa"]:
            return await self._handle_avaliacao(db, paciente, action, cliente_id)

        elif action == "iniciar_agendamento":
            return await self._handle_iniciar_agendamento(db, paciente)

        elif action == "sem_interesse":
            return await self._handle_sem_interesse(db, paciente)

        else:
            return {"handled": False}

    def _buscar_paciente(
        self,
        db: Session,
        telefone: str,
        cliente_id: int
    ) -> Optional[Paciente]:
        """Busca paciente pelo telefone."""
        telefone_limpo = ''.join(filter(str.isdigit, telefone))

        return db.query(Paciente).filter(
            Paciente.cliente_id == cliente_id,
            Paciente.telefone.like(f"%{telefone_limpo[-8:]}%")
        ).first()

    def _buscar_agendamento_pendente(
        self,
        db: Session,
        paciente_id: int,
        incluir_recentes: bool = False
    ) -> Optional[Agendamento]:
        """
        Busca agendamento pendente mais próximo do paciente.

        Args:
            paciente_id: ID do paciente
            incluir_recentes: Se True, inclui consultas das últimas 2h (para cancelar/remarcar)
        """
        agora = now_brazil()

        if incluir_recentes:
            # Para cancelar/remarcar, incluir consultas que começaram há até 2h
            # Isso cobre casos onde o paciente clica no botão pouco após o horário
            limite_inferior = agora - timedelta(hours=2)
        else:
            # Para confirmar presença, só consultas futuras
            limite_inferior = agora

        return db.query(Agendamento).filter(
            Agendamento.paciente_id == paciente_id,
            Agendamento.status.in_(["agendado", "confirmado"]),
            Agendamento.data_hora >= limite_inferior
        ).order_by(Agendamento.data_hora).first()

    def _buscar_endereco_clinica(self, db: Session, cliente_id: int) -> Optional[str]:
        """Busca o endereço da clínica pelo cliente_id."""
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        return cliente.endereco if cliente else None

    def _montar_orientacoes_consulta(
        self,
        endereco: Optional[str],
        eh_convenio: bool = False
    ) -> str:
        """
        Monta as orientações padrão para a consulta.

        Inclui: endereço, documento com foto, exames recentes.
        """
        orientacoes = []

        if endereco:
            orientacoes.append(f"📍 Nosso endereço: {endereco}")

        # Documento com foto - mais enfático para convênio
        if eh_convenio:
            orientacoes.append("🪪 Traga documento com foto e carteirinha do convênio")
        else:
            orientacoes.append("🪪 Traga documento com foto")

        orientacoes.append("📎 Se tiver exames recentes, traga no dia da consulta!")

        return "\n".join(orientacoes)

    # ==================== HANDLERS DE AÇÕES ====================

    async def _handle_confirmar(
        self,
        db: Session,
        paciente: Paciente,
        cliente_id: int
    ) -> Dict[str, Any]:
        """Confirma presença na consulta."""
        agendamento = self._buscar_agendamento_pendente(db, paciente.id)

        if not agendamento:
            return {
                "handled": True,
                "action": "confirmar",
                "response": f"Olá {paciente.nome.split()[0]}! Não encontrei nenhuma consulta pendente para confirmar. Se precisar agendar, é só me chamar!",
                "notify_clinic": False
            }

        # Atualizar status
        status_anterior = agendamento.status
        agendamento.status = "confirmado"

        # Atualizar lembrete se existir
        lembrete = db.query(Lembrete).filter(
            Lembrete.agendamento_id == agendamento.id,
            Lembrete.status == StatusLembrete.ENVIADO.value
        ).first()

        if lembrete:
            lembrete.status = StatusLembrete.CONFIRMADO.value
            lembrete.resposta_paciente = "Confirmar presença"
            lembrete.respondido_em = now_brazil()

        db.commit()

        # Formatar data/hora
        data_formatada = agendamento.data_hora.strftime("%d/%m/%Y")
        hora_formatada = agendamento.data_hora.strftime("%H:%M")
        medico_nome = agendamento.medico.nome if agendamento.medico else "médico"

        # Verificar se é convênio
        eh_convenio = agendamento.forma_pagamento and agendamento.forma_pagamento.startswith("convenio")

        # Buscar endereço da clínica
        endereco = self._buscar_endereco_clinica(db, cliente_id)

        # Montar orientações
        orientacoes = self._montar_orientacoes_consulta(endereco, eh_convenio)

        logger.info(
            f"[ButtonHandler] ✅ Consulta confirmada: "
            f"Paciente={paciente.nome}, Agendamento={agendamento.id}, "
            f"Status: {status_anterior} -> confirmado"
        )

        # Notificar via WebSocket
        await websocket_manager.send_agendamento_atualizado(
            cliente_id=cliente_id,
            agendamento={
                "id": agendamento.id,
                "paciente_nome": paciente.nome,
                "status": "confirmado",
                "data_hora": agendamento.data_hora.isoformat(),
                "evento": "confirmado_pelo_paciente"
            }
        )

        return {
            "handled": True,
            "action": "confirmar",
            "response": (
                f"Perfeito, {paciente.nome.split()[0]}! ✅\n\n"
                f"Sua consulta está confirmada para:\n"
                f"📅 {data_formatada} às {hora_formatada}\n"
                f"👨‍⚕️ {medico_nome}\n\n"
                f"{orientacoes}\n\n"
                f"Aguardamos você!"
            ),
            "notify_clinic": True,
            "agendamento_id": agendamento.id
        }

    async def _handle_remarcar(
        self,
        db: Session,
        paciente: Paciente,
        cliente_id: int
    ) -> Dict[str, Any]:
        """Inicia fluxo de remarcação."""
        # incluir_recentes=True para encontrar consultas que acabaram de passar
        agendamento = self._buscar_agendamento_pendente(db, paciente.id, incluir_recentes=True)

        if not agendamento:
            return {
                "handled": True,
                "action": "remarcar",
                "response": f"Olá {paciente.nome.split()[0]}! Não encontrei nenhuma consulta para remarcar. Se precisar agendar uma nova, é só me chamar!",
                "notify_clinic": False
            }

        # Atualizar lembrete se existir
        lembrete = db.query(Lembrete).filter(
            Lembrete.agendamento_id == agendamento.id,
            Lembrete.status == StatusLembrete.ENVIADO.value
        ).first()

        if lembrete:
            lembrete.status = StatusLembrete.REMARCAR.value
            lembrete.resposta_paciente = "Preciso remarcar"
            lembrete.respondido_em = now_brazil()
            db.commit()

        # Formatar data/hora atual
        data_formatada = agendamento.data_hora.strftime("%d/%m/%Y")
        hora_formatada = agendamento.data_hora.strftime("%H:%M")

        logger.info(
            f"[ButtonHandler] 🔄 Remarcação solicitada: "
            f"Paciente={paciente.nome}, Agendamento={agendamento.id}"
        )

        # Notificar via WebSocket
        await websocket_manager.send_agendamento_atualizado(
            cliente_id=cliente_id,
            agendamento={
                "id": agendamento.id,
                "paciente_nome": paciente.nome,
                "paciente_telefone": paciente.telefone,
                "status": agendamento.status,
                "data_hora": agendamento.data_hora.isoformat(),
                "evento": "remarcacao_solicitada"
            }
        )

        return {
            "handled": True,
            "action": "remarcar",
            "response": (
                f"Entendi, {paciente.nome.split()[0]}! 🔄\n\n"
                f"Sua consulta atual é:\n"
                f"📅 {data_formatada} às {hora_formatada}\n\n"
                f"Para qual data e horário você gostaria de remarcar?"
            ),
            "notify_clinic": True,
            "agendamento_id": agendamento.id,
            "await_new_datetime": True  # Sinaliza que espera nova data/hora
        }

    async def _handle_cancelar(
        self,
        db: Session,
        paciente: Paciente,
        cliente_id: int
    ) -> Dict[str, Any]:
        """
        Processa "Não vou conseguir ir" - oferece remarcar ao invés de cancelar direto.

        IMPORTANTE: Não cancela automaticamente! Pergunta se quer remarcar.
        O cancelamento efetivo só acontece se o paciente confirmar ou a IA processar.
        """
        # incluir_recentes=True para encontrar consultas que acabaram de passar
        agendamento = self._buscar_agendamento_pendente(db, paciente.id, incluir_recentes=True)

        if not agendamento:
            return {
                "handled": True,
                "action": "cancelar",
                "response": (
                    f"Olá {paciente.nome.split()[0]}! Não encontrei nenhuma consulta agendada.\n\n"
                    f"Se precisar agendar uma consulta, é só me dizer!"
                ),
                "notify_clinic": False,
                "forward_to_ai": True  # Deixa a IA continuar a conversa
            }

        # Guardar dados da consulta
        data_formatada = agendamento.data_hora.strftime("%d/%m/%Y")
        hora_formatada = agendamento.data_hora.strftime("%H:%M")
        medico_nome = agendamento.medico.nome if agendamento.medico else "médico"

        # Atualizar lembrete para registrar a resposta (mas NÃO cancela ainda)
        lembrete = db.query(Lembrete).filter(
            Lembrete.agendamento_id == agendamento.id,
            Lembrete.status == StatusLembrete.ENVIADO.value
        ).first()

        if lembrete:
            lembrete.status = StatusLembrete.REMARCAR.value  # Marca como remarcar, não cancelar
            lembrete.resposta_paciente = "Não vou conseguir ir"
            lembrete.respondido_em = now_brazil()
            db.commit()

        logger.info(
            f"[ButtonHandler] 🔄 'Não vou conseguir ir' - oferecendo remarcar: "
            f"Paciente={paciente.nome}, Agendamento={agendamento.id}"
        )

        # Notificar via WebSocket
        await websocket_manager.send_agendamento_atualizado(
            cliente_id=cliente_id,
            agendamento={
                "id": agendamento.id,
                "paciente_nome": paciente.nome,
                "paciente_telefone": paciente.telefone,
                "medico_nome": medico_nome,
                "status": agendamento.status,  # Mantém status atual
                "data_hora": agendamento.data_hora.isoformat(),
                "evento": "paciente_nao_pode_ir",
                "urgente": True
            }
        )

        # Resposta oferecendo remarcar (NÃO cancela automaticamente)
        return {
            "handled": True,
            "action": "oferecer_remarcar",
            "response": (
                f"Entendi, {paciente.nome.split()[0]}! 😊\n\n"
                f"Sua consulta está marcada para:\n"
                f"📅 {data_formatada} às {hora_formatada}\n"
                f"👨‍⚕️ {medico_nome}\n\n"
                f"Você gostaria de *remarcar* para outra data ou prefere *cancelar* completamente?"
            ),
            "notify_clinic": True,
            "agendamento_id": agendamento.id,
            "urgente": True,
            "await_remarcar_ou_cancelar": True  # Sinaliza que espera decisão
        }

    async def _handle_entendido(
        self,
        db: Session,
        paciente: Paciente
    ) -> Dict[str, Any]:
        """Apenas confirmação de recebimento."""
        return {
            "handled": True,
            "action": "entendido",
            "response": f"Perfeito, {paciente.nome.split()[0]}! Se precisar de algo, é só chamar. 😊",
            "notify_clinic": False
        }

    async def _handle_avaliacao(
        self,
        db: Session,
        paciente: Paciente,
        nivel: str,
        cliente_id: int
    ) -> Dict[str, Any]:
        """Processa avaliação de satisfação."""
        # Mapear nível para nota
        notas = {
            "avaliacao_ruim": (1, 2),
            "avaliacao_media": (3, 3),
            "avaliacao_boa": (4, 5)
        }
        nota_min, nota_max = notas.get(nivel, (3, 3))

        logger.info(
            f"[ButtonHandler] ⭐ Avaliação recebida: "
            f"Paciente={paciente.nome}, Nível={nivel} ({nota_min}-{nota_max})"
        )

        # Notificar via WebSocket (avaliação - log apenas por enquanto)
        try:
            await websocket_manager.send_agendamento_atualizado(
                cliente_id=cliente_id,
                agendamento={
                    "id": 0,  # Não há agendamento específico
                    "paciente_nome": paciente.nome,
                    "paciente_telefone": paciente.telefone,
                    "status": "avaliacao",
                    "evento": f"avaliacao_{nivel}",
                    "nota_range": f"{nota_min}-{nota_max}"
                }
            )
        except Exception as e:
            logger.warning(f"[ButtonHandler] Erro ao notificar avaliação: {e}")

        if nivel == "avaliacao_ruim":
            return {
                "handled": True,
                "action": nivel,
                "response": (
                    f"Obrigado pelo feedback, {paciente.nome.split()[0]}. 🙏\n\n"
                    f"Lamentamos que sua experiência não tenha sido satisfatória. "
                    f"Poderia nos contar o que aconteceu? Queremos melhorar!"
                ),
                "notify_clinic": True,
                "urgente": True  # Avaliação ruim é urgente
            }
        elif nivel == "avaliacao_media":
            return {
                "handled": True,
                "action": nivel,
                "response": (
                    f"Obrigado pelo feedback, {paciente.nome.split()[0]}! 🙏\n\n"
                    f"Ficamos felizes em atendê-lo(a). "
                    f"Tem algo que poderíamos melhorar?"
                ),
                "notify_clinic": True
            }
        else:  # avaliacao_boa
            return {
                "handled": True,
                "action": nivel,
                "response": (
                    f"Muito obrigado, {paciente.nome.split()[0]}! ⭐⭐⭐⭐⭐\n\n"
                    f"Ficamos muito felizes com sua avaliação! "
                    f"Conte sempre conosco. 😊"
                ),
                "notify_clinic": True
            }

    async def _handle_iniciar_agendamento(
        self,
        db: Session,
        paciente: Paciente
    ) -> Dict[str, Any]:
        """Inicia fluxo de novo agendamento."""
        return {
            "handled": True,
            "action": "iniciar_agendamento",
            "response": (
                f"Ótimo, {paciente.nome.split()[0]}! 📅\n\n"
                f"Vamos agendar sua consulta.\n"
                f"Qual especialidade você precisa?"
            ),
            "notify_clinic": False,
            "start_scheduling_flow": True
        }

    async def _handle_sem_interesse(
        self,
        db: Session,
        paciente: Paciente
    ) -> Dict[str, Any]:
        """Paciente não tem interesse em agendar."""
        logger.info(f"[ButtonHandler] Paciente {paciente.nome} sem interesse em agendar")

        return {
            "handled": True,
            "action": "sem_interesse",
            "response": (
                f"Tudo bem, {paciente.nome.split()[0]}! 😊\n\n"
                f"Quando precisar, estaremos à disposição."
            ),
            "notify_clinic": False
        }


# ==================== INSTÂNCIA SINGLETON ====================

_button_handler_instance = None


def get_button_handler() -> ButtonHandlerService:
    """Retorna instância singleton do serviço."""
    global _button_handler_instance

    if _button_handler_instance is None:
        _button_handler_instance = ButtonHandlerService()

    return _button_handler_instance
