# app/api/medico_config.py
# Rotas para configuração individualizada de médicos
# Sistema Horário Inteligente - Marco

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import time, datetime
from app.database import get_db
from app.api.auth import get_current_user
from app.utils.auth_middleware import AuthMiddleware

router = APIRouter()

# ================== SCHEMAS ==================

class ConfiguracaoMedicoUpdate(BaseModel):
    """Schema para atualizar configurações do médico"""
    intervalo_consulta: Optional[int] = None
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    dias_atendimento: Optional[str] = None
    intervalo_almoco_inicio: Optional[str] = None
    intervalo_almoco_fim: Optional[str] = None
    antecedencia_minima: Optional[int] = None
    antecedencia_maxima: Optional[int] = None
    lembrete_24h: Optional[bool] = None
    lembrete_2h: Optional[bool] = None

class HorarioAtendimentoCreate(BaseModel):
    """Schema para criar horário de atendimento"""
    dia_semana: int  # 1=Segunda, 2=Terça, ..., 7=Domingo
    hora_inicio: str  # Formato HH:MM
    hora_fim: str  # Formato HH:MM

class BloqueioAgendaCreate(BaseModel):
    """Schema para criar bloqueio de agenda"""
    data_inicio: str  # Formato YYYY-MM-DD HH:MM
    data_fim: str  # Formato YYYY-MM-DD HH:MM
    motivo: str
    tipo: Optional[str] = "bloqueio"  # bloqueio, ferias, almoco, etc

class NotificacoesMedicoUpdate(BaseModel):
    """Schema para atualizar configurações de notificações do médico"""
    notificar_novos: Optional[bool] = None
    notificar_reagendamentos: Optional[bool] = None
    notificar_cancelamentos: Optional[bool] = None
    notificar_confirmacoes: Optional[bool] = None
    canal_whatsapp: Optional[bool] = None
    canal_email: Optional[bool] = None
    whatsapp_numero: Optional[str] = None
    email: Optional[str] = None

# ================== ROTAS DE CONFIGURAÇÃO ==================

