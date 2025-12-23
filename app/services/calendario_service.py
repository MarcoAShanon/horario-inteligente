# app/services/calendario_service.py
# Serviço de Calendário Próprio - substitui Google Calendar
# Marco - Sistema Horário Inteligente

from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
import logging

from ..database import get_db
from ..models.medico import Medico

logger = logging.getLogger(__name__)

class CalendarioService:
    def __init__(self):
        self.timezone_br = 'America/Sao_Paulo'
    
    def verificar_disponibilidade_medico(
        self, 
        medico_id: int, 
        data_consulta: datetime,
        duracao_minutos: int = 30
    ) -> Dict[str, Any]:
        """
        Verifica se médico está disponível em data/hora específica
        """
        try:
            db = next(get_db())
            
            # 1. Verificar se é dia de atendimento
            dia_semana = data_consulta.weekday() + 1  # Python: 0=Segunda, SQL: 1=Segunda
            
            horario_atendimento = db.execute(text("""
                SELECT hora_inicio, hora_fim 
                FROM horarios_atendimento 
                WHERE medico_id = :medico_id 
                AND dia_semana = :dia_semana 
                AND ativo = true
                AND :hora_consulta BETWEEN hora_inicio AND hora_fim
            """), {
                'medico_id': medico_id,
                'dia_semana': dia_semana,
                'hora_consulta': data_consulta.time()
            }).fetchone()
            
            if not horario_atendimento:
                return {
                    'disponivel': False,
                    'motivo': 'Médico não atende neste dia/horário'
                }
            
            # 2. Verificar bloqueios
            data_fim_consulta = data_consulta + timedelta(minutes=duracao_minutos)
            
            bloqueio = db.execute(text("""
                SELECT motivo, tipo 
                FROM bloqueios_agenda 
                WHERE medico_id = :medico_id 
                AND ativo = true
                AND (
                    (:data_inicio BETWEEN data_inicio AND data_fim) OR
                    (:data_fim BETWEEN data_inicio AND data_fim) OR
                    (data_inicio BETWEEN :data_inicio AND :data_fim)
                )
            """), {
                'medico_id': medico_id,
                'data_inicio': data_consulta,
                'data_fim': data_fim_consulta
            }).fetchone()
            
            if bloqueio:
                return {
                    'disponivel': False,
                    'motivo': f'Horário bloqueado: {bloqueio.motivo}'
                }

            # 3. Verificar agendamentos existentes
            agendamento_conflito = db.execute(text("""
                SELECT COUNT(*) as total
                FROM agendamentos
                WHERE medico_id = :medico_id
                AND status IN ('agendado', 'confirmado')
                AND (
                    (:data_inicio >= data_hora AND :data_inicio < data_hora + INTERVAL '1 minute' * :duracao) OR
                    (:data_fim > data_hora AND :data_inicio < data_hora + INTERVAL '1 minute' * :duracao)
                )
            """), {
                'medico_id': medico_id,
                'data_inicio': data_consulta,
                'data_fim': data_fim_consulta,
                'duracao': duracao_minutos
            }).fetchone()
            if agendamento_conflito.total > 0:
                return {
                    'disponivel': False,
                    'motivo': 'Horário já agendado'
                }
            
            # 4. Verificar antecedência mínima
            config = db.execute(text("""
                SELECT antecedencia_minima, antecedencia_maxima
                FROM configuracoes_medico
                WHERE medico_id = :medico_id
            """), {'medico_id': medico_id}).fetchone()

            agora = datetime.now()
            if config:
                # antecedencia_minima está em minutos
                min_antecedencia = agora + timedelta(minutes=config.antecedencia_minima)
                # antecedencia_maxima está em horas
                max_antecedencia = agora + timedelta(hours=config.antecedencia_maxima)

                if data_consulta < min_antecedencia:
                    return {
                        'disponivel': False,
                        'motivo': f'Agendamento deve ser feito com pelo menos {config.antecedencia_minima} minutos de antecedência'
                    }

                if data_consulta > max_antecedencia:
                    horas = config.antecedencia_maxima
                    dias = horas // 24
                    return {
                        'disponivel': False,
                        'motivo': f'Agendamento não pode ser feito com mais de {dias} dias de antecedência'
                    }
            
            return {
                'disponivel': True,
                'motivo': 'Horário disponível'
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {str(e)}")
            return {
                'disponivel': False,
                'motivo': f'Erro interno: {str(e)}'
            }
    
    def listar_horarios_disponiveis(
        self, 
        medico_id: int, 
        data_inicio: datetime, 
        data_fim: datetime,
        duracao_consulta: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Lista todos os horários disponíveis do médico em um período
        """
        try:
            db = next(get_db())
            
            # Buscar configurações do médico
            config = db.execute(text("""
                SELECT intervalo_consulta, tempo_antes_consulta
                FROM configuracoes_medico
                WHERE medico_id = :medico_id
            """), {'medico_id': medico_id}).fetchone()

            if config:
                duracao_consulta = config.intervalo_consulta or duracao_consulta

            # Para horários de hora em hora, não usamos intervalo entre consultas
            intervalo = 0
            
            # Buscar horários de atendimento
            horarios_base = db.execute(text("""
                SELECT dia_semana, hora_inicio, hora_fim
                FROM horarios_atendimento 
                WHERE medico_id = :medico_id AND ativo = true
                ORDER BY dia_semana, hora_inicio
            """), {'medico_id': medico_id}).fetchall()
            
            horarios_disponiveis = []
            data_atual = data_inicio.date()
            
            while data_atual <= data_fim.date():
                dia_semana = data_atual.weekday() + 1
                
                # Verificar se médico atende neste dia
                horarios_dia = [h for h in horarios_base if h.dia_semana == dia_semana]
                
                for horario in horarios_dia:
                    # Gerar slots de horário
                    hora_atual = datetime.combine(data_atual, horario.hora_inicio)
                    hora_fim_periodo = datetime.combine(data_atual, horario.hora_fim)
                    
                    while hora_atual + timedelta(minutes=duracao_consulta) <= hora_fim_periodo:
                        # Verificar se este slot está disponível
                        disponibilidade = self.verificar_disponibilidade_medico(
                            medico_id, hora_atual, duracao_consulta
                        )
                        
                        if disponibilidade['disponivel']:
                            horarios_disponiveis.append({
                                'data_hora': hora_atual,
                                'data_formatada': hora_atual.strftime('%d/%m/%Y'),
                                'hora_formatada': hora_atual.strftime('%H:%M'),
                                'dia_semana': self._get_nome_dia_semana(hora_atual.weekday()),
                                'duracao_minutos': duracao_consulta
                            })
                        
                        # Próximo slot
                        hora_atual += timedelta(minutes=duracao_consulta + intervalo)
                
                data_atual += timedelta(days=1)
            
            return horarios_disponiveis
            
        except Exception as e:
            logger.error(f"Erro ao listar horários disponíveis: {str(e)}")
            return []
    
    def criar_agendamento(
        self, 
        medico_id: int,
        dados_agendamento: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cria um novo agendamento
        """
        try:
            db = next(get_db())
            
            data_agendamento = dados_agendamento['data_agendamento']
            duracao = dados_agendamento.get('duracao_minutos', 30)
            
            # Verificar disponibilidade uma última vez
            disponibilidade = self.verificar_disponibilidade_medico(
                medico_id, data_agendamento, duracao
            )
            
            if not disponibilidade['disponivel']:
                return {
                    'success': False,
                    'error': disponibilidade['motivo']
                }
            
        # Criar agendamento
            result = db.execute(text("""
                INSERT INTO agendamentos (
                    medico_id, paciente_id, data_hora, status, tipo_atendimento,
                    valor_consulta, motivo_consulta, criado_em, atualizado_em
                ) VALUES (
                    :medico_id, :paciente_id, :data_hora, 'agendado', :tipo_atendimento,
                    :valor_consulta, :motivo_consulta, NOW(), NOW()
                ) RETURNING id
            """), {
                'medico_id': medico_id,
                'paciente_id': dados_agendamento['paciente_id'],
                'data_hora': dados_agendamento['data_agendamento'],
                'tipo_atendimento': dados_agendamento.get('tipo_atendimento', 'consulta'),
                'valor_consulta': dados_agendamento.get('valor_consulta'),
                'motivo_consulta': dados_agendamento.get('motivo_consulta')
            })
            
            agendamento_id = result.fetchone()[0]
            db.commit()
            
            return {
                'success': True,
                'agendamento_id': agendamento_id,
                'message': 'Agendamento criado com sucesso'
            }      
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao criar agendamento: {str(e)}")
            return {
                'success': False,
                'error': f'Erro ao criar agendamento: {str(e)}'
            }
    
    def listar_agendamentos_medico(
        self, 
        medico_id: int, 
        data_inicio: datetime = None,
        data_fim: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Lista agendamentos do médico
        """
        try:
            db = next(get_db())
            
            if not data_inicio:
                data_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if not data_fim:
                data_fim = data_inicio + timedelta(days=7)
            
            agendamentos = db.execute(text("""
                SELECT 
                    a.id,
                    a.paciente_nome,
                    a.paciente_telefone,
                    a.data_agendamento,
                    a.duracao_minutos,
                    a.status,
                    a.observacoes,
                    c.nome as convenio_nome
                FROM agendamentos a
                LEFT JOIN convenios c ON a.convenio_id = c.id
                WHERE a.medico_id = :medico_id
                AND a.data_agendamento BETWEEN :data_inicio AND :data_fim
                AND a.status IN ('agendado', 'confirmado')
                ORDER BY a.data_agendamento
            """), {
                'medico_id': medico_id,
                'data_inicio': data_inicio,
                'data_fim': data_fim
            }).fetchall()
            
            resultado = []
            for ag in agendamentos:
                resultado.append({
                    'id': ag.id,
                    'paciente_nome': ag.paciente_nome,
                    'paciente_telefone': ag.paciente_telefone,
                    'data_agendamento': ag.data_agendamento,
                    'data_formatada': ag.data_agendamento.strftime('%d/%m/%Y'),
                    'hora_formatada': ag.data_agendamento.strftime('%H:%M'),
                    'duracao_minutos': ag.duracao_minutos,
                    'status': ag.status,
                    'convenio': ag.convenio_nome,
                    'observacoes': ag.observacoes
                })
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao listar agendamentos: {str(e)}")
            return []
    
    def _get_nome_dia_semana(self, weekday: int) -> str:
        """Converte número do dia da semana para nome"""
        nomes = {
            0: 'Segunda-feira',
            1: 'Terça-feira', 
            2: 'Quarta-feira',
            3: 'Quinta-feira',
            4: 'Sexta-feira',
            5: 'Sábado',
            6: 'Domingo'
        }
        return nomes.get(weekday, 'Dia inválido')

# Instância global do serviço
calendario_service = CalendarioService()
