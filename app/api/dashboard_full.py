"""
Rotas da API para dashboard médico
Arquivo: app/api/dashboard.py
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import List, Optional
from pydantic import BaseModel

from app.database import SessionLocal
from app.models.medico import Medico
from app.models.paciente import Paciente
from app.models.agendamento import Agendamento
from app.models.horario_atendimento import HorarioAtendimento
from app.api.auth import get_current_medico

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AgendamentoResponse(BaseModel):
    id: int
    paciente_nome: str
    paciente_telefone: str
    data_hora: datetime
    status: str
    tipo_atendimento: str
    observacoes: Optional[str]

class DashboardStats(BaseModel):
    total_pacientes: int
    consultas_hoje: int
    consultas_semana: int
    atendimentos_realizados: int  # NOVO: consultas concluídas (excluindo faltas/cancelamentos)
    faltas_sem_aviso: int  # NOVO: total de faltas
    cancelamentos: int  # NOVO: total de cancelamentos
    taxa_comparecimento: float  # NOVO: % de comparecimento (realizados / total agendado)
    proxima_consulta: Optional[dict]
    taxa_ocupacao: float

class HorarioConfig(BaseModel):
    dia_semana: int
    inicio: str
    fim: str
    ativo: bool

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    medico: Medico = Depends(get_current_medico),
    db: Session = Depends(get_db)
):
    """Obtém estatísticas do dashboard com métricas de comparecimento"""
    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)

    # Total de pacientes do médico
    total_pacientes = db.query(func.count(func.distinct(Agendamento.paciente_id))).filter(
        Agendamento.medico_id == medico.id
    ).scalar()

    # Consultas hoje (futuras)
    consultas_hoje = db.query(func.count(Agendamento.id)).filter(
        Agendamento.medico_id == medico.id,
        func.date(Agendamento.data_hora) == hoje,
        Agendamento.status.in_(['confirmado', 'em_atendimento'])
    ).scalar()

    # Consultas na semana (futuras + em andamento)
    consultas_semana = db.query(func.count(Agendamento.id)).filter(
        Agendamento.medico_id == medico.id,
        func.date(Agendamento.data_hora) >= inicio_semana,
        func.date(Agendamento.data_hora) <= fim_semana,
        Agendamento.status.in_(['confirmado', 'em_atendimento'])
    ).scalar()

    # NOVO: Atendimentos realizados (concluídos com sucesso)
    atendimentos_realizados = db.query(func.count(Agendamento.id)).filter(
        Agendamento.medico_id == medico.id,
        func.date(Agendamento.data_hora) >= inicio_semana,
        func.date(Agendamento.data_hora) <= fim_semana,
        Agendamento.status == 'concluido'
    ).scalar()

    # NOVO: Faltas sem aviso
    faltas = db.query(func.count(Agendamento.id)).filter(
        Agendamento.medico_id == medico.id,
        func.date(Agendamento.data_hora) >= inicio_semana,
        func.date(Agendamento.data_hora) <= fim_semana,
        Agendamento.status == 'faltou'
    ).scalar()

    # NOVO: Cancelamentos
    cancelamentos = db.query(func.count(Agendamento.id)).filter(
        Agendamento.medico_id == medico.id,
        func.date(Agendamento.data_hora) >= inicio_semana,
        func.date(Agendamento.data_hora) <= fim_semana,
        Agendamento.status == 'cancelado'
    ).scalar()

    # NOVO: Taxa de comparecimento
    # Total agendado (passados) = realizados + faltas
    total_agendado_passado = atendimentos_realizados + faltas
    taxa_comparecimento = 0
    if total_agendado_passado > 0:
        taxa_comparecimento = (atendimentos_realizados / total_agendado_passado) * 100

    # Próxima consulta
    proxima = db.query(Agendamento).join(Paciente).filter(
        Agendamento.medico_id == medico.id,
        Agendamento.data_hora >= datetime.now(),
        Agendamento.status.in_(['confirmado', 'confirmada', 'agendada'])
    ).order_by(Agendamento.data_hora).first()

    proxima_consulta = None
    if proxima:
        proxima_consulta = {
            "id": proxima.id,
            "paciente": proxima.paciente.nome,
            "data_hora": proxima.data_hora.isoformat(),
            "tipo": proxima.tipo_atendimento
        }

    # Taxa de ocupação (simplificada)
    total_horarios = 8 * 5  # 8 horas por dia, 5 dias
    taxa_ocupacao = (consultas_semana / total_horarios) * 100 if total_horarios > 0 else 0

    return DashboardStats(
        total_pacientes=total_pacientes or 0,
        consultas_hoje=consultas_hoje or 0,
        consultas_semana=consultas_semana or 0,
        atendimentos_realizados=atendimentos_realizados or 0,
        faltas_sem_aviso=faltas or 0,
        cancelamentos=cancelamentos or 0,
        taxa_comparecimento=round(taxa_comparecimento, 2),
        proxima_consulta=proxima_consulta,
        taxa_ocupacao=round(taxa_ocupacao, 2)
    )

@router.get("/agenda", response_model=List[AgendamentoResponse])
async def get_agenda(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    medico: Medico = Depends(get_current_medico),
    db: Session = Depends(get_db)
):
    """Obtém agenda do médico"""
    
    # Datas padrão: próximos 7 dias
    if not data_inicio:
        data_inicio = date.today()
    if not data_fim:
        data_fim = data_inicio + timedelta(days=7)
    
    agendamentos = db.query(Agendamento).join(Paciente).filter(
        Agendamento.medico_id == medico.id,
        func.date(Agendamento.data_hora) >= data_inicio,
        func.date(Agendamento.data_hora) <= data_fim
    ).order_by(Agendamento.data_hora).all()
    
    return [
        AgendamentoResponse(
            id=a.id,
            paciente_nome=a.paciente.nome,
            paciente_telefone=a.paciente.telefone,
            data_hora=a.data_hora,
            status=a.status,
            tipo_atendimento=a.tipo_atendimento,
            observacoes=a.observacoes
        )
        for a in agendamentos
    ]

@router.get("/agenda/hoje")
async def get_agenda_hoje(
    medico: Medico = Depends(get_current_medico),
    db: Session = Depends(get_db)
):
    """Obtém agenda de hoje"""
    hoje = date.today()

    # IMPORTANTE: Ocultar cancelado, remarcado, faltou (ficam no banco para estatísticas)
    agendamentos = db.query(Agendamento).join(Paciente).filter(
        Agendamento.medico_id == medico.id,
        func.date(Agendamento.data_hora) == hoje,
        Agendamento.status.notin_(['cancelado', 'remarcado', 'faltou'])
    ).order_by(Agendamento.data_hora).all()
    
    return [
        {
            "id": a.id,
            "horario": a.data_hora.strftime("%H:%M"),
            "paciente": a.paciente.nome,
            "telefone": a.paciente.telefone,
            "status": a.status,
            "tipo": a.tipo_atendimento
        }
        for a in agendamentos
    ]

@router.put("/agendamento/{agendamento_id}/status")
async def update_status_agendamento(
    agendamento_id: int,
    status: str,
    medico: Medico = Depends(get_current_medico),
    db: Session = Depends(get_db)
):
    """Atualiza status de um agendamento"""
    
    agendamento = db.query(Agendamento).filter(
        Agendamento.id == agendamento_id,
        Agendamento.medico_id == medico.id
    ).first()
    
    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    
    status_validos = ['agendado', 'agendada', 'confirmado', 'confirmada', 'cancelado', 'cancelada', 'em_atendimento', 'concluido', 'concluida', 'realizado', 'realizada', 'faltou', 'remarcado']
    if status not in status_validos:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use: {status_validos}")
    
    agendamento.status = status
    db.commit()
    
    return {"message": "Status atualizado com sucesso", "novo_status": status}

@router.get("/pacientes")
async def get_pacientes(
    search: Optional[str] = Query(None),
    medico: Medico = Depends(get_current_medico),
    db: Session = Depends(get_db)
):
    """Lista pacientes do médico"""
    
    # Buscar pacientes que já tiveram consulta com este médico
    query = db.query(Paciente).join(Agendamento).filter(
        Agendamento.medico_id == medico.id
    ).distinct()
    
    if search:
        query = query.filter(
            Paciente.nome.ilike(f"%{search}%") |
            Paciente.telefone.ilike(f"%{search}%") |
            Paciente.cpf.ilike(f"%{search}%")
        )
    
    pacientes = query.all()
    
    return [
        {
            "id": p.id,
            "nome": p.nome,
            "telefone": p.telefone,
            "email": p.email,
            "convenio": p.convenio,
            "data_nascimento": p.data_nascimento.isoformat() if p.data_nascimento else None,
            "ultima_consulta": db.query(func.max(Agendamento.data_hora)).filter(
                Agendamento.paciente_id == p.id,
                Agendamento.medico_id == medico.id
            ).scalar()
        }
        for p in pacientes
    ]

@router.get("/horarios")
async def get_horarios_medico(
    medico: Medico = Depends(get_current_medico),
    db: Session = Depends(get_db)
):
    """Obtém configuração de horários do médico"""
    
    horarios = db.query(HorarioAtendimento).filter(
        HorarioAtendimento.medico_id == medico.id
    ).order_by(HorarioAtendimento.dia_semana).all()
    
    return [
        {
            "id": h.id,
            "dia_semana": h.dia_semana,
            "inicio": h.inicio.strftime("%H:%M"),
            "fim": h.fim.strftime("%H:%M"),
            "ativo": h.ativo
        }
        for h in horarios
    ]

@router.post("/horarios")
async def update_horarios(
    horarios: List[HorarioConfig],
    medico: Medico = Depends(get_current_medico),
    db: Session = Depends(get_db)
):
    """Atualiza horários de atendimento do médico"""
    
    # Deletar horários existentes
    db.query(HorarioAtendimento).filter(
        HorarioAtendimento.medico_id == medico.id
    ).delete()
    
    # Adicionar novos horários
    for h in horarios:
        novo_horario = HorarioAtendimento(
            medico_id=medico.id,
            dia_semana=h.dia_semana,
            inicio=datetime.strptime(h.inicio, "%H:%M").time(),
            fim=datetime.strptime(h.fim, "%H:%M").time(),
            ativo=h.ativo
        )
        db.add(novo_horario)
    
    db.commit()
    return {"message": "Horários atualizados com sucesso"}