@router.get("/medicos/{medico_id}/configuracoes")
async def obter_configuracoes(
    medico_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtém as configurações do médico
    - Médicos: apenas suas próprias configurações
    - Secretárias: podem ver configurações de qualquer médico
    """
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        # Buscar configurações
        result = db.execute(text("""
            SELECT
                intervalo_consulta,
                horario_inicio,
                horario_fim,
                dias_atendimento,
                intervalo_almoco_inicio,
                intervalo_almoco_fim,
                tempo_antes_consulta,
                consultas_simultaneas,
                antecedencia_minima,
                antecedencia_maxima,
                permite_reagendamento,
                limite_reagendamentos,
                lembrete_24h,
                lembrete_2h,
                confirmacao_automatica,
                ativo,
                created_at,
                updated_at
            FROM configuracoes_medico
            WHERE medico_id = :medico_id
        """), {"medico_id": medico_id})

        config = result.fetchone()

        if not config:
            # Retornar configurações padrão se não existirem
            return {
                "sucesso": True,
                "configuracoes": {
                    "intervalo_consulta": 30,
                    "horario_inicio": "08:00",
                    "horario_fim": "18:00",
                    "dias_atendimento": "[1,2,3,4,5]",
                    "intervalo_almoco_inicio": None,
                    "intervalo_almoco_fim": None,
                    "antecedencia_minima": 60,
                    "antecedencia_maxima": 8760,
                    "lembrete_24h": True,
                    "lembrete_2h": True,
                    "existe": False
                }
            }

        return {
            "sucesso": True,
            "configuracoes": {
                "intervalo_consulta": config.intervalo_consulta,
                "horario_inicio": config.horario_inicio,
                "horario_fim": config.horario_fim,
                "dias_atendimento": config.dias_atendimento,
                "intervalo_almoco_inicio": config.intervalo_almoco_inicio,
                "intervalo_almoco_fim": config.intervalo_almoco_fim,
                "tempo_antes_consulta": config.tempo_antes_consulta,
                "consultas_simultaneas": config.consultas_simultaneas,
                "antecedencia_minima": config.antecedencia_minima,
                "antecedencia_maxima": config.antecedencia_maxima,
                "permite_reagendamento": config.permite_reagendamento,
                "limite_reagendamentos": config.limite_reagendamentos,
                "lembrete_24h": config.lembrete_24h,
                "lembrete_2h": config.lembrete_2h,
                "confirmacao_automatica": config.confirmacao_automatica,
                "ativo": config.ativo,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                "existe": True
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter configurações: {str(e)}")

@router.put("/medicos/{medico_id}/configuracoes")
async def atualizar_configuracoes(
    medico_id: int,
    dados: ConfiguracaoMedicoUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Atualiza as configurações do médico
    - Médicos: apenas suas próprias configurações
    - Secretárias: podem alterar configurações de qualquer médico
    """
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        # Verificar se configuração já existe
        result = db.execute(text("""
            SELECT id FROM configuracoes_medico
            WHERE medico_id = :medico_id
        """), {"medico_id": medico_id})

        config_existe = result.fetchone()

        if not config_existe:
            # Criar nova configuração
            insert_fields = ["medico_id"]
            insert_values = [":medico_id"]
            params = {"medico_id": medico_id}

            for field, value in dados.dict(exclude_unset=True).items():
                if value is not None:
                    insert_fields.append(field)
                    insert_values.append(f":{field}")
                    params[field] = value

            query = f"""
                INSERT INTO configuracoes_medico ({', '.join(insert_fields)})
                VALUES ({', '.join(insert_values)})
            """
            db.execute(text(query), params)
        else:
            # Atualizar configuração existente
            updates = []
            params = {"medico_id": medico_id}

            for field, value in dados.dict(exclude_unset=True).items():
                if value is not None:
                    updates.append(f"{field} = :{field}")
                    params[field] = value

            if not updates:
                raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

            updates.append("updated_at = NOW()")
            query = f"""
                UPDATE configuracoes_medico
                SET {', '.join(updates)}
                WHERE medico_id = :medico_id
            """
            db.execute(text(query), params)

        db.commit()

        return {
            "sucesso": True,
            "mensagem": "Configurações atualizadas com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar configurações: {str(e)}")

# ================== ROTAS DE FORMAS DE PAGAMENTO ==================

@router.get("/medicos/{medico_id}/formas-pagamento")
async def obter_formas_pagamento(
    medico_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtém as formas de pagamento aceitas pelo médico.
    Retorna Particular (se configurado) + Convênios aceitos.
    Usado para popular o dropdown de forma de pagamento no agendamento.
    """
    try:
        # Buscar dados do médico
        result = db.execute(text("""
            SELECT valor_consulta_particular, convenios_aceitos
            FROM medicos
            WHERE id = :medico_id AND ativo = true
        """), {"medico_id": medico_id})

        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Médico não encontrado")

        formas_pagamento = []

        # Adicionar Particular se tiver valor configurado
        valor_particular = row[0]
        if valor_particular and float(valor_particular) > 0:
            formas_pagamento.append({
                "id": "particular",
                "nome": "Particular",
                "valor": float(valor_particular),
                "tipo": "particular"
            })
        else:
            # Sempre incluir Particular, mesmo sem valor
            formas_pagamento.append({
                "id": "particular",
                "nome": "Particular",
                "valor": None,
                "tipo": "particular"
            })

        # Adicionar convênios aceitos pelo médico
        convenios_aceitos = row[1]
        if convenios_aceitos:
            # convenios_aceitos é um JSONB com lista de convênios
            import json
            if isinstance(convenios_aceitos, str):
                convenios_aceitos = json.loads(convenios_aceitos)

            for i, conv in enumerate(convenios_aceitos):
                if isinstance(conv, dict):
                    formas_pagamento.append({
                        "id": f"convenio_{i}",
                        "nome": conv.get("nome", "Convênio"),
                        "valor": conv.get("valor"),
                        "codigo": conv.get("codigo", ""),
                        "tipo": "convenio"
                    })
                elif isinstance(conv, str):
                    # Compatibilidade com formato antigo (lista de strings)
                    formas_pagamento.append({
                        "id": f"convenio_{i}",
                        "nome": conv,
                        "valor": None,
                        "tipo": "convenio"
                    })

        return {
            "sucesso": True,
            "medico_id": medico_id,
            "formas_pagamento": formas_pagamento
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar formas de pagamento: {str(e)}")

# ================== ROTAS DE HORÁRIOS DE ATENDIMENTO ==================

@router.get("/medicos/{medico_id}/horarios")
async def listar_horarios(
    medico_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lista os horários de atendimento do médico"""
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        result = db.execute(text("""
            SELECT id, dia_semana, hora_inicio, hora_fim, ativo, created_at
            FROM horarios_atendimento
            WHERE medico_id = :medico_id AND ativo = true
            ORDER BY dia_semana, hora_inicio
        """), {"medico_id": medico_id})

        horarios = []
        dias_semana = {
            1: "Segunda-feira",
            2: "Terça-feira",
            3: "Quarta-feira",
            4: "Quinta-feira",
            5: "Sexta-feira",
            6: "Sábado",
            7: "Domingo"
        }

        for row in result:
            horarios.append({
                "id": row.id,
                "dia_semana": row.dia_semana,
                "dia_semana_nome": dias_semana.get(row.dia_semana, "Desconhecido"),
                "hora_inicio": str(row.hora_inicio),
                "hora_fim": str(row.hora_fim),
                "ativo": row.ativo,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })

        return {
            "sucesso": True,
            "horarios": horarios
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar horários: {str(e)}")

@router.post("/medicos/{medico_id}/horarios")
async def criar_horario(
    medico_id: int,
    dados: HorarioAtendimentoCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cria um novo horário de atendimento para o médico"""
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        # Validar dia da semana
        if dados.dia_semana < 1 or dados.dia_semana > 7:
            raise HTTPException(status_code=400, detail="Dia da semana inválido (1-7)")

        # Inserir horário
        result = db.execute(text("""
            INSERT INTO horarios_atendimento
            (medico_id, dia_semana, hora_inicio, hora_fim, ativo, created_at)
            VALUES
            (:medico_id, :dia_semana, :hora_inicio, :hora_fim, true, NOW())
            RETURNING id
        """), {
            "medico_id": medico_id,
            "dia_semana": dados.dia_semana,
            "hora_inicio": dados.hora_inicio,
            "hora_fim": dados.hora_fim
        })

        horario_id = result.scalar()
        db.commit()

        return {
            "sucesso": True,
            "mensagem": "Horário criado com sucesso",
            "horario_id": horario_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar horário: {str(e)}")

@router.delete("/medicos/{medico_id}/horarios/{horario_id}")
async def deletar_horario(
    medico_id: int,
    horario_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove um horário de atendimento"""
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        # Verificar se horário pertence ao médico
        result = db.execute(text("""
            SELECT id FROM horarios_atendimento
            WHERE id = :horario_id AND medico_id = :medico_id
        """), {"horario_id": horario_id, "medico_id": medico_id})

        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Horário não encontrado")

        # Marcar como inativo (soft delete)
        db.execute(text("""
            UPDATE horarios_atendimento
            SET ativo = false
            WHERE id = :horario_id
        """), {"horario_id": horario_id})

        db.commit()

        return {
            "sucesso": True,
            "mensagem": "Horário removido com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao remover horário: {str(e)}")

# ================== ROTAS DE BLOQUEIOS DE AGENDA ==================

@router.get("/medicos/{medico_id}/bloqueios")
async def listar_bloqueios(
    medico_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lista os bloqueios de agenda do médico"""
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        result = db.execute(text("""
            SELECT id, data_inicio, data_fim, motivo, tipo, ativo, created_at
            FROM bloqueios_agenda
            WHERE medico_id = :medico_id AND ativo = true
            ORDER BY data_inicio DESC
        """), {"medico_id": medico_id})

        bloqueios = []
        for row in result:
            bloqueios.append({
                "id": row.id,
                "data_inicio": row.data_inicio.isoformat(),
                "data_fim": row.data_fim.isoformat(),
                "motivo": row.motivo,
                "tipo": row.tipo,
                "ativo": row.ativo,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })

        return {
            "sucesso": True,
            "bloqueios": bloqueios
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar bloqueios: {str(e)}")

@router.get("/medicos/{medico_id}/bloqueios/validar")
async def validar_bloqueio(
    medico_id: int,
    data_inicio: str,
    data_fim: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Valida se há conflitos de agendamentos no período do bloqueio
    Retorna lista de agendamentos conflitantes
    """
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        # Buscar agendamentos no período (confirmados ou agendados)
        result = db.execute(text("""
            SELECT
                a.id,
                a.data_hora,
                a.status,
                a.motivo_consulta,
                p.nome as paciente_nome,
                p.telefone as paciente_telefone
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
              AND a.data_hora >= :data_inicio
              AND a.data_hora <= :data_fim
              AND a.status IN ('agendado', 'confirmado')
            ORDER BY a.data_hora
        """), {
            "medico_id": medico_id,
            "data_inicio": data_inicio,
            "data_fim": data_fim
        })

        agendamentos_conflitantes = []
        for row in result:
            agendamentos_conflitantes.append({
                "id": row.id,
                "data_hora": row.data_hora.isoformat(),
                "status": row.status,
                "motivo_consulta": row.motivo_consulta,
                "paciente_nome": row.paciente_nome,
                "paciente_telefone": row.paciente_telefone
            })

        tem_conflito = len(agendamentos_conflitantes) > 0

        return {
            "sucesso": True,
            "tem_conflito": tem_conflito,
            "total_conflitos": len(agendamentos_conflitantes),
            "agendamentos_conflitantes": agendamentos_conflitantes,
            "mensagem": f"{'⚠️ Atenção: ' if tem_conflito else '✅ '}"
                       f"{len(agendamentos_conflitantes)} agendamento(s) encontrado(s) no período"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao validar bloqueio: {str(e)}")

@router.post("/medicos/{medico_id}/bloqueios")
async def criar_bloqueio(
    medico_id: int,
    dados: BloqueioAgendaCreate,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Cria um novo bloqueio de agenda

    Parâmetros:
    - force: Se True, cancela automaticamente agendamentos conflitantes
             Se False (padrão), retorna erro se houver conflitos
    """
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        # Verificar se há agendamentos conflitantes
        result = db.execute(text("""
            SELECT
                a.id,
                a.data_hora,
                p.nome as paciente_nome
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
              AND a.data_hora >= :data_inicio
              AND a.data_hora <= :data_fim
              AND a.status IN ('agendado', 'confirmado')
            ORDER BY a.data_hora
        """), {
            "medico_id": medico_id,
            "data_inicio": dados.data_inicio,
            "data_fim": dados.data_fim
        })

        agendamentos_conflitantes = result.fetchall()

        # Se há conflitos e não está forçando, retornar erro com detalhes
        if agendamentos_conflitantes and not force:
            conflitos = []
            for ag in agendamentos_conflitantes:
                conflitos.append({
                    "id": ag.id,
                    "data_hora": ag.data_hora.isoformat(),
                    "paciente_nome": ag.paciente_nome
                })

            return {
                "sucesso": False,
                "erro": "conflito_agendamentos",
                "mensagem": f"⚠️ Existem {len(agendamentos_conflitantes)} agendamento(s) no período selecionado",
                "total_conflitos": len(agendamentos_conflitantes),
                "agendamentos_conflitantes": conflitos,
                "sugestao": "Cancele manualmente os agendamentos ou use force=true para cancelar automaticamente"
            }

        # Se force=true, cancelar agendamentos conflitantes
        agendamentos_cancelados = []
        if force and agendamentos_conflitantes:
            for ag in agendamentos_conflitantes:
                db.execute(text("""
                    UPDATE agendamentos
                    SET status = 'cancelado',
                        atualizado_em = NOW()
                    WHERE id = :ag_id
                """), {"ag_id": ag.id})

                agendamentos_cancelados.append({
                    "id": ag.id,
                    "data_hora": ag.data_hora.isoformat(),
                    "paciente_nome": ag.paciente_nome
                })

        # Inserir bloqueio
        result = db.execute(text("""
            INSERT INTO bloqueios_agenda
            (medico_id, data_inicio, data_fim, motivo, tipo, ativo, created_at)
            VALUES
            (:medico_id, :data_inicio, :data_fim, :motivo, :tipo, true, NOW())
            RETURNING id
        """), {
            "medico_id": medico_id,
            "data_inicio": dados.data_inicio,
            "data_fim": dados.data_fim,
            "motivo": dados.motivo,
            "tipo": dados.tipo
        })

        bloqueio_id = result.scalar()
        db.commit()

        mensagem = "Bloqueio criado com sucesso"
        if agendamentos_cancelados:
            mensagem += f" ({len(agendamentos_cancelados)} agendamento(s) cancelado(s))"

        return {
            "sucesso": True,
            "mensagem": mensagem,
            "bloqueio_id": bloqueio_id,
            "agendamentos_cancelados": agendamentos_cancelados if agendamentos_cancelados else []
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar bloqueio: {str(e)}")

@router.delete("/medicos/{medico_id}/bloqueios/{bloqueio_id}")
async def deletar_bloqueio(
    medico_id: int,
    bloqueio_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove um bloqueio de agenda"""
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        # Verificar se bloqueio pertence ao médico
        result = db.execute(text("""
            SELECT id FROM bloqueios_agenda
            WHERE id = :bloqueio_id AND medico_id = :medico_id
        """), {"bloqueio_id": bloqueio_id, "medico_id": medico_id})

        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Bloqueio não encontrado")

        # Marcar como inativo (soft delete)
        db.execute(text("""
            UPDATE bloqueios_agenda
            SET ativo = false
            WHERE id = :bloqueio_id
        """), {"bloqueio_id": bloqueio_id})

        db.commit()

        return {
            "sucesso": True,
            "mensagem": "Bloqueio removido com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao remover bloqueio: {str(e)}")

# ================== ROTAS DE NOTIFICAÇÕES ==================

@router.get("/medicos/{medico_id}/notificacoes")
async def obter_notificacoes(
    medico_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtém as configurações de notificações do médico
    - Médicos: apenas suas próprias configurações
    - Secretárias: podem ver configurações de qualquer médico
    """
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        result = db.execute(text("""
            SELECT
                notificar_novos,
                notificar_reagendamentos,
                notificar_cancelamentos,
                notificar_confirmacoes,
                canal_whatsapp,
                canal_email,
                whatsapp_numero,
                email,
                criado_em,
                atualizado_em
            FROM notificacoes_medico
            WHERE medico_id = :medico_id
              AND cliente_id = :cliente_id
        """), {
            "medico_id": medico_id,
            "cliente_id": current_user["cliente_id"]
        })

        config = result.fetchone()

        if not config:
            # Retornar configurações padrão se não existirem
            return {
                "sucesso": True,
                "notificacoes": {
                    "notificar_novos": True,
                    "notificar_reagendamentos": True,
                    "notificar_cancelamentos": True,
                    "notificar_confirmacoes": False,
                    "canal_whatsapp": True,
                    "canal_email": False,
                    "whatsapp_numero": None,
                    "email": None,
                    "existe": False
                }
            }

        return {
            "sucesso": True,
            "notificacoes": {
                "notificar_novos": config[0],
                "notificar_reagendamentos": config[1],
                "notificar_cancelamentos": config[2],
                "notificar_confirmacoes": config[3],
                "canal_whatsapp": config[4],
                "canal_email": config[5],
                "whatsapp_numero": config[6],
                "email": config[7],
                "criado_em": config[8].isoformat() if config[8] else None,
                "atualizado_em": config[9].isoformat() if config[9] else None,
                "existe": True
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter notificações: {str(e)}")

@router.put("/medicos/{medico_id}/notificacoes")
async def atualizar_notificacoes(
    medico_id: int,
    dados: NotificacoesMedicoUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Atualiza as configurações de notificações do médico
    - Médicos: apenas suas próprias configurações
    - Secretárias: podem alterar configurações de qualquer médico
    """
    # Verificar permissão de acesso
    AuthMiddleware.check_medico_access(current_user, medico_id)

    try:
        # Verificar se configuração já existe
        result = db.execute(text("""
            SELECT id FROM notificacoes_medico
            WHERE medico_id = :medico_id
              AND cliente_id = :cliente_id
        """), {
            "medico_id": medico_id,
            "cliente_id": current_user["cliente_id"]
        })

        config_existe = result.fetchone()

        if not config_existe:
            # Criar nova configuração
            insert_fields = ["medico_id", "cliente_id"]
            insert_values = [":medico_id", ":cliente_id"]
            params = {
                "medico_id": medico_id,
                "cliente_id": current_user["cliente_id"]
            }

            for field, value in dados.dict(exclude_unset=True).items():
                if value is not None:
                    insert_fields.append(field)
                    insert_values.append(f":{field}")
                    params[field] = value

            query = f"""
                INSERT INTO notificacoes_medico ({', '.join(insert_fields)})
                VALUES ({', '.join(insert_values)})
            """
            db.execute(text(query), params)
        else:
            # Atualizar configuração existente
            updates = []
            params = {
                "medico_id": medico_id,
                "cliente_id": current_user["cliente_id"]
            }

            for field, value in dados.dict(exclude_unset=True).items():
                if value is not None:
                    updates.append(f"{field} = :{field}")
                    params[field] = value

            if not updates:
                raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

            updates.append("atualizado_em = NOW()")
            query = f"""
                UPDATE notificacoes_medico
                SET {', '.join(updates)}
                WHERE medico_id = :medico_id
                  AND cliente_id = :cliente_id
            """
            db.execute(text(query), params)

        db.commit()

        return {
            "sucesso": True,
            "mensagem": "Configurações de notificações atualizadas com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar notificações: {str(e)}")
