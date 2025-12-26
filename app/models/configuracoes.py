# app/models/configuracoes.py

from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class ConfiguracoesMedico(Base):
    __tablename__ = "configuracoes_medico"
    __table_args__ = {'extend_existing': True}    
    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False, unique=True)
    
    # Configurações de intervalo
    intervalo_consulta = Column(Integer, default=30, comment="Duração da consulta em minutos")
    horario_inicio = Column(String(5), default="08:00", comment="Horário de início do atendimento")
    horario_fim = Column(String(5), default="18:00", comment="Horário de fim do atendimento")
    dias_atendimento = Column(Text, comment="JSON com dias da semana [1,2,3,4,5] seg-sex")
    horarios_por_dia = Column(Text, nullable=True, comment="JSON com horários específicos por dia da semana")
    
    # Intervalo de almoço/pausa
    intervalo_almoco_inicio = Column(String(5), nullable=True, comment="Início do intervalo de almoço")
    intervalo_almoco_fim = Column(String(5), nullable=True, comment="Fim do intervalo de almoço")
    
    # Configurações avançadas
    tempo_antes_consulta = Column(Integer, default=5, comment="Tempo de preparação antes da consulta (min)")
    consultas_simultaneas = Column(Integer, default=1, comment="Quantas consultas simultâneas permitir")
    
    # Configurações de agendamento
    antecedencia_minima = Column(Integer, default=60, comment="Antecedência mínima para agendamento (min)")
    antecedencia_maxima = Column(Integer, default=8760, comment="Antecedência máxima para agendamento (horas)")
    permite_reagendamento = Column(Boolean, default=True, comment="Permite reagendamento pelo paciente")
    limite_reagendamentos = Column(Integer, default=2, comment="Limite de reagendamentos por paciente")
    
    # Notificações
    lembrete_24h = Column(Boolean, default=True, comment="Enviar lembrete 24h antes")
    lembrete_2h = Column(Boolean, default=True, comment="Enviar lembrete 2h antes")
    confirmacao_automatica = Column(Boolean, default=False, comment="Confirmar automaticamente agendamentos")
    
    # Status
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    medico = relationship("Medico", back_populates="configuracoes")
    
    def __repr__(self):
        return f"<ConfiguracoesMedico(medico_id={self.medico_id}, intervalo={self.intervalo_consulta}min)>"


class BloqueioAgenda(Base):
    """
    Tabela para gerenciar bloqueios específicos na agenda
    (férias, consultas particulares, emergências, etc.)
    """
    __tablename__ = "bloqueios_agenda"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    
    # Data e horário do bloqueio
    data_inicio = Column(DateTime, nullable=False, comment="Data/hora início do bloqueio")
    data_fim = Column(DateTime, nullable=False, comment="Data/hora fim do bloqueio")
    
    # Detalhes do bloqueio
    tipo_bloqueio = Column(String(50), nullable=False, comment="ferias, emergencia, particular, manutencao")
    motivo = Column(String(200), nullable=True, comment="Descrição do motivo")
    recorrente = Column(Boolean, default=False, comment="Se é um bloqueio recorrente")
    
    # Configurações
    bloqueia_novos_agendamentos = Column(Boolean, default=True)
    cancela_agendamentos_existentes = Column(Boolean, default=False)
    notificar_pacientes = Column(Boolean, default=True)
    
    # Status
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, comment="ID do usuário que criou o bloqueio")
    
    # Relacionamentos
    medico = relationship("Medico")
    
    def __repr__(self):
        return f"<BloqueioAgenda(medico_id={self.medico_id}, tipo={self.tipo_bloqueio})>"


class HorarioEspecial(Base):
    """
    Tabela para horários especiais/personalizados 
    (plantões, consultas extras, horários diferenciados)
    """
    __tablename__ = "horarios_especiais"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    
    # Data específica
    data = Column(String(10), nullable=False, comment="Data no formato YYYY-MM-DD")
    
    # Horários especiais para esta data
    horario_inicio = Column(String(5), nullable=True, comment="Horário início diferente do padrão")
    horario_fim = Column(String(5), nullable=True, comment="Horário fim diferente do padrão")
    intervalo_consulta = Column(Integer, nullable=True, comment="Intervalo diferente do padrão")
    
    # Configurações especiais
    valor_consulta_diferenciado = Column(Integer, nullable=True, comment="Valor em centavos se diferente")
    tipo_atendimento = Column(String(50), default="normal", comment="normal, plantao, emergencia, particular")
    observacoes = Column(Text, nullable=True)
    
    # Status
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    medico = relationship("Medico")
    
    def __repr__(self):
        return f"<HorarioEspecial(medico_id={self.medico_id}, data={self.data})>"


# Atualizar o modelo Medico para incluir os relacionamentos
# Adicionar ao arquivo app/models/medicos.py:

"""
# Adicionar estas linhas ao modelo Medico existente:

configuracoes = relationship("ConfiguracoesMedico", back_populates="medico", uselist=False)
bloqueios = relationship("BloqueioAgenda", back_populates="medico")
horarios_especiais = relationship("HorarioEspecial", back_populates="medico")
"""
