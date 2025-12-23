from fastapi import APIRouter, Depends
from datetime import date, datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.auth import get_current_user

router = APIRouter()

class DashboardStats(BaseModel):
    total_pacientes: int
    consultas_hoje: int
    consultas_semana: int
    atendimentos_realizados: int
    faltas_sem_aviso: int
    cancelamentos: int
    taxa_comparecimento: float
    taxa_ocupacao: float
    proxima_consulta: Optional[dict] = None

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dashboard stats com dados reais - SIMPLIFICADO"""

    # Determinar ID do médico  (se for médico)
    user_type = current_user.get("tipo")
    user_id = current_user.get("id")
    cliente_id = current_user.get("cliente_id")

    # Se for médico, filtra apenas seus dados
    medico_id = user_id if user_type == "medico" else None

    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)

    # Total de pacientes únicos
    if medico_id:
        result = db.execute(text("""
            SELECT COUNT(DISTINCT a.paciente_id)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id AND p.cliente_id = :cliente_id
        """), {"medico_id": medico_id, "cliente_id": cliente_id})
    else:
        result = db.execute(text("""
            SELECT COUNT(DISTINCT id)
            FROM pacientes
            WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})

    total_pacientes = result.scalar() or 0

    # Consultas hoje
    if medico_id:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
            AND DATE(a.data_hora) = :hoje
            AND a.status IN ('confirmado', 'em_atendimento')
            AND p.cliente_id = :cliente_id
        """), {"medico_id": medico_id, "hoje": hoje, "cliente_id": cliente_id})
    else:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE DATE(a.data_hora) = :hoje
            AND a.status IN ('confirmado', 'em_atendimento')
            AND p.cliente_id = :cliente_id
        """), {"hoje": hoje, "cliente_id": cliente_id})

    consultas_hoje = result.scalar() or 0

    # Consultas na semana (TODOS os agendamentos, independente do status)
    if medico_id:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
            AND DATE(a.data_hora) >= :inicio_semana
            AND DATE(a.data_hora) <= :fim_semana
            AND p.cliente_id = :cliente_id
        """), {"medico_id": medico_id, "inicio_semana": inicio_semana, "fim_semana": fim_semana, "cliente_id": cliente_id})
    else:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE DATE(a.data_hora) >= :inicio_semana
            AND DATE(a.data_hora) <= :fim_semana
            AND p.cliente_id = :cliente_id
        """), {"inicio_semana": inicio_semana, "fim_semana": fim_semana, "cliente_id": cliente_id})

    consultas_semana = result.scalar() or 0

    # Atendimentos realizados (status = 'concluido')
    if medico_id:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
            AND DATE(a.data_hora) >= :inicio_semana
            AND DATE(a.data_hora) <= :fim_semana
            AND a.status = 'concluido'
            AND p.cliente_id = :cliente_id
        """), {"medico_id": medico_id, "inicio_semana": inicio_semana, "fim_semana": fim_semana, "cliente_id": cliente_id})
    else:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE DATE(a.data_hora) >= :inicio_semana
            AND DATE(a.data_hora) <= :fim_semana
            AND a.status = 'concluido'
            AND p.cliente_id = :cliente_id
        """), {"inicio_semana": inicio_semana, "fim_semana": fim_semana, "cliente_id": cliente_id})

    atendimentos_realizados = result.scalar() or 0

    # Faltas sem aviso (status = 'faltou')
    if medico_id:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
            AND DATE(a.data_hora) >= :inicio_semana
            AND DATE(a.data_hora) <= :fim_semana
            AND a.status = 'faltou'
            AND p.cliente_id = :cliente_id
        """), {"medico_id": medico_id, "inicio_semana": inicio_semana, "fim_semana": fim_semana, "cliente_id": cliente_id})
    else:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE DATE(a.data_hora) >= :inicio_semana
            AND DATE(a.data_hora) <= :fim_semana
            AND a.status = 'faltou'
            AND p.cliente_id = :cliente_id
        """), {"inicio_semana": inicio_semana, "fim_semana": fim_semana, "cliente_id": cliente_id})

    faltas = result.scalar() or 0

    # Cancelamentos (status = 'cancelado')
    if medico_id:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
            AND DATE(a.data_hora) >= :inicio_semana
            AND DATE(a.data_hora) <= :fim_semana
            AND a.status = 'cancelado'
            AND p.cliente_id = :cliente_id
        """), {"medico_id": medico_id, "inicio_semana": inicio_semana, "fim_semana": fim_semana, "cliente_id": cliente_id})
    else:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE DATE(a.data_hora) >= :inicio_semana
            AND DATE(a.data_hora) <= :fim_semana
            AND a.status = 'cancelado'
            AND p.cliente_id = :cliente_id
        """), {"inicio_semana": inicio_semana, "fim_semana": fim_semana, "cliente_id": cliente_id})

    cancelamentos = result.scalar() or 0

    # Taxa de comparecimento (realizados / (realizados + faltas) * 100)
    total_passado = atendimentos_realizados + faltas
    taxa_comparecimento = (atendimentos_realizados / total_passado * 100) if total_passado > 0 else 0

    # Taxa de ocupação (simplificada)
    total_horarios = 8 * 5  # 8 horas por dia, 5 dias
    taxa_ocupacao = (consultas_semana / total_horarios) * 100 if total_horarios > 0 else 0

    return DashboardStats(
        total_pacientes=total_pacientes,
        consultas_hoje=consultas_hoje,
        consultas_semana=consultas_semana,
        atendimentos_realizados=atendimentos_realizados,
        faltas_sem_aviso=faltas,
        cancelamentos=cancelamentos,
        taxa_comparecimento=round(taxa_comparecimento, 2),
        taxa_ocupacao=round(taxa_ocupacao, 2),
        proxima_consulta=None  # Simplificado por enquanto
    )

@router.get("/agenda/hoje")
async def get_agenda_hoje(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Agenda de hoje com dados reais"""

    user_type = current_user.get("tipo")
    user_id = current_user.get("id")
    cliente_id = current_user.get("cliente_id")

    medico_id = user_id if user_type == "medico" else None
    hoje = date.today()

    # Buscar agendamentos de hoje
    if medico_id:
        result = db.execute(text("""
            SELECT
                a.id,
                TO_CHAR(a.data_hora, 'HH24:MI') as horario,
                p.nome as paciente,
                p.telefone,
                a.status,
                a.tipo_atendimento
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
            AND DATE(a.data_hora) = :hoje
            AND p.cliente_id = :cliente_id
            ORDER BY a.data_hora
        """), {"medico_id": medico_id, "hoje": hoje, "cliente_id": cliente_id})
    else:
        result = db.execute(text("""
            SELECT
                a.id,
                TO_CHAR(a.data_hora, 'HH24:MI') as horario,
                p.nome as paciente,
                p.telefone,
                a.status,
                a.tipo_atendimento,
                m.nome as medico_nome
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            JOIN medicos m ON a.medico_id = m.id
            WHERE DATE(a.data_hora) = :hoje
            AND p.cliente_id = :cliente_id
            ORDER BY a.data_hora
        """), {"hoje": hoje, "cliente_id": cliente_id})

    agendamentos = []
    for row in result:
        agendamento = {
            "id": row[0],
            "horario": row[1],
            "paciente": row[2],
            "telefone": row[3],
            "status": row[4],
            "tipo": row[5]
        }
        if user_type != "medico" and len(row) > 6:
            agendamento["medico"] = row[6]

        agendamentos.append(agendamento)

    return agendamentos
