# app/api/configuracao.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.configuracoes import ConfiguracoesMedico, BloqueioAgenda
from app.models.medico import Medico
from app.models.calendario import HorarioAtendimento
from app.api.auth import get_current_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import time, datetime
import json

router = APIRouter()

class ConfiguracaoIntervalosRequest(BaseModel):
    medico_id: int
    intervalo_consulta: int  # em minutos (15, 30, 45, 60, 90, 120)
    horario_inicio: str     # "08:00"
    horario_fim: str        # "18:00"
    dias_atendimento: List[int]  # [1,2,3,4,5] = seg-sex
    intervalo_almoco_inicio: Optional[str] = None  # "12:00"
    intervalo_almoco_fim: Optional[str] = None     # "13:00"
    tempo_antes_consulta: int = 5  # tempo de preparação em minutos
    consultas_simultaneas: int = 1  # quantas consultas ao mesmo tempo
    antecedencia_minima: Optional[int] = 60  # antecedência mínima em minutos
    horarios_por_dia: Optional[dict] = None  # horários individuais por dia da semana

class ConfiguracaoIntervalosResponse(BaseModel):
    id: int
    medico_id: int
    medico_nome: str
    intervalo_consulta: int
    horario_inicio: str
    horario_fim: str
    dias_atendimento: List[int]
    intervalo_almoco_inicio: Optional[str]
    intervalo_almoco_fim: Optional[str]
    tempo_antes_consulta: int
    consultas_simultaneas: int
    antecedencia_minima: int
    horarios_por_dia: Optional[dict] = None
    ativo: bool

@router.get("/intervalos/{medico_id}", response_model=ConfiguracaoIntervalosResponse)
async def obter_configuracao_intervalos(medico_id: int, db: Session = Depends(get_db)):
    """Obtém a configuração de intervalos de um médico"""
    
    # Buscar configuração existente
    config = db.query(ConfiguracoesMedico).filter(
        ConfiguracoesMedico.medico_id == medico_id
    ).first()
    
    # Buscar dados do médico
    medico = db.query(Medico).filter(Medico.id == medico_id).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico não encontrado")
    
    if not config:
        # Retornar configuração padrão se não existir
        return ConfiguracaoIntervalosResponse(
            id=0,
            medico_id=medico_id,
            medico_nome=medico.nome,
            intervalo_consulta=30,  # padrão 30 minutos
            horario_inicio="08:00",
            horario_fim="18:00",
            dias_atendimento=[1, 2, 3, 4, 5],  # seg-sex
            intervalo_almoco_inicio="12:00",
            intervalo_almoco_fim="13:00",
            tempo_antes_consulta=5,
            consultas_simultaneas=1,
            antecedencia_minima=60,
            horarios_por_dia=None,
            ativo=True
        )
    
    # Parse dos dias de atendimento se estiver em JSON
    dias_atendimento = config.dias_atendimento
    if isinstance(dias_atendimento, str):
        try:
            dias_atendimento = json.loads(dias_atendimento)
        except:
            dias_atendimento = [1, 2, 3, 4, 5]

    # Parse dos horários por dia se existir
    horarios_por_dia = None
    if config.horarios_por_dia:
        try:
            horarios_por_dia = json.loads(config.horarios_por_dia)
        except:
            horarios_por_dia = None

    return ConfiguracaoIntervalosResponse(
        id=config.id,
        medico_id=config.medico_id,
        medico_nome=medico.nome,
        intervalo_consulta=config.intervalo_consulta or 30,
        horario_inicio=config.horario_inicio or "08:00",
        horario_fim=config.horario_fim or "18:00",
        dias_atendimento=dias_atendimento,
        intervalo_almoco_inicio=config.intervalo_almoco_inicio,
        intervalo_almoco_fim=config.intervalo_almoco_fim,
        tempo_antes_consulta=config.tempo_antes_consulta or 5,
        consultas_simultaneas=config.consultas_simultaneas or 1,
        antecedencia_minima=config.antecedencia_minima or 60,
        horarios_por_dia=horarios_por_dia,
        ativo=config.ativo if config.ativo is not None else True
    )

