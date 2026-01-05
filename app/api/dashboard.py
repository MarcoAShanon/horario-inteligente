from fastapi import APIRouter, Query, Depends
from datetime import date, datetime, timedelta
from typing import Optional, List
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
    taxa_ocupacao: float
    proxima_consulta: Optional[dict]

@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Estatísticas do dashboard com dados REAIS do banco"""

    # Determinar ID do médico (se for médico)
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
        # Médico vê apenas seus pacientes
        result = db.execute(text("""
            SELECT COUNT(DISTINCT a.paciente_id)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id AND p.cliente_id = :cliente_id
        """), {"medico_id": medico_id, "cliente_id": cliente_id})
    else:
        # Secretária vê todos os pacientes do cliente
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

    # Consultas na semana
    if medico_id:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
            AND DATE(a.data_hora) >= :inicio_semana
            AND DATE(a.data_hora) <= :fim_semana
            AND a.status IN ('confirmado', 'em_atendimento')
            AND p.cliente_id = :cliente_id
        """), {"medico_id": medico_id, "inicio_semana": inicio_semana, "fim_semana": fim_semana, "cliente_id": cliente_id})
    else:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE DATE(a.data_hora) >= :inicio_semana
            AND DATE(a.data_hora) <= :fim_semana
            AND a.status IN ('confirmado', 'em_atendimento')
            AND p.cliente_id = :cliente_id
        """), {"inicio_semana": inicio_semana, "fim_semana": fim_semana, "cliente_id": cliente_id})

    consultas_semana = result.scalar() or 0

    # Próxima consulta
    if medico_id:
        result = db.execute(text("""
            SELECT a.id, p.nome, a.data_hora, a.tipo_atendimento
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
            AND a.data_hora >= NOW()
            AND a.status IN ('confirmado', 'confirmada', 'agendada')
            AND p.cliente_id = :cliente_id
            ORDER BY a.data_hora
            LIMIT 1
        """), {"medico_id": medico_id, "cliente_id": cliente_id})
    else:
        result = db.execute(text("""
            SELECT a.id, p.nome, a.data_hora, a.tipo_atendimento
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.data_hora >= NOW()
            AND a.status IN ('confirmado', 'confirmada', 'agendada')
            AND p.cliente_id = :cliente_id
            ORDER BY a.data_hora
            LIMIT 1
        """), {"cliente_id": cliente_id})

    proxima = result.fetchone()
    proxima_consulta = None
    if proxima:
        proxima_consulta = {
            "id": proxima[0],
            "paciente": proxima[1],
            "data_hora": proxima[2].isoformat(),
            "tipo": proxima[3]
        }

    # Taxa de ocupação (simplificada)
    total_horarios = 8 * 5  # 8 horas por dia, 5 dias
    taxa_ocupacao = (consultas_semana / total_horarios) * 100 if total_horarios > 0 else 0

    return DashboardStats(
        total_pacientes=total_pacientes,
        consultas_hoje=consultas_hoje,
        consultas_semana=consultas_semana,
        taxa_ocupacao=round(taxa_ocupacao, 2),
        proxima_consulta=proxima_consulta
    )


# ============== NOVOS ENDPOINTS PARA MÉTRICAS POR PERÍODO ==============

class MetricasPeriodo(BaseModel):
    periodo: str
    mes_ano: str
    total_agendamentos: int
    confirmados: int
    concluidos: int
    cancelados: int
    remarcados: int
    faltou: int
    taxa_comparecimento: float
    taxa_cancelamento: float
    por_status: List[dict]
    por_dia: List[dict]
    por_convenio: Optional[List[dict]] = None
    horarios_populares: Optional[List[dict]] = None
    comparativo_anterior: Optional[dict] = None


@router.get("/metricas", response_model=MetricasPeriodo)
async def get_metricas_periodo(
    periodo: str = Query(..., description="mes_atual, mes_anterior ou 12_meses"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna métricas detalhadas por período com gráficos

    Períodos disponíveis:
    - mes_atual: Mês corrente
    - mes_anterior: Mês passado
    - 12_meses: Últimos 12 meses
    """

    user_type = current_user.get("tipo")
    user_id = current_user.get("id")
    cliente_id = current_user.get("cliente_id")

    # Se for médico, filtra apenas seus dados
    medico_id = user_id if user_type == "medico" else None

    hoje = date.today()

    # Nomes dos meses em português
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    # Definir período baseado no parâmetro
    if periodo == "mes_atual":
        inicio_periodo = date(hoje.year, hoje.month, 1)
        fim_periodo = hoje
        mes_ano = f"{meses_pt[hoje.month]} {hoje.year}"

        # Mês anterior para comparativo
        if hoje.month == 1:
            inicio_anterior = date(hoje.year - 1, 12, 1)
            mes_anterior = 12
            ano_anterior = hoje.year - 1
        else:
            inicio_anterior = date(hoje.year, hoje.month - 1, 1)
            mes_anterior = hoje.month - 1
            ano_anterior = hoje.year

        # Último dia do mês anterior
        if mes_anterior == 12:
            fim_anterior = date(ano_anterior, 12, 31)
        else:
            proximo_mes = date(ano_anterior, mes_anterior + 1, 1)
            fim_anterior = proximo_mes - timedelta(days=1)

    elif periodo == "mes_anterior":
        if hoje.month == 1:
            inicio_periodo = date(hoje.year - 1, 12, 1)
            fim_periodo = date(hoje.year - 1, 12, 31)
            mes_ano = f"Dezembro {hoje.year - 1}"

            # Dois meses atrás para comparativo
            inicio_anterior = date(hoje.year - 1, 11, 1)
            fim_anterior = date(hoje.year - 1, 11, 30)
        else:
            inicio_periodo = date(hoje.year, hoje.month - 1, 1)
            # Último dia do mês anterior
            fim_periodo = date(hoje.year, hoje.month, 1) - timedelta(days=1)
            mes_ano = f"{meses_pt[hoje.month - 1]} {hoje.year}"

            # Dois meses atrás
            if hoje.month == 2:
                inicio_anterior = date(hoje.year - 1, 12, 1)
                fim_anterior = date(hoje.year - 1, 12, 31)
            else:
                inicio_anterior = date(hoje.year, hoje.month - 2, 1)
                fim_anterior = date(hoje.year, hoje.month - 1, 1) - timedelta(days=1)

    else:  # 12_meses
        inicio_periodo = hoje - timedelta(days=365)
        fim_periodo = hoje
        mes_ano = f"Últimos 12 meses até {hoje.strftime('%d/%m/%Y')}"
        inicio_anterior = None
        fim_anterior = None

    # Query base para agendamentos
    filtro_medico = "AND a.medico_id = :medico_id" if medico_id else ""

    # Total de agendamentos no período
    # Nota: 'realizada' implica que foi 'confirmada' antes, então conta em ambos
    query_total = text(f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN a.status IN ('confirmado', 'confirmada', 'realizada', 'concluido', 'concluida') THEN 1 ELSE 0 END) as confirmados,
            SUM(CASE WHEN a.status IN ('concluido', 'concluida', 'realizada') THEN 1 ELSE 0 END) as concluidos,
            SUM(CASE WHEN a.status IN ('cancelado', 'cancelada') THEN 1 ELSE 0 END) as cancelados,
            SUM(CASE WHEN a.status = 'remarcado' THEN 1 ELSE 0 END) as remarcados,
            SUM(CASE WHEN a.status = 'faltou' THEN 1 ELSE 0 END) as faltou
        FROM agendamentos a
        JOIN pacientes p ON a.paciente_id = p.id
        WHERE DATE(a.data_hora) >= :inicio
        AND DATE(a.data_hora) <= :fim
        AND p.cliente_id = :cliente_id
        {filtro_medico}
    """)

    params = {
        "inicio": inicio_periodo,
        "fim": fim_periodo,
        "cliente_id": cliente_id
    }
    if medico_id:
        params["medico_id"] = medico_id

    result = db.execute(query_total, params).fetchone()

    total_agendamentos = result[0] or 0
    confirmados = result[1] or 0
    concluidos = result[2] or 0
    cancelados = result[3] or 0
    remarcados = result[4] or 0
    faltou = result[5] or 0

    # Calcular taxas
    total_realizados = concluidos + faltou
    taxa_comparecimento = (concluidos / total_realizados * 100) if total_realizados > 0 else 0
    taxa_cancelamento = (cancelados / total_agendamentos * 100) if total_agendamentos > 0 else 0

    # Distribuição por status (para gráfico de pizza)
    por_status = [
        {"status": "Confirmados", "quantidade": confirmados, "cor": "#3b82f6"},
        {"status": "Concluídos", "quantidade": concluidos, "cor": "#10b981"},
        {"status": "Cancelados", "quantidade": cancelados, "cor": "#ef4444"},
        {"status": "Remarcados", "quantidade": remarcados, "cor": "#f59e0b"},
        {"status": "Faltas", "quantidade": faltou, "cor": "#6b7280"}
    ]

    # Agendamentos por dia (para gráfico de barras)
    if periodo in ["mes_atual", "mes_anterior"]:
        query_por_dia = text(f"""
            SELECT
                DATE(a.data_hora) as dia,
                COUNT(*) as quantidade
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE DATE(a.data_hora) >= :inicio
            AND DATE(a.data_hora) <= :fim
            AND p.cliente_id = :cliente_id
            {filtro_medico}
            GROUP BY DATE(a.data_hora)
            ORDER BY dia
        """)

        resultado_dias = db.execute(query_por_dia, params).fetchall()
        por_dia = [
            {"dia": row[0].strftime("%d/%m"), "quantidade": row[1]}
            for row in resultado_dias
        ]
    else:  # 12 meses - agrupar por mês
        query_por_mes = text(f"""
            SELECT
                DATE_TRUNC('month', a.data_hora) as mes,
                COUNT(*) as quantidade
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE DATE(a.data_hora) >= :inicio
            AND DATE(a.data_hora) <= :fim
            AND p.cliente_id = :cliente_id
            {filtro_medico}
            GROUP BY DATE_TRUNC('month', a.data_hora)
            ORDER BY mes
        """)

        resultado_meses = db.execute(query_por_mes, params).fetchall()
        meses_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                   "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        por_dia = [
            {"dia": f"{meses_pt[row[0].month - 1]}/{str(row[0].year)[2:]}", "quantidade": row[1]}
            for row in resultado_meses
        ]

    # Distribuição por convênio
    query_convenio = text(f"""
        SELECT
            COALESCE(p.convenio, 'Particular') as convenio,
            COUNT(*) as quantidade
        FROM agendamentos a
        JOIN pacientes p ON a.paciente_id = p.id
        WHERE DATE(a.data_hora) >= :inicio
        AND DATE(a.data_hora) <= :fim
        AND p.cliente_id = :cliente_id
        {filtro_medico}
        GROUP BY p.convenio
        ORDER BY quantidade DESC
        LIMIT 5
    """)

    resultado_convenio = db.execute(query_convenio, params).fetchall()
    por_convenio = [
        {"convenio": row[0] or "Particular", "quantidade": row[1]}
        for row in resultado_convenio
    ]

    # Horários mais populares
    query_horarios = text(f"""
        SELECT
            EXTRACT(HOUR FROM a.data_hora) as hora,
            COUNT(*) as quantidade
        FROM agendamentos a
        JOIN pacientes p ON a.paciente_id = p.id
        WHERE DATE(a.data_hora) >= :inicio
        AND DATE(a.data_hora) <= :fim
        AND p.cliente_id = :cliente_id
        {filtro_medico}
        GROUP BY EXTRACT(HOUR FROM a.data_hora)
        ORDER BY quantidade DESC
        LIMIT 5
    """)

    resultado_horarios = db.execute(query_horarios, params).fetchall()
    horarios_populares = [
        {"horario": f"{int(row[0]):02d}:00", "quantidade": row[1]}
        for row in resultado_horarios
    ]

    # Comparativo com período anterior (apenas para mês atual e anterior)
    comparativo_anterior = None
    if periodo in ["mes_atual", "mes_anterior"] and inicio_anterior and fim_anterior:
        params_anterior = {
            "inicio": inicio_anterior,
            "fim": fim_anterior,
            "cliente_id": cliente_id
        }
        if medico_id:
            params_anterior["medico_id"] = medico_id

        result_anterior = db.execute(query_total, params_anterior).fetchone()
        total_anterior = result_anterior[0] or 0
        concluidos_anterior = result_anterior[2] or 0

        variacao_agendamentos = ((total_agendamentos - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0

        total_realizados_anterior = concluidos_anterior + (result_anterior[5] or 0)
        taxa_anterior = (concluidos_anterior / total_realizados_anterior * 100) if total_realizados_anterior > 0 else 0
        variacao_taxa = taxa_comparecimento - taxa_anterior

        comparativo_anterior = {
            "total_anterior": total_anterior,
            "variacao_agendamentos": round(variacao_agendamentos, 1),
            "variacao_taxa": round(variacao_taxa, 1)
        }

    return MetricasPeriodo(
        periodo=periodo,
        mes_ano=mes_ano,
        total_agendamentos=total_agendamentos,
        confirmados=confirmados,
        concluidos=concluidos,
        cancelados=cancelados,
        remarcados=remarcados,
        faltou=faltou,
        taxa_comparecimento=round(taxa_comparecimento, 1),
        taxa_cancelamento=round(taxa_cancelamento, 1),
        por_status=por_status,
        por_dia=por_dia,
        por_convenio=por_convenio,
        horarios_populares=horarios_populares,
        comparativo_anterior=comparativo_anterior
    )


# ============== FIM NOVOS ENDPOINTS ==============

@router.get("/agenda/hoje")
async def get_agenda_hoje():
    """Agenda de hoje (dados mock)"""
    return [
        {
            "id": 1,
            "horario": "09:00",
            "paciente": "Maria Santos",
            "telefone": "(21) 99999-1234",
            "status": "confirmado",
            "tipo": "Consulta"
        },
        {
            "id": 2,
            "horario": "10:00",
            "paciente": "José Oliveira",
            "telefone": "(21) 99999-5678",
            "status": "confirmado",
            "tipo": "Retorno"
        },
        {
            "id": 3,
            "horario": "11:00",
            "paciente": "Ana Costa",
            "telefone": "(21) 99999-9012",
            "status": "confirmado",
            "tipo": "Consulta"
        },
        {
            "id": 4,
            "horario": "14:00",
            "paciente": "Carlos Souza",
            "telefone": "(21) 99999-3456",
            "status": "em_atendimento",
            "tipo": "Consulta"
        }
    ]

@router.put("/agendamento/{agendamento_id}/status")
async def update_status(agendamento_id: int, status: str = Query(...)):
    """Atualiza status do agendamento"""
    return {
        "message": "Status atualizado com sucesso",
        "agendamento_id": agendamento_id,
        "novo_status": status
    }

@router.get("/pacientes")
async def get_pacientes(search: Optional[str] = None):
    """Lista de pacientes (dados mock)"""
    pacientes = [
        {"id": 1, "nome": "João Silva", "telefone": "(21) 99999-1234", "convenio": "Unimed"},
        {"id": 2, "nome": "Maria Santos", "telefone": "(21) 99999-5678", "convenio": "Particular"},
        {"id": 3, "nome": "José Oliveira", "telefone": "(21) 99999-9012", "convenio": "Amil"},
    ]
    
    if search:
        pacientes = [p for p in pacientes if search.lower() in p["nome"].lower()]
    
    return pacientes

@router.get("/horarios")
async def get_horarios():
    """Configuração de horários"""
    return [
        {"dia_semana": 0, "dia": "Segunda", "inicio": "08:00", "fim": "18:00", "ativo": True},
        {"dia_semana": 1, "dia": "Terça", "inicio": "08:00", "fim": "18:00", "ativo": True},
        {"dia_semana": 2, "dia": "Quarta", "inicio": "08:00", "fim": "18:00", "ativo": True},
        {"dia_semana": 3, "dia": "Quinta", "inicio": "08:00", "fim": "18:00", "ativo": True},
        {"dia_semana": 4, "dia": "Sexta", "inicio": "08:00", "fim": "18:00", "ativo": True},
    ]
