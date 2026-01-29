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
        # Status que LIBERAM o horário: cancelado, faltou, remarcado
        query = """
            SELECT id FROM agendamentos
            WHERE medico_id = :medico_id
            AND status NOT IN ('cancelado', 'faltou', 'remarcado')
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
        """
        Obtém horários disponíveis de um médico em uma data específica.
        Busca configuração da tabela configuracoes_medico (horarios_por_dia).
        """
        import pytz
        import json

        # Buscar médico
        medico = self.db.query(Medico).filter(
            Medico.id == medico_id,
            Medico.ativo == True
        ).first()

        if not medico:
            return []

        # Buscar configuração do médico na tabela configuracoes_medico
        config_result = self.db.execute(text("""
            SELECT horarios_por_dia, intervalo_consulta,
                   intervalo_almoco_inicio, intervalo_almoco_fim
            FROM configuracoes_medico
            WHERE medico_id = :medico_id AND ativo = true
        """), {"medico_id": medico_id}).fetchone()

        if not config_result or not config_result[0]:
            # Fallback: tentar usar medico.horarios_atendimento se existir
            if medico.horarios_atendimento:
                return self._obter_horarios_legado(medico, data_consulta, duracao_minutos)
            return []

        horarios_por_dia = config_result[0]
        intervalo_consulta = config_result[1] or 30
        almoco_inicio_str = config_result[2]
        almoco_fim_str = config_result[3]

        # Parse JSON se necessário
        if isinstance(horarios_por_dia, str):
            horarios_por_dia = json.loads(horarios_por_dia)

        # Mapear dia da semana Python para chave do JSON
        # Python weekday(): 0=Segunda, ..., 6=Domingo
        # JSON horarios_por_dia: "0"=Domingo, "1"=Segunda, ..., "6"=Sábado
        dia_semana_python = data_consulta.weekday()
        dia_semana_json = str((dia_semana_python + 1) % 7)  # Converte: 0→1, 1→2, ..., 5→6, 6→0

        # Verificar se há configuração para este dia
        if dia_semana_json not in horarios_por_dia:
            return []

        config_dia = horarios_por_dia[dia_semana_json]

        # Verificar se está ativo neste dia
        if not config_dia.get('ativo', False):
            return []

        # Obter horários do dia
        inicio_str = config_dia.get('inicio', '08:00')
        fim_str = config_dia.get('fim', '18:00')

        # Horário de almoço específico do dia (se configurado)
        almoco_inicio_dia = config_dia.get('almoco_inicio') or almoco_inicio_str
        almoco_fim_dia = config_dia.get('almoco_fim') or almoco_fim_str
        sem_almoco = config_dia.get('sem_almoco', False)

        hora_inicio, min_inicio = map(int, inicio_str.split(':'))
        hora_fim, min_fim = map(int, fim_str.split(':'))

        # Criar datetime com timezone de Brasília
        tz_brazil = pytz.timezone('America/Sao_Paulo')

        hora_atual = tz_brazil.localize(
            datetime.combine(data_consulta, datetime.min.time().replace(hour=hora_inicio, minute=min_inicio))
        )
        hora_final = tz_brazil.localize(
            datetime.combine(data_consulta, datetime.min.time().replace(hour=hora_fim, minute=min_fim))
        )

        # Configurar intervalo de almoço
        almoco_inicio = None
        almoco_fim = None
        if not sem_almoco and almoco_inicio_dia and almoco_fim_dia:
            try:
                h_almoco_ini, m_almoco_ini = map(int, almoco_inicio_dia.split(':'))
                h_almoco_fim, m_almoco_fim = map(int, almoco_fim_dia.split(':'))
                almoco_inicio = tz_brazil.localize(
                    datetime.combine(data_consulta, datetime.min.time().replace(hour=h_almoco_ini, minute=m_almoco_ini))
                )
                almoco_fim = tz_brazil.localize(
                    datetime.combine(data_consulta, datetime.min.time().replace(hour=h_almoco_fim, minute=m_almoco_fim))
                )
            except (ValueError, AttributeError):
                pass

        # Buscar bloqueios de agenda para o médico nesta data
        bloqueios = self._obter_bloqueios_dia(medico_id, data_consulta, tz_brazil)

        # Gerar slots usando o intervalo configurado do médico
        horarios_disponiveis = []

        # Se for hoje, obter hora atual para filtrar horários que já passaram
        agora = datetime.now(tz_brazil)
        eh_hoje = data_consulta == agora.date()

        while hora_atual < hora_final:
            # Se for hoje, pular horários que já passaram (com margem de 30 min)
            if eh_hoje and hora_atual <= agora + timedelta(minutes=30):
                hora_atual += timedelta(minutes=intervalo_consulta)
                continue

            # Verificar se está no horário de almoço
            if almoco_inicio and almoco_fim:
                if almoco_inicio <= hora_atual < almoco_fim:
                    hora_atual += timedelta(minutes=intervalo_consulta)
                    continue

            # Verificar se está em período bloqueado
            if self._horario_bloqueado(hora_atual, duracao_minutos, bloqueios):
                hora_atual += timedelta(minutes=intervalo_consulta)
                continue

            # Verificar disponibilidade (sem conflito com outros agendamentos)
            if self.verificar_disponibilidade_medico(medico_id, hora_atual, duracao_minutos):
                horarios_disponiveis.append(hora_atual.strftime('%H:%M'))

            hora_atual += timedelta(minutes=intervalo_consulta)

        return horarios_disponiveis

    def _obter_bloqueios_dia(self, medico_id: int, data_consulta: date, tz_brazil) -> List[Dict]:
        """Busca bloqueios de agenda ativos para o médico na data especificada."""
        # Definir início e fim do dia
        inicio_dia = datetime.combine(data_consulta, datetime.min.time())
        fim_dia = datetime.combine(data_consulta, datetime.max.time())

        result = self.db.execute(text("""
            SELECT data_inicio, data_fim, motivo, tipo
            FROM bloqueios_agenda
            WHERE medico_id = :medico_id
            AND ativo = true
            AND (
                -- Bloqueio começa antes do fim do dia E termina depois do início do dia
                data_inicio <= :fim_dia AND data_fim >= :inicio_dia
            )
        """), {
            "medico_id": medico_id,
            "inicio_dia": inicio_dia,
            "fim_dia": fim_dia
        }).fetchall()

        bloqueios = []
        for row in result:
            bloqueios.append({
                "inicio": tz_brazil.localize(row[0]) if row[0].tzinfo is None else row[0],
                "fim": tz_brazil.localize(row[1]) if row[1].tzinfo is None else row[1],
                "motivo": row[2],
                "tipo": row[3]
            })

        return bloqueios

    def _horario_bloqueado(self, hora_inicio: datetime, duracao_minutos: int, bloqueios: List[Dict]) -> bool:
        """Verifica se um horário específico está dentro de um período bloqueado."""
        hora_fim = hora_inicio + timedelta(minutes=duracao_minutos)

        for bloqueio in bloqueios:
            # Conflito: horário começa antes do bloqueio terminar E horário termina depois do bloqueio começar
            if hora_inicio < bloqueio["fim"] and hora_fim > bloqueio["inicio"]:
                return True

        return False

    def _obter_horarios_legado(
        self,
        medico: Medico,
        data_consulta: date,
        duracao_minutos: int = 30
    ) -> List[str]:
        """Fallback: buscar horários do campo medico.horarios_atendimento (formato antigo)."""
        import pytz

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

        tz_brazil = pytz.timezone('America/Sao_Paulo')

        hora_atual = tz_brazil.localize(
            datetime.combine(data_consulta, datetime.min.time().replace(hour=hora_inicio, minute=min_inicio))
        )
        hora_final = tz_brazil.localize(
            datetime.combine(data_consulta, datetime.min.time().replace(hour=hora_fim, minute=min_fim))
        )

        while hora_atual < hora_final:
            if self.verificar_disponibilidade_medico(medico.id, hora_atual, duracao_minutos):
                horarios_disponiveis.append(hora_atual.strftime('%H:%M'))
            hora_atual += timedelta(minutes=30)

        return horarios_disponiveis