@router.post("/intervalos")
async def salvar_configuracao_intervalos(config_request: ConfiguracaoIntervalosRequest, db: Session = Depends(get_db)):
    """Salva/atualiza a configuração de intervalos de um médico"""
    
    # Verificar se médico existe
    medico = db.query(Medico).filter(Medico.id == config_request.medico_id).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico não encontrado")
    
    # Validações
    if config_request.intervalo_consulta < 15 or config_request.intervalo_consulta > 240:
        raise HTTPException(status_code=400, detail="Intervalo deve estar entre 15 e 240 minutos")
    
    if not config_request.dias_atendimento or len(config_request.dias_atendimento) == 0:
        raise HTTPException(status_code=400, detail="Deve selecionar pelo menos um dia de atendimento")
    
    # Verificar se já existe configuração
    config_existente = db.query(ConfiguracoesMedico).filter(
        ConfiguracoesMedico.medico_id == config_request.medico_id
    ).first()
    
    # Serializar horarios_por_dia se presente
    horarios_por_dia_json = None
    if config_request.horarios_por_dia:
        horarios_por_dia_json = json.dumps(config_request.horarios_por_dia)

    if config_existente:
        # Atualizar configuração existente
        config_existente.intervalo_consulta = config_request.intervalo_consulta
        config_existente.horario_inicio = config_request.horario_inicio
        config_existente.horario_fim = config_request.horario_fim
        config_existente.dias_atendimento = json.dumps(config_request.dias_atendimento)
        config_existente.intervalo_almoco_inicio = config_request.intervalo_almoco_inicio
        config_existente.intervalo_almoco_fim = config_request.intervalo_almoco_fim
        config_existente.tempo_antes_consulta = config_request.tempo_antes_consulta
        config_existente.consultas_simultaneas = config_request.consultas_simultaneas
        config_existente.antecedencia_minima = config_request.antecedencia_minima or 60
        config_existente.horarios_por_dia = horarios_por_dia_json
        config_existente.ativo = True

        config = config_existente
    else:
        # Criar nova configuração
        nova_config = ConfiguracoesMedico(
            medico_id=config_request.medico_id,
            intervalo_consulta=config_request.intervalo_consulta,
            horario_inicio=config_request.horario_inicio,
            horario_fim=config_request.horario_fim,
            dias_atendimento=json.dumps(config_request.dias_atendimento),
            intervalo_almoco_inicio=config_request.intervalo_almoco_inicio,
            intervalo_almoco_fim=config_request.intervalo_almoco_fim,
            tempo_antes_consulta=config_request.tempo_antes_consulta,
            consultas_simultaneas=config_request.consultas_simultaneas,
            antecedencia_minima=config_request.antecedencia_minima or 60,
            horarios_por_dia=horarios_por_dia_json,
            ativo=True
        )
        db.add(nova_config)
        config = nova_config
    
    try:
        db.commit()
        db.refresh(config)
        
        return {
            "success": True,
            "message": "Configuração salva com sucesso!",
            "config_id": config.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar configuração: {str(e)}")

@router.get("/opcoes-intervalo")
async def obter_opcoes_intervalo():
    """Retorna as opções disponíveis para intervalos de consulta"""
    
    opcoes_intervalo = [
        {"valor": 15, "texto": "15 minutos"},
        {"valor": 20, "texto": "20 minutos"},
        {"valor": 30, "texto": "30 minutos"},
        {"valor": 45, "texto": "45 minutos"},
        {"valor": 60, "texto": "1 hora"},
        {"valor": 90, "texto": "1 hora e 30 minutos"},
        {"valor": 120, "texto": "2 horas"},
    ]
    
    dias_semana = [
        {"valor": 1, "texto": "Segunda-feira"},
        {"valor": 2, "texto": "Terça-feira"},
        {"valor": 3, "texto": "Quarta-feira"},
        {"valor": 4, "texto": "Quinta-feira"},
        {"valor": 5, "texto": "Sexta-feira"},
        {"valor": 6, "texto": "Sábado"},
        {"valor": 0, "texto": "Domingo"},
    ]
    
    horarios_padrao = []
    for hora in range(6, 24):  # 06:00 às 23:00
        for minuto in [0, 30]:
            horario = f"{hora:02d}:{minuto:02d}"
            horarios_padrao.append({
                "valor": horario,
                "texto": horario
            })
    
    return {
        "opcoes_intervalo": opcoes_intervalo,
        "dias_semana": dias_semana,
        "horarios_padrao": horarios_padrao
    }

# Função auxiliar para calcular horários disponíveis baseado na configuração
def calcular_horarios_disponiveis(config: ConfiguracoesMedico, data_consulta: str):
    """
    Calcula os horários disponíveis para uma data específica baseado na configuração
    Esta função será útil para integrar com o WhatsApp Bot
    """
    from datetime import datetime, timedelta
    import calendar
    
    try:
        data_obj = datetime.strptime(data_consulta, "%Y-%m-%d")
        dia_semana = data_obj.weekday()  # 0=segunda, 6=domingo
        
        # Converter para formato usado na configuração (1=segunda, 0=domingo)
        dia_config = dia_semana + 1 if dia_semana < 6 else 0
        
        # Parse dos dias de atendimento
        dias_atendimento = config.dias_atendimento
        if isinstance(dias_atendimento, str):
            dias_atendimento = json.loads(dias_atendimento)
        
        # Verificar se atende neste dia
        if dia_config not in dias_atendimento:
            return []
        
        # Calcular horários
        horarios = []
        inicio = datetime.strptime(config.horario_inicio or "08:00", "%H:%M")
        fim = datetime.strptime(config.horario_fim or "18:00", "%H:%M")
        intervalo = timedelta(minutes=config.intervalo_consulta or 30)
        
        # Intervalo de almoço
        almoco_inicio = None
        almoco_fim = None
        if config.intervalo_almoco_inicio and config.intervalo_almoco_fim:
            almoco_inicio = datetime.strptime(config.intervalo_almoco_inicio, "%H:%M")
            almoco_fim = datetime.strptime(config.intervalo_almoco_fim, "%H:%M")
        
        horario_atual = inicio
        while horario_atual < fim:
            # Verificar se não está no horário de almoço
            if almoco_inicio and almoco_fim:
                if almoco_inicio <= horario_atual < almoco_fim:
                    horario_atual += intervalo
                    continue
            
            horarios.append(horario_atual.strftime("%H:%M"))
            horario_atual += intervalo
        
        return horarios
        
    except Exception as e:
        print(f"Erro ao calcular horários disponíveis: {e}")
        return []

@router.get("/horarios-disponiveis/{medico_id}")
async def obter_horarios_disponiveis(medico_id: int, data: str, db: Session = Depends(get_db)):
    """
    Retorna os horários disponíveis para um médico em uma data específica
    Format data: YYYY-MM-DD
    """
    
    # Buscar configuração do médico
    config = db.query(ConfiguracoesMedico).filter(
        ConfiguracoesMedico.medico_id == medico_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuração do médico não encontrada")
    
    horarios = calcular_horarios_disponiveis(config, data)
    
    return {
        "data": data,
        "medico_id": medico_id,
        "horarios_disponiveis": horarios,
        "total_horarios": len(horarios)
    }

# ============================================
# HORÁRIOS SEMANAIS DETALHADOS (individualizado por médico)
# ============================================

class HorarioSemanalRequest(BaseModel):
    medico_id: int
    dia_semana: int  # 1=Segunda, 2=Terça, ..., 7=Domingo
    hora_inicio: str  # "08:00"
    hora_fim: str     # "12:00"
    ativo: bool = True

class HorarioSemanalResponse(BaseModel):
    id: int
    medico_id: int
    medico_nome: str
    dia_semana: int
    dia_semana_nome: str
    hora_inicio: str
    hora_fim: str
    ativo: bool

    class Config:
        from_attributes = True

def _get_nome_dia_semana(dia: int) -> str:
    """Converte número do dia para nome"""
    dias = {
        1: "Segunda-feira",
        2: "Terça-feira",
        3: "Quarta-feira",
        4: "Quinta-feira",
        5: "Sexta-feira",
        6: "Sábado",
        7: "Domingo"
    }
    return dias.get(dia, "Desconhecido")

@router.get("/horarios-semanais/{medico_id}", response_model=List[HorarioSemanalResponse])
async def listar_horarios_semanais(medico_id: int, db: Session = Depends(get_db)):
    """Lista todos os horários semanais de um médico"""

    # Verificar se médico existe
    medico = db.query(Medico).filter(Medico.id == medico_id).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico não encontrado")

    # Buscar horários
    horarios = db.query(HorarioAtendimento).filter(
        HorarioAtendimento.medico_id == medico_id
    ).order_by(HorarioAtendimento.dia_semana, HorarioAtendimento.hora_inicio).all()

    # Formatar resposta
    resultado = []
    for horario in horarios:
        resultado.append(HorarioSemanalResponse(
            id=horario.id,
            medico_id=horario.medico_id,
            medico_nome=medico.nome,
            dia_semana=horario.dia_semana,
            dia_semana_nome=_get_nome_dia_semana(horario.dia_semana),
            hora_inicio=horario.hora_inicio.strftime("%H:%M") if isinstance(horario.hora_inicio, time) else horario.hora_inicio,
            hora_fim=horario.hora_fim.strftime("%H:%M") if isinstance(horario.hora_fim, time) else horario.hora_fim,
            ativo=horario.ativo
        ))

    return resultado

@router.post("/horarios-semanais")
async def criar_horario_semanal(horario_request: HorarioSemanalRequest, db: Session = Depends(get_db)):
    """Cria um novo horário semanal para o médico"""

    # Verificar se médico existe
    medico = db.query(Medico).filter(Medico.id == horario_request.medico_id).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico não encontrado")

    # Validações
    if horario_request.dia_semana < 1 or horario_request.dia_semana > 7:
        raise HTTPException(status_code=400, detail="Dia da semana deve estar entre 1 (Segunda) e 7 (Domingo)")

    try:
        # Converter strings de horário para objetos time
        hora_inicio_obj = time.fromisoformat(horario_request.hora_inicio)
        hora_fim_obj = time.fromisoformat(horario_request.hora_fim)

        if hora_inicio_obj >= hora_fim_obj:
            raise HTTPException(status_code=400, detail="Hora de início deve ser antes da hora de fim")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de hora inválido. Use HH:MM")

    # Verificar conflitos de horário
    horarios_existentes = db.query(HorarioAtendimento).filter(
        HorarioAtendimento.medico_id == horario_request.medico_id,
        HorarioAtendimento.dia_semana == horario_request.dia_semana,
        HorarioAtendimento.ativo == True
    ).all()

    for horario_existente in horarios_existentes:
        hora_inicio_existente = horario_existente.hora_inicio
        hora_fim_existente = horario_existente.hora_fim

        # Verificar sobreposição de horários
        if (hora_inicio_obj < hora_fim_existente and hora_fim_obj > hora_inicio_existente):
            raise HTTPException(
                status_code=400,
                detail=f"Conflito de horário com período existente: {hora_inicio_existente.strftime('%H:%M')} - {hora_fim_existente.strftime('%H:%M')}"
            )

    # Criar novo horário
    novo_horario = HorarioAtendimento(
        medico_id=horario_request.medico_id,
        dia_semana=horario_request.dia_semana,
        hora_inicio=hora_inicio_obj,
        hora_fim=hora_fim_obj,
        ativo=horario_request.ativo
    )

    try:
        db.add(novo_horario)
        db.commit()
        db.refresh(novo_horario)

        return {
            "success": True,
            "message": f"Horário criado com sucesso para {_get_nome_dia_semana(horario_request.dia_semana)}",
            "horario_id": novo_horario.id,
            "horario": {
                "id": novo_horario.id,
                "dia_semana": novo_horario.dia_semana,
                "dia_semana_nome": _get_nome_dia_semana(novo_horario.dia_semana),
                "hora_inicio": novo_horario.hora_inicio.strftime("%H:%M"),
                "hora_fim": novo_horario.hora_fim.strftime("%H:%M"),
                "ativo": novo_horario.ativo
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar horário: {str(e)}")

@router.put("/horarios-semanais/{horario_id}")
async def atualizar_horario_semanal(horario_id: int, horario_request: HorarioSemanalRequest, db: Session = Depends(get_db)):
    """Atualiza um horário semanal existente"""

    # Buscar horário
    horario = db.query(HorarioAtendimento).filter(HorarioAtendimento.id == horario_id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horário não encontrado")

    # Validações
    if horario_request.dia_semana < 1 or horario_request.dia_semana > 7:
        raise HTTPException(status_code=400, detail="Dia da semana deve estar entre 1 (Segunda) e 7 (Domingo)")

    try:
        # Converter strings de horário para objetos time
        hora_inicio_obj = time.fromisoformat(horario_request.hora_inicio)
        hora_fim_obj = time.fromisoformat(horario_request.hora_fim)

        if hora_inicio_obj >= hora_fim_obj:
            raise HTTPException(status_code=400, detail="Hora de início deve ser antes da hora de fim")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de hora inválido. Use HH:MM")

    # Atualizar
    horario.dia_semana = horario_request.dia_semana
    horario.hora_inicio = hora_inicio_obj
    horario.hora_fim = hora_fim_obj
    horario.ativo = horario_request.ativo

    try:
        db.commit()
        db.refresh(horario)

        return {
            "success": True,
            "message": "Horário atualizado com sucesso",
            "horario_id": horario.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar horário: {str(e)}")

@router.delete("/horarios-semanais/{horario_id}")
async def deletar_horario_semanal(horario_id: int, db: Session = Depends(get_db)):
    """Deleta um horário semanal"""

    # Buscar horário
    horario = db.query(HorarioAtendimento).filter(HorarioAtendimento.id == horario_id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horário não encontrado")

    try:
        db.delete(horario)
        db.commit()

        return {
            "success": True,
            "message": "Horário deletado com sucesso"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar horário: {str(e)}")

@router.patch("/horarios-semanais/{horario_id}/toggle")
async def toggle_horario_semanal(horario_id: int, db: Session = Depends(get_db)):
    """Ativa/desativa um horário semanal"""

    # Buscar horário
    horario = db.query(HorarioAtendimento).filter(HorarioAtendimento.id == horario_id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horário não encontrado")

    # Toggle ativo
    horario.ativo = not horario.ativo

    try:
        db.commit()
        db.refresh(horario)

        return {
            "success": True,
            "message": f"Horário {'ativado' if horario.ativo else 'desativado'} com sucesso",
            "ativo": horario.ativo
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar horário: {str(e)}")

# ============================================
# ENDPOINTS DE BLOQUEIOS DE AGENDA
# ============================================

class BloqueioRequest(BaseModel):
    medico_id: int
    tipo_bloqueio: str  # ferias, emergencia, particular, manutencao
    motivo: Optional[str] = None
    data_inicio: str  # ISO format datetime
    data_fim: str     # ISO format datetime

class BloqueioResponse(BaseModel):
    id: int
    medico_id: int
    tipo_bloqueio: str
    motivo: Optional[str]
    data_inicio: str
    data_fim: str
    ativo: bool

@router.get("/bloqueios")
async def listar_bloqueios(
    medico_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lista bloqueios de agenda de um médico"""
    bloqueios = db.query(BloqueioAgenda).filter(
        BloqueioAgenda.medico_id == medico_id,
        BloqueioAgenda.ativo == True
    ).order_by(BloqueioAgenda.data_inicio.desc()).all()

    return {
        "sucesso": True,
        "bloqueios": [
            {
                "id": b.id,
                "medico_id": b.medico_id,
                "tipo_bloqueio": b.tipo_bloqueio,
                "motivo": b.motivo,
                "data_inicio": b.data_inicio.isoformat() if b.data_inicio else None,
                "data_fim": b.data_fim.isoformat() if b.data_fim else None,
                "ativo": b.ativo
            }
            for b in bloqueios
        ]
    }

@router.post("/bloqueios")
async def criar_bloqueio(
    dados: BloqueioRequest,
    cancelar_agendamentos: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cria um novo bloqueio de agenda"""
    try:
        # Converter datas
        data_inicio = datetime.fromisoformat(dados.data_inicio.replace('Z', '+00:00'))
        data_fim = datetime.fromisoformat(dados.data_fim.replace('Z', '+00:00'))

        # Verificar conflitos com agendamentos existentes
        from app.models.agendamento import Agendamento
        conflitos = db.query(Agendamento).filter(
            Agendamento.medico_id == dados.medico_id,
            Agendamento.data_hora >= data_inicio,
            Agendamento.data_hora <= data_fim,
            Agendamento.status.in_(['agendado', 'confirmado'])
        ).all()

        if conflitos and not cancelar_agendamentos:
            return {
                "sucesso": False,
                "mensagem": "Existem agendamentos no período",
                "conflitos": [
                    {
                        "id": a.id,
                        "paciente_nome": a.paciente.nome if a.paciente else "Desconhecido",
                        "data_hora": a.data_hora.isoformat()
                    }
                    for a in conflitos
                ]
            }

        # Se cancelar_agendamentos=True, cancelar os conflitos
        if cancelar_agendamentos and conflitos:
            for agendamento in conflitos:
                agendamento.status = 'cancelado'
                agendamento.observacoes = f"Cancelado automaticamente - {dados.tipo_bloqueio}: {dados.motivo or 'Sem motivo'}"

        # Criar bloqueio
        bloqueio = BloqueioAgenda(
            medico_id=dados.medico_id,
            tipo_bloqueio=dados.tipo_bloqueio,
            motivo=dados.motivo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            ativo=True
        )
        db.add(bloqueio)
        db.commit()
        db.refresh(bloqueio)

        return {
            "sucesso": True,
            "mensagem": "Bloqueio criado com sucesso",
            "bloqueio": {
                "id": bloqueio.id,
                "medico_id": bloqueio.medico_id,
                "tipo_bloqueio": bloqueio.tipo_bloqueio,
                "data_inicio": bloqueio.data_inicio.isoformat(),
                "data_fim": bloqueio.data_fim.isoformat()
            },
            "agendamentos_cancelados": len(conflitos) if cancelar_agendamentos else 0
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar bloqueio: {str(e)}")

@router.delete("/bloqueios/{bloqueio_id}")
async def deletar_bloqueio(
    bloqueio_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove um bloqueio de agenda"""
    bloqueio = db.query(BloqueioAgenda).filter(BloqueioAgenda.id == bloqueio_id).first()

    if not bloqueio:
        raise HTTPException(status_code=404, detail="Bloqueio não encontrado")

    try:
        bloqueio.ativo = False
        db.commit()
        return {"sucesso": True, "mensagem": "Bloqueio removido com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao remover bloqueio: {str(e)}")
