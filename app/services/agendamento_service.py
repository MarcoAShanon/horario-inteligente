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
        duracao_minutos: int = 30,
        excluir_agendamento_id: int = None
    ) -> bool:
        """
        Verifica se o médico está disponível no horário solicitado.
        Considera a duração real de cada agendamento existente.

        Args:
            medico_id: ID do médico
            data_hora: Data/hora de início do novo agendamento
            duracao_minutos: Duração do novo agendamento
            excluir_agendamento_id: ID de agendamento a excluir da verificação (para reagendamentos)
        """
        # Verificar se médico existe e está ativo
        medico = self.db.query(Medico).filter(
            Medico.id == medico_id,
            Medico.ativo == True
        ).first()

        if not medico:
            return False

        # Usar SQL para verificar conflito considerando duração real de cada agendamento
        # Conflito ocorre quando: novo_inicio < existente_fim AND novo_fim > existente_inicio
        query = """
            SELECT id FROM agendamentos
            WHERE medico_id = :medico_id
            AND status NOT IN ('cancelado', 'faltou')
            AND (
                -- Novo agendamento começa antes do existente terminar
                :novo_inicio < (data_hora + (COALESCE(duracao_minutos, 30) || ' minutes')::interval)
                AND
                -- Novo agendamento termina depois do existente começar
                (:novo_inicio + (:duracao || ' minutes')::interval) > data_hora
            )
        """

        params = {
            "medico_id": medico_id,
            "novo_inicio": data_hora,
            "duracao": duracao_minutos
        }

        # Se estamos reagendando, excluir o próprio agendamento da verificação
        if excluir_agendamento_id:
            query = query.replace(
                "WHERE medico_id = :medico_id",
                "WHERE medico_id = :medico_id AND id != :excluir_id"
            )
            params["excluir_id"] = excluir_agendamento_id

        result = self.db.execute(text(query), params).fetchone()

        return result is None

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

        # Criar datetime com timezone de Brasília (importante para comparação com banco)
        import pytz
        tz_brazil = pytz.timezone('America/Sao_Paulo')

        hora_atual = tz_brazil.localize(
            datetime.combine(data_consulta, datetime.min.time().replace(hour=hora_inicio, minute=min_inicio))
        )
        hora_final = tz_brazil.localize(
            datetime.combine(data_consulta, datetime.min.time().replace(hour=hora_fim, minute=min_fim))
        )

        # Gerar slots de 30 em 30 minutos (verificação usa duração solicitada)
        while hora_atual < hora_final:
            if self.verificar_disponibilidade_medico(medico_id, hora_atual, duracao_minutos):
                horarios_disponiveis.append(hora_atual.strftime('%H:%M'))
            hora_atual += timedelta(minutes=30)  # Slots de 30 em 30, mas verificação considera duração real

        return horarios_disponiveis
