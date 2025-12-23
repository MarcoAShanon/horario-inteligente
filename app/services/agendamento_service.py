"""
Serviço de Agendamentos
Sistema de agendamento médico SaaS - Pro-Saúde
Desenvolvido por Marco
"""

from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text

from app.models.agendamento import Agendamento
from app.models.medico import Medico
from app.models.paciente import Paciente


class AgendamentoService:
    """Serviço para gerenciamento de agendamentos médicos."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def verificar_disponibilidade_medico(
        self,
        medico_id: int,
        data_hora: datetime,
        duracao_minutos: int = 30
    ) -> bool:
        """Verifica se o médico está disponível no horário solicitado."""
        # Verificar se médico existe e está ativo
        medico = self.db.query(Medico).filter(
            Medico.id == medico_id,
            Medico.ativo == True
        ).first()

        if not medico:
            return False

        # Verificar se existe agendamento no horário
        hora_fim = data_hora + timedelta(minutes=duracao_minutos)

        agendamento_conflitante = self.db.query(Agendamento).filter(
            Agendamento.medico_id == medico_id,
            Agendamento.status.in_(['agendado', 'confirmado']),
            or_(
                # Novo agendamento começa durante um existente
                and_(
                    Agendamento.data_hora <= data_hora,
                    Agendamento.data_hora + timedelta(minutes=duracao_minutos) > data_hora
                ),
                # Novo agendamento termina durante um existente
                and_(
                    Agendamento.data_hora < hora_fim,
                    Agendamento.data_hora + timedelta(minutes=duracao_minutos) >= hora_fim
                ),
                # Novo agendamento engloba um existente
                and_(
                    Agendamento.data_hora >= data_hora,
                    Agendamento.data_hora < hora_fim
                )
            )
        ).first()

        return agendamento_conflitante is None

    def obter_horarios_disponiveis(
        self,
        medico_id: int,
        data_consulta: date,
        duracao_minutos: int = 30
    ) -> List[str]:
        """Obtém horários disponíveis de um médico em uma data específica."""
        # Buscar médico
        medico = self.db.query(Medico).filter(
            Medico.id == medico_id,
            Medico.ativo == True
        ).first()

        if not medico or not medico.horarios_atendimento:
            return []

        # Obter dia da semana (0=segunda, 6=domingo)
        dia_semana = data_consulta.weekday()
        dias_map = {
            0: "segunda",
            1: "terca",
            2: "quarta",
            3: "quinta",
            4: "sexta",
            5: "sabado",
            6: "domingo"
        }

        dia_nome = dias_map.get(dia_semana)
        if not dia_nome or dia_nome not in medico.horarios_atendimento:
            return []

        horario_dia = medico.horarios_atendimento[dia_nome]
        if not horario_dia.get('ativo', False):
            return []

        # Gerar slots de horários
        horarios_disponiveis = []
        inicio_str = horario_dia.get('inicio', '08:00')
        fim_str = horario_dia.get('fim', '18:00')

        hora_inicio, min_inicio = map(int, inicio_str.split(':'))
        hora_fim, min_fim = map(int, fim_str.split(':'))

        hora_atual = datetime.combine(data_consulta, datetime.min.time().replace(hour=hora_inicio, minute=min_inicio))
        hora_final = datetime.combine(data_consulta, datetime.min.time().replace(hour=hora_fim, minute=min_fim))

        # Gerar slots de 30 em 30 minutos
        while hora_atual < hora_final:
            if self.verificar_disponibilidade_medico(medico_id, hora_atual, duracao_minutos):
                horarios_disponiveis.append(hora_atual.strftime('%H:%M'))
            hora_atual += timedelta(minutes=duracao_minutos)

        return horarios_disponiveis
