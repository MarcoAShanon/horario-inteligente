"""
Serviço de Processamento de Faltas
Envia mensagem empática via WhatsApp e sugere reagendamento
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from app.utils.timezone_helper import now_brazil, format_brazil

logger = logging.getLogger(__name__)


class FaltaService:
    """Gerencia o processamento de faltas e reagendamento automático"""

    def __init__(self, db: Session):
        self.db = db

    async def marcar_como_falta(self, agendamento_id: int) -> Dict:
        """
        Marca agendamento como falta e dispara processo de recuperação

        Args:
            agendamento_id: ID do agendamento

        Returns:
            dict com status do processamento
        """
        try:
            # Buscar agendamento com dados do paciente e médico
            result = self.db.execute(text("""
                SELECT
                    a.id,
                    a.data_hora,
                    a.status,
                    p.nome as paciente_nome,
                    p.telefone as paciente_telefone,
                    p.cliente_id,
                    m.nome as medico_nome,
                    m.id as medico_id
                FROM agendamentos a
                JOIN pacientes p ON a.paciente_id = p.id
                JOIN medicos m ON a.medico_id = m.id
                WHERE a.id = :agendamento_id
            """), {"agendamento_id": agendamento_id}).fetchone()

            if not result:
                return {
                    "sucesso": False,
                    "erro": "Agendamento não encontrado"
                }

            # Verificar se já passou a data/hora
            agendamento_data = result[1]
            if agendamento_data > now_brazil():
                return {
                    "sucesso": False,
                    "erro": "Não é possível marcar como falta um agendamento futuro"
                }

            # Atualizar status para "faltou"
            self.db.execute(text("""
                UPDATE agendamentos
                SET status = 'faltou',
                    atualizado_em = NOW()
                WHERE id = :agendamento_id
            """), {"agendamento_id": agendamento_id})

            self.db.commit()

            # Buscar próximos horários disponíveis
            proximos_horarios = self._buscar_proximos_horarios(
                medico_id=result[7],
                cliente_id=result[5]
            )

            # Enviar mensagem WhatsApp
            mensagem_enviada = await self._enviar_mensagem_falta(
                paciente_nome=result[3],
                paciente_telefone=result[4],
                medico_nome=result[6],
                data_hora_falta=result[1],
                proximos_horarios=proximos_horarios,
                cliente_id=result[5]
            )

            return {
                "sucesso": True,
                "mensagem": "Agendamento marcado como falta",
                "mensagem_whatsapp_enviada": mensagem_enviada,
                "proximos_horarios_sugeridos": proximos_horarios
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao marcar como falta: {e}", exc_info=True)
            return {
                "sucesso": False,
                "erro": str(e)
            }

    def _buscar_proximos_horarios(
        self,
        medico_id: int,
        cliente_id: int,
        quantidade: int = 3
    ) -> List[Dict]:
        """
        Busca próximos horários disponíveis na agenda do médico

        Args:
            medico_id: ID do médico
            cliente_id: ID do cliente
            quantidade: Quantidade de sugestões (padrão: 3)

        Returns:
            Lista de horários disponíveis
        """
        try:
            # Buscar configuração do médico
            config = self.db.execute(text("""
                SELECT
                    intervalo_consulta,
                    horario_inicio,
                    horario_fim,
                    dias_atendimento,
                    intervalo_almoco_inicio,
                    intervalo_almoco_fim
                FROM configuracoes_medico
                WHERE medico_id = :medico_id
                  AND cliente_id = :cliente_id
            """), {
                "medico_id": medico_id,
                "cliente_id": cliente_id
            }).fetchone()

            if not config:
                logger.warning(f"Configuração não encontrada para médico {medico_id}")
                return []

            intervalo_minutos = config[0]
            horario_inicio = config[1]
            horario_fim = config[2]
            dias_atendimento = config[3] if config[3] else [1, 2, 3, 4, 5]
            almoco_inicio = config[4]
            almoco_fim = config[5]

            # Gerar próximos horários disponíveis
            horarios_disponiveis = []
            data_atual = now_brazil().date()
            dias_checados = 0
            max_dias = 30  # Buscar nos próximos 30 dias

            while len(horarios_disponiveis) < quantidade and dias_checados < max_dias:
                data_check = data_atual + timedelta(days=dias_checados)
                dia_semana = data_check.isoweekday()  # 1=Monday, 7=Sunday

                # Verificar se é dia de atendimento
                if dia_semana in dias_atendimento:
                    # Gerar horários do dia
                    horarios_dia = self._gerar_horarios_dia(
                        data_check,
                        horario_inicio,
                        horario_fim,
                        intervalo_minutos,
                        almoco_inicio,
                        almoco_fim
                    )

                    # Filtrar apenas futuros
                    horarios_futuros = [
                        h for h in horarios_dia
                        if h > now_brazil()
                    ]

                    # Verificar disponibilidade
                    for horario in horarios_futuros:
                        if self._horario_disponivel(horario, medico_id, cliente_id):
                            horarios_disponiveis.append({
                                "data_hora": horario.strftime("%Y-%m-%d %H:%M:%S"),
                                "data_formatada": horario.strftime("%d/%m/%Y"),
                                "hora_formatada": horario.strftime("%H:%M"),
                                "dia_semana": self._nome_dia_semana(horario.weekday())
                            })

                            if len(horarios_disponiveis) >= quantidade:
                                break

                dias_checados += 1

            return horarios_disponiveis[:quantidade]

        except Exception as e:
            logger.error(f"Erro ao buscar próximos horários: {e}", exc_info=True)
            return []

    def _gerar_horarios_dia(
        self,
        data: datetime.date,
        hora_inicio: datetime.time,
        hora_fim: datetime.time,
        intervalo_minutos: int,
        almoco_inicio: Optional[datetime.time],
        almoco_fim: Optional[datetime.time]
    ) -> List[datetime]:
        """Gera lista de horários para um dia específico"""
        horarios = []

        hora_atual = datetime.combine(data, hora_inicio)
        hora_final = datetime.combine(data, hora_fim)

        while hora_atual < hora_final:
            # Verificar se não está no horário de almoço
            if almoco_inicio and almoco_fim:
                almoco_inicio_dt = datetime.combine(data, almoco_inicio)
                almoco_fim_dt = datetime.combine(data, almoco_fim)

                if not (almoco_inicio_dt <= hora_atual < almoco_fim_dt):
                    horarios.append(hora_atual)
            else:
                horarios.append(hora_atual)

            hora_atual += timedelta(minutes=intervalo_minutos)

        return horarios

    def _horario_disponivel(
        self,
        data_hora: datetime,
        medico_id: int,
        cliente_id: int
    ) -> bool:
        """Verifica se horário está disponível (sem agendamento ou bloqueio)"""
        # Verificar agendamentos existentes
        agendamento = self.db.execute(text("""
            SELECT id FROM agendamentos
            WHERE medico_id = :medico_id
              AND cliente_id = :cliente_id
              AND data_hora = :data_hora
              AND status IN ('confirmado', 'agendado')
        """), {
            "medico_id": medico_id,
            "cliente_id": cliente_id,
            "data_hora": data_hora
        }).fetchone()

        if agendamento:
            return False

        # Verificar bloqueios
        bloqueio = self.db.execute(text("""
            SELECT id FROM bloqueios_agenda
            WHERE medico_id = :medico_id
              AND :data_hora >= data_inicio
              AND :data_hora < data_fim
        """), {
            "medico_id": medico_id,
            "data_hora": data_hora
        }).fetchone()

        return bloqueio is None

    def _nome_dia_semana(self, dia: int) -> str:
        """Retorna nome do dia da semana (0=Monday)"""
        dias = {
            0: "Segunda",
            1: "Terça",
            2: "Quarta",
            3: "Quinta",
            4: "Sexta",
            5: "Sábado",
            6: "Domingo"
        }
        return dias.get(dia, "")

    async def _enviar_mensagem_falta(
        self,
        paciente_nome: str,
        paciente_telefone: str,
        medico_nome: str,
        data_hora_falta: datetime,
        proximos_horarios: List[Dict],
        cliente_id: int
    ) -> bool:
        """
        Envia mensagem empática via WhatsApp sobre a falta

        Args:
            paciente_nome: Nome do paciente
            paciente_telefone: Telefone do paciente
            medico_nome: Nome do médico
            data_hora_falta: Data/hora da consulta que faltou
            proximos_horarios: Lista de próximos horários disponíveis
            cliente_id: ID do cliente

        Returns:
            True se enviou com sucesso, False caso contrário
        """
        try:
            # Formatar data/hora da falta
            data_falta = data_hora_falta.strftime("%d/%m às %Hh%M")

            # Construir mensagem empática
            primeiro_nome = paciente_nome.split()[0]

            mensagem = f"Olá, {primeiro_nome}! 😊\n\n"
            mensagem += f"Percebemos que você não compareceu à sua consulta com {medico_nome} "
            mensagem += f"no dia {data_falta}. Esperamos que esteja tudo bem com você! 🙏\n\n"
            mensagem += "Caso tenha surgido algum imprevisto e deseje remarcar, estamos à disposição.\n\n"

            if proximos_horarios:
                mensagem += "📅 *Que tal reagendar para:*\n"
                for idx, horario in enumerate(proximos_horarios, 1):
                    mensagem += f"   {idx}. {horario['dia_semana']}, {horario['data_formatada']} às {horario['hora_formatada']}\n"

                mensagem += "\nPara confirmar, basta responder com o número da opção (1, 2 ou 3) "
                mensagem += "ou nos informe sua preferência.\n\n"
            else:
                mensagem += "Entre em contato conosco para reagendar sua consulta.\n\n"

            mensagem += "Estamos aqui para cuidar de você! 💙"

            # Enviar via WhatsApp API Oficial (Meta)
            from app.services.whatsapp_official_service import WhatsAppOfficialService

            whatsapp_service = WhatsAppOfficialService()

            # Buscar phone_number_id do cliente
            config = self.db.execute(text("""
                SELECT whatsapp_phone_number_id
                FROM configuracoes
                WHERE cliente_id = :cliente_id AND whatsapp_ativo = true
            """), {"cliente_id": cliente_id}).fetchone()

            phone_number_id = config[0] if config else None

            resultado = await whatsapp_service.send_text(
                to=paciente_telefone,
                message=mensagem,
                phone_number_id=phone_number_id
            )

            if resultado.success:
                logger.info(f"Mensagem de falta enviada para {paciente_nome} ({paciente_telefone})")
                return True
            else:
                logger.warning(f"Falha ao enviar mensagem de falta para {paciente_nome}: {resultado.error}")
                return False

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de falta: {e}", exc_info=True)
            return False


# Instância global do serviço
_falta_service_instance = None

def get_falta_service(db: Session) -> FaltaService:
    """Factory para obter instância do serviço"""
    return FaltaService(db)
