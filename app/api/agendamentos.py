from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, date
from app.database import get_db
from app.services.agendamento_service import AgendamentoService
from app.services.notification_service import get_notification_service
from app.services.lembrete_service import lembrete_service
from app.api.auth import get_current_user
from app.utils.auth_middleware import AuthMiddleware, get_medico_filter_dependency
from app.utils.phone_utils import normalize_phone
from app.utils.timezone_helper import parse_datetime_brazil, now_brazil, format_brazil
from app.services.websocket_manager import websocket_manager

router = APIRouter()

# Schema para criar agendamento - CORRIGIDO
class AgendamentoCreate(BaseModel):
    paciente_nome: str
    paciente_telefone: str
    data: str
    hora: str
    medico_id: int = 1
    duracao_minutos: int = 30  # Duração customizável (padrão 30min)
    motivo_consulta: Optional[str] = None  # Aceita do frontend
    motivo: Optional[str] = None  # Retrocompatibilidade
    # Campos opcionais adicionais
    paciente_cpf: Optional[str] = None
    paciente_email: Optional[str] = None
    paciente_data_nascimento: Optional[str] = None
    # Forma de pagamento e valor
    forma_pagamento: Optional[str] = None  # 'particular', 'convenio_0', etc
    valor_consulta: Optional[str] = None  # Valor da consulta

@router.post("/agendamentos")
async def criar_agendamento(
    dados: AgendamentoCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cria um novo agendamento manual - MULTI-TENANT"""
    try:
        # Pegar cliente_id do usuário logado (do JWT)
        cliente_id = current_user.get("cliente_id")
        if not cliente_id:
            raise HTTPException(status_code=400, detail="cliente_id não encontrado no token")

        # Determinar o motivo (prioriza motivo_consulta)
        motivo_final = dados.motivo_consulta or dados.motivo or "Consulta"

        # ========== NORMALIZAR TELEFONE PARA FORMATO WHATSAPP ==========
        # Garante que o telefone seja salvo no mesmo formato do WhatsApp
        # Exemplo: (24) 98849-3257 → 5524988493257
        # Isso permite que futuras interações via WhatsApp reconheçam o paciente
        telefone_normalizado = normalize_phone(dados.paciente_telefone)
        # ================================================================

        # Buscar ou criar paciente (filtra por cliente_id)
        paciente = db.execute(text("""
            SELECT id FROM pacientes
            WHERE telefone = :tel AND cliente_id = :cli_id
            LIMIT 1
        """), {"tel": telefone_normalizado, "cli_id": cliente_id}).fetchone()

        if not paciente:
            # Verificar se telefone já existe (pode ser de outro cliente)
            paciente_existente = db.execute(text("""
                SELECT id, cliente_id FROM pacientes WHERE telefone = :tel LIMIT 1
            """), {"tel": telefone_normalizado}).fetchone()

            if paciente_existente:
                # Telefone já existe - usar o paciente existente
                paciente_id = paciente_existente.id
            else:
                # Criar paciente novo
                try:
                    result = db.execute(text("""
                    INSERT INTO pacientes (nome, telefone, cpf, email, data_nascimento, cliente_id, convenio, preferencia_audio, criado_em, atualizado_em)
                    VALUES (:nome, :tel, :cpf, :email, :data_nasc, :cli_id, 'Particular', 'auto', NOW(), NOW())
                    RETURNING id
                    """), {
                        "nome": dados.paciente_nome,
                        "tel": telefone_normalizado,
                        "cpf": getattr(dados, 'paciente_cpf', None),
                        "email": getattr(dados, 'paciente_email', None),
                        "data_nasc": getattr(dados, 'paciente_data_nascimento', None),
                        "cli_id": cliente_id
                    })
                    paciente_id = result.scalar()
                except Exception as sql_error:
                    db.rollback()
                    return {"sucesso": False, "erro": f"Erro ao criar paciente: {str(sql_error)}"}
        else:
            paciente_id = paciente.id
            # Atualizar paciente se campos adicionais foram fornecidos
            cpf = getattr(dados, 'paciente_cpf', None)
            email = getattr(dados, 'paciente_email', None)
            data_nasc = getattr(dados, 'paciente_data_nascimento', None)
            if cpf or email or data_nasc:
                db.execute(text("""
                    UPDATE pacientes
                    SET cpf = COALESCE(:cpf, cpf),
                        email = COALESCE(:email, email),
                        data_nascimento = COALESCE(:data_nasc, data_nascimento),
                        atualizado_em = NOW()
                    WHERE id = :pac_id
                """), {
                    "cpf": cpf,
                    "email": email,
                    "data_nasc": data_nasc,
                    "pac_id": paciente_id
                })
        
        # Criar agendamento - TIMEZONE-AWARE (horário de Brasília)
        data_hora_tz = parse_datetime_brazil(dados.data, dados.hora)

        # VALIDAÇÃO: Não permitir agendamentos no passado
        from datetime import datetime
        import pytz
        tz_brazil = pytz.timezone('America/Sao_Paulo')
        agora = datetime.now(tz_brazil)

        if data_hora_tz < agora:
            return {"sucesso": False, "erro": "Não é possível agendar para datas ou horários passados"}

        # Validar duração (mínimo 5 minutos, máximo 480 minutos = 8 horas)
        duracao = max(5, min(480, dados.duracao_minutos))

        # VALIDAÇÃO DE CONFLITO: Verificar sobreposição com agendamentos existentes
        # Conflito ocorre quando: novo_inicio < existente_fim AND novo_fim > existente_inicio
        # Status que LIBERAM o horário: cancelado, faltou, remarcado
        conflito = db.execute(text("""
            SELECT a.id, a.data_hora, a.duracao_minutos, p.nome as paciente
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE a.medico_id = :medico_id
            AND a.status NOT IN ('cancelado', 'faltou', 'remarcado')
            AND (
                -- Novo agendamento começa antes do existente terminar
                :novo_inicio < (a.data_hora + (COALESCE(a.duracao_minutos, 30) || ' minutes')::interval)
                AND
                -- Novo agendamento termina depois do existente começar
                (:novo_inicio + (:duracao || ' minutes')::interval) > a.data_hora
            )
        """), {
            "medico_id": dados.medico_id,
            "novo_inicio": data_hora_tz,
            "duracao": duracao
        }).fetchone()

        if conflito:
            # Converter para horário de Brasília para exibição
            hora_conflito_utc = conflito[1]
            hora_conflito_br = hora_conflito_utc.astimezone(tz_brazil).strftime('%H:%M')
            return {
                "sucesso": False,
                "erro": f"Conflito de horário: já existe agendamento de {conflito[3]} às {hora_conflito_br} ({conflito[2]} min)"
            }

        # Determinar valor da consulta
        valor_consulta = dados.valor_consulta
        forma_pagamento = dados.forma_pagamento or 'particular'

        # Se valor não foi enviado, buscar do cadastro do médico
        if not valor_consulta:
            import json
            medico_dados = db.execute(text("""
                SELECT valor_consulta_particular, convenios_aceitos
                FROM medicos WHERE id = :med_id
            """), {"med_id": dados.medico_id}).fetchone()

            if medico_dados:
                if forma_pagamento == 'particular':
                    valor_consulta = str(medico_dados[0]) if medico_dados[0] else None
                elif forma_pagamento.startswith('convenio_') and medico_dados[1]:
                    convenios = medico_dados[1]
                    if isinstance(convenios, str):
                        convenios = json.loads(convenios)
                    try:
                        idx = int(forma_pagamento.replace('convenio_', ''))
                        if idx < len(convenios):
                            valor_consulta = str(convenios[idx].get('valor', ''))
                    except (ValueError, IndexError):
                        pass

        result = db.execute(text("""
            INSERT INTO agendamentos
            (paciente_id, medico_id, data_hora, duracao_minutos, status, tipo_atendimento,
             motivo_consulta, valor_consulta, forma_pagamento, lembrete_24h_enviado, lembrete_3h_enviado, lembrete_1h_enviado,
             criado_em, atualizado_em)
            VALUES
            (:pac_id, :med_id, :dt, :duracao, 'confirmado', 'consulta',
             :motivo, :valor, :forma_pag, FALSE, FALSE, FALSE, NOW(), NOW())
            RETURNING id
        """), {
            "pac_id": paciente_id,
            "med_id": dados.medico_id,
            "dt": data_hora_tz,  # Agora timezone-aware!
            "duracao": duracao,
            "motivo": motivo_final,
            "valor": valor_consulta,
            "forma_pag": forma_pagamento
        })
        
        agendamento_id = result.scalar()
        db.commit()

        # Criar lembrete de 24h para o agendamento
        try:
            lembrete_service.criar_lembretes_para_agendamento(
                db=db,
                agendamento_id=agendamento_id,
                tipos=["24h"]
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro ao criar lembrete para agendamento {agendamento_id}: {e}")

        # Notificar médico sobre novo agendamento
        try:
            notification_service = get_notification_service(db)
            await notification_service.notificar_medico(
                medico_id=dados.medico_id,
                cliente_id=cliente_id,
                evento="novo",
                dados_agendamento={
                    "paciente_nome": dados.paciente_nome,
                    "data_hora": data_hora_tz
                }
            )
        except Exception as e:
            # Log do erro, mas não falha o agendamento
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro ao notificar médico sobre novo agendamento: {e}")

        # Notificar via WebSocket para atualizar calendários em tempo real
        try:
            await websocket_manager.send_novo_agendamento(cliente_id, {
                "id": agendamento_id,
                "paciente_nome": dados.paciente_nome,
                "medico_id": dados.medico_id,
                "data_hora": data_hora_tz.isoformat(),
                "status": "confirmado"
            })
        except Exception as ws_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[WebSocket] Erro ao notificar novo agendamento: {ws_error}")

        return {
            "sucesso": True,
            "mensagem": "Agendamento criado com sucesso",
            "agendamento_id": agendamento_id,
            "paciente_id": paciente_id
        }
    except Exception as e:
        db.rollback()
        return {
            "sucesso": False,
            "erro": str(e)
        }

@router.get("/agendamentos/calendario")
async def listar_calendario(
    db: Session = Depends(get_db),
    medico_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    medico_filter: Optional[int] = Depends(get_medico_filter_dependency)
):
    """
    Lista agendamentos e bloqueios para o calendário
    - Médicos: veem apenas sua própria agenda
    - Secretárias: veem todas as agendas ou filtram por médico específico
    """
    try:
        # Determinar filtro de médico
        # Se é médico, ignora o parâmetro medico_id e usa sempre seu próprio ID
        # Se é secretária, pode filtrar por médico específico ou ver todos
        if medico_filter is not None:
            # Usuário é médico - sempre filtra por seu próprio ID
            final_medico_id = medico_filter
        else:
            # Usuário é secretária - pode filtrar por médico ou ver todos
            final_medico_id = medico_id if medico_id else 0

        # Buscar agendamentos (filtrado por cliente_id para multi-tenant)
        # IMPORTANTE: Ocultar do calendário: cancelado, remarcado, faltou
        # Esses registros permanecem no banco para estatísticas, mas não devem
        # aparecer no calendário para não confundir o usuário
        cliente_id = current_user.get("cliente_id")
        result = db.execute(text("""
            SELECT
                a.id,
                a.data_hora,
                a.duracao_minutos,
                a.status,
                a.tipo_atendimento,
                a.motivo_consulta,
                a.medico_id,
                p.nome as paciente_nome,
                p.telefone as paciente_telefone,
                m.nome as medico_nome,
                m.especialidade
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            JOIN medicos m ON a.medico_id = m.id
            WHERE (:medico_id = 0 OR a.medico_id = :medico_id)
            AND m.cliente_id = :cliente_id
            AND a.data_hora >= CURRENT_DATE - INTERVAL '30 days'
            AND a.status NOT IN ('cancelado', 'remarcado', 'faltou')
            ORDER BY a.data_hora
        """), {"medico_id": final_medico_id, "cliente_id": cliente_id})
        
        agendamentos = []
        for row in result:
            # Calcular horário final usando duração real do agendamento
            duracao = row.duracao_minutos or 30  # Fallback para 30 se null
            horario_final = row.data_hora + timedelta(minutes=duracao)

            agendamentos.append({
                "id": row.id,
                "title": f"{row.paciente_nome} - {row.tipo_atendimento}",
                "start": row.data_hora.isoformat(),
                "end": horario_final.isoformat(),  # Adicionar horário final para visualização diária
                "medico_id": row.medico_id,  # Adicionar medico_id para filtro por cor
                "backgroundColor": "#10b981" if row.status == "confirmado" else "#f59e0b",
                "borderColor": "#10b981" if row.status == "confirmado" else "#f59e0b",
                "extendedProps": {
                    "paciente": row.paciente_nome,
                    "telefone": row.paciente_telefone,
                    "medico": row.medico_nome,
                    "especialidade": row.especialidade,
                    "tipo": row.tipo_atendimento,
                    "status": row.status,
                    "motivo": row.motivo_consulta,
                    "medico_id": row.medico_id,  # Também nos extendedProps para fácil acesso
                    "duracao_minutos": duracao  # Incluir duração para exibição
                }
            })
        
        return {"eventos": agendamentos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/medicos")
async def listar_medicos(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    medico_filter: Optional[int] = Depends(get_medico_filter_dependency)
):
    """
    Lista médicos disponíveis
    - Médicos: veem apenas a si mesmos
    - Secretárias: veem todos os médicos
    """
    try:
        # Se medico_filter não for None, usuário é médico e só vê a si mesmo
        if medico_filter is not None:
            result = db.execute(text("""
                SELECT id, nome, especialidade, crm, convenios_aceitos
                FROM medicos
                WHERE id = :medico_id AND ativo = true AND is_secretaria = false
            """), {"medico_id": medico_filter})
        else:
            # Secretária vê todos os médicos DO SEU CLIENTE (excluindo secretárias)
            cliente_id = current_user.get("cliente_id")
            result = db.execute(text("""
                SELECT id, nome, especialidade, crm, convenios_aceitos
                FROM medicos
                WHERE ativo = true AND cliente_id = :cliente_id AND is_secretaria = false
                ORDER BY nome
            """), {"cliente_id": cliente_id})

        medicos = []
        for row in result:
            medicos.append({
                "id": row.id,
                "nome": row.nome,
                "especialidade": row.especialidade,
                "crm": row.crm,
                "convenios_aceitos": row.convenios_aceitos
            })

        return {"sucesso": True, "medicos": medicos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/horarios-disponiveis")
async def obter_horarios_disponiveis(
    medico_id: int,
    data: str,
    duracao: int = 30,  # Duração em minutos (padrão 30)
    db: Session = Depends(get_db)
):
    """
    Obtém horários disponíveis de um médico em uma data específica.

    Considera a duração solicitada e a duração dos agendamentos existentes
    para retornar apenas horários onde há espaço suficiente.
    """
    try:
        # Converter string de data para objeto date
        data_consulta = datetime.strptime(data, "%Y-%m-%d").date()

        # Validar duração
        duracao = max(5, min(480, duracao))

        # Criar serviço de agendamento
        service = AgendamentoService(db)

        # Obter horários disponíveis considerando a duração solicitada
        horarios = service.obter_horarios_disponiveis(
            medico_id=medico_id,
            data_consulta=data_consulta,
            duracao_minutos=duracao
        )

        return {
            "sucesso": True,
            "data": data,
            "duracao": duracao,
            "horarios": horarios,
            "total": len(horarios)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verificar-disponibilidade")
async def verificar_disponibilidade(
    medico_id: int,
    data: str,
    hora: str,
    db: Session = Depends(get_db)
):
    """Verifica se um horário específico está disponível"""
    try:
        # Converter data e hora para datetime
        data_hora_str = f"{data} {hora}:00"
        data_hora = datetime.strptime(data_hora_str, "%Y-%m-%d %H:%M:%S")

        # Criar serviço de agendamento
        service = AgendamentoService(db)

        # Verificar disponibilidade
        disponivel = service.verificar_disponibilidade_medico(
            medico_id=medico_id,
            data_hora=data_hora,
            duracao_minutos=30
        )

        return {
            "sucesso": True,
            "disponivel": disponivel,
            "mensagem": "Horário disponível" if disponivel else "Horário não disponível"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Formato de data/hora inválido")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Schemas para edição de agendamentos
class AgendamentoUpdate(BaseModel):
    data: Optional[str] = None
    hora: Optional[str] = None
    medico_id: Optional[int] = None
    duracao_minutos: Optional[int] = None  # Duração customizável
    status: Optional[str] = None
    motivo_consulta: Optional[str] = None
    observacoes: Optional[str] = None

@router.put("/agendamentos/{agendamento_id}")
async def atualizar_agendamento(
    agendamento_id: int,
    dados: AgendamentoUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Atualiza um agendamento existente (edição/realocação)"""
    try:
        # Verificar se agendamento existe
        result = db.execute(text("""
            SELECT id, paciente_id, medico_id, data_hora, status
            FROM agendamentos
            WHERE id = :id
        """), {"id": agendamento_id})

        agendamento = result.fetchone()
        if not agendamento:
            raise HTTPException(status_code=404, detail="Agendamento não encontrado")

        # Verificar se usuário tem permissão para editar este agendamento
        AuthMiddleware.check_medico_access(current_user, agendamento.medico_id)

        # Preparar dados para atualização
        updates = []
        params = {"id": agendamento_id}

        if dados.data and dados.hora:
            # Realocação de data/hora (timezone-aware)
            nova_data_hora_tz = parse_datetime_brazil(dados.data, dados.hora)

            # VALIDAÇÃO: Não permitir reagendamento para o passado
            from datetime import datetime
            import pytz
            tz_brazil = pytz.timezone('America/Sao_Paulo')
            agora = datetime.now(tz_brazil)

            if nova_data_hora_tz < agora:
                return {"sucesso": False, "erro": "Não é possível reagendar para datas ou horários passados"}

            # Verificar disponibilidade do novo horário (considerando duração)
            if dados.medico_id or agendamento.medico_id:
                medico_id = dados.medico_id if dados.medico_id else agendamento.medico_id

                # Determinar a duração (nova duração ou duração atual do agendamento)
                duracao_verificacao = dados.duracao_minutos if dados.duracao_minutos else 30
                # Buscar duração atual se não estiver sendo alterada
                if not dados.duracao_minutos:
                    duracao_atual = db.execute(text(
                        "SELECT duracao_minutos FROM agendamentos WHERE id = :id"
                    ), {"id": agendamento_id}).fetchone()
                    if duracao_atual:
                        duracao_verificacao = duracao_atual[0] or 30

                # VALIDAÇÃO DE CONFLITO: Verificar sobreposição (excluindo o próprio agendamento)
                # Status que LIBERAM o horário: cancelado, faltou, remarcado
                conflito = db.execute(text("""
                    SELECT a.id, a.data_hora, a.duracao_minutos, p.nome as paciente
                    FROM agendamentos a
                    JOIN pacientes p ON a.paciente_id = p.id
                    WHERE a.medico_id = :medico_id
                    AND a.id != :agendamento_id
                    AND a.status NOT IN ('cancelado', 'faltou', 'remarcado')
                    AND (
                        :novo_inicio < (a.data_hora + (COALESCE(a.duracao_minutos, 30) || ' minutes')::interval)
                        AND
                        (:novo_inicio + (:duracao || ' minutes')::interval) > a.data_hora
                    )
                """), {
                    "medico_id": medico_id,
                    "agendamento_id": agendamento_id,
                    "novo_inicio": nova_data_hora_tz,
                    "duracao": duracao_verificacao
                }).fetchone()

                if conflito:
                    # Converter para horário de Brasília para exibição
                    hora_conflito_utc = conflito[1]
                    hora_conflito_br = hora_conflito_utc.astimezone(tz_brazil).strftime('%H:%M')
                    raise HTTPException(
                        status_code=400,
                        detail=f"Conflito de horário: já existe agendamento de {conflito[3]} às {hora_conflito_br} ({conflito[2]} min)"
                    )

            updates.append("data_hora = :data_hora")
            params["data_hora"] = nova_data_hora_tz

            # IMPORTANTE: Resetar campos de lembrete quando data/hora é alterada
            # Isso garante que os lembretes sejam enviados novamente para o novo horário
            updates.append("lembrete_24h_enviado = false")
            updates.append("lembrete_3h_enviado = false")
            updates.append("lembrete_1h_enviado = false")

        if dados.medico_id:
            updates.append("medico_id = :medico_id")
            params["medico_id"] = dados.medico_id

        if dados.duracao_minutos:
            # Validar duração (mínimo 5 minutos, máximo 480 minutos = 8 horas)
            duracao = max(5, min(480, dados.duracao_minutos))
            updates.append("duracao_minutos = :duracao")
            params["duracao"] = duracao

        if dados.status:
            # Status válidos para atualização manual
            # Permite corrigir status mesmo após atualização automática (ex: marcar falta após "realizada")
            status_validos = [
                "agendado", "agendada",
                "confirmado", "confirmada",
                "cancelado", "cancelada",
                "realizado", "realizada",
                "concluido", "concluida",
                "faltou",
                "remarcado"
            ]
            if dados.status not in status_validos:
                raise HTTPException(status_code=400, detail="Status inválido")
            updates.append("status = :status")
            params["status"] = dados.status

        if dados.motivo_consulta:
            updates.append("motivo_consulta = :motivo")
            params["motivo"] = dados.motivo_consulta

        if dados.observacoes:
            updates.append("observacoes = :observacoes")
            params["observacoes"] = dados.observacoes

        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

        # Atualizar agendamento
        updates.append("atualizado_em = NOW()")
        query = f"""
            UPDATE agendamentos
            SET {', '.join(updates)}
            WHERE id = :id
        """

        db.execute(text(query), params)

        # Registrar no histórico
        db.execute(text("""
            INSERT INTO historico_agendamentos
            (agendamento_id, acao, descricao, criado_em)
            VALUES
            (:agendamento_id, 'atualizacao', :descricao, NOW())
        """), {
            "agendamento_id": agendamento_id,
            "descricao": f"Agendamento atualizado: {', '.join([k for k in dados.dict(exclude_unset=True).keys()])}"
        })

        db.commit()

        # Notificar médico se data/hora foi alterada (reagendamento)
        if dados.data and dados.hora:
            try:
                # Buscar dados do paciente para notificação
                result_pac = db.execute(text("""
                    SELECT p.nome
                    FROM agendamentos a
                    JOIN pacientes p ON a.paciente_id = p.id
                    WHERE a.id = :id
                """), {"id": agendamento_id})
                paciente_info = result_pac.fetchone()

                notification_service = get_notification_service(db)
                await notification_service.notificar_medico(
                    medico_id=agendamento.medico_id,
                    cliente_id=current_user["cliente_id"],
                    evento="reagendado",
                    dados_agendamento={
                        "paciente_nome": paciente_info[0] if paciente_info else "Paciente",
                        "data_hora": nova_data_hora_tz
                    }
                )
            except Exception as e:
                # Log do erro, mas não falha a atualização
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Erro ao notificar médico sobre reagendamento: {e}")

        return {
            "sucesso": True,
            "mensagem": "Agendamento atualizado com sucesso",
            "agendamento_id": agendamento_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar agendamento: {str(e)}")

@router.delete("/agendamentos/{agendamento_id}")
async def cancelar_agendamento(
    agendamento_id: int,
    motivo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cancela um agendamento"""
    try:
        # Verificar se agendamento existe
        result = db.execute(text("""
            SELECT id, status, medico_id FROM agendamentos
            WHERE id = :id
        """), {"id": agendamento_id})

        agendamento = result.fetchone()
        if not agendamento:
            raise HTTPException(status_code=404, detail="Agendamento não encontrado")

        # Verificar se usuário tem permissão para cancelar este agendamento
        AuthMiddleware.check_medico_access(current_user, agendamento.medico_id)

        if agendamento.status == "cancelado":
            return {
                "sucesso": True,
                "mensagem": "Agendamento já está cancelado"
            }

        # Cancelar agendamento
        db.execute(text("""
            UPDATE agendamentos
            SET status = 'cancelado',
                observacoes = COALESCE(observacoes || ' | ', '') || :motivo,
                atualizado_em = NOW()
            WHERE id = :id
        """), {
            "id": agendamento_id,
            "motivo": f"Cancelado: {motivo}" if motivo else "Cancelado"
        })

        # Registrar no histórico
        db.execute(text("""
            INSERT INTO historico_agendamentos
            (agendamento_id, acao, descricao, criado_em)
            VALUES
            (:agendamento_id, 'cancelamento', :descricao, NOW())
        """), {
            "agendamento_id": agendamento_id,
            "descricao": motivo or "Agendamento cancelado"
        })

        db.commit()

        # Notificar médico sobre cancelamento
        try:
            # Buscar dados do agendamento para notificação
            result_ag = db.execute(text("""
                SELECT p.nome, a.data_hora
                FROM agendamentos a
                JOIN pacientes p ON a.paciente_id = p.id
                WHERE a.id = :id
            """), {"id": agendamento_id})
            agendamento_info = result_ag.fetchone()

            if agendamento_info:
                notification_service = get_notification_service(db)
                await notification_service.notificar_medico(
                    medico_id=agendamento.medico_id,
                    cliente_id=current_user["cliente_id"],
                    evento="cancelado",
                    dados_agendamento={
                        "paciente_nome": agendamento_info[0],
                        "data_hora": agendamento_info[1]
                    }
                )
        except Exception as e:
            # Log do erro, mas não falha o cancelamento
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro ao notificar médico sobre cancelamento: {e}")

        return {
            "sucesso": True,
            "mensagem": "Agendamento cancelado com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao cancelar agendamento: {str(e)}")

@router.get("/agendamentos/{agendamento_id}")
async def obter_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtém detalhes de um agendamento específico"""
    try:
        result = db.execute(text("""
            SELECT
                a.id,
                a.data_hora,
                a.duracao_minutos,
                a.status,
                a.tipo_atendimento,
                a.motivo_consulta,
                a.observacoes,
                a.criado_em,
                a.atualizado_em,
                p.id as paciente_id,
                p.nome as paciente_nome,
                p.telefone as paciente_telefone,
                p.email as paciente_email,
                p.cpf as paciente_cpf,
                m.id as medico_id,
                m.nome as medico_nome,
                m.especialidade,
                m.crm,
                a.forma_pagamento,
                a.valor_consulta
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            JOIN medicos m ON a.medico_id = m.id
            WHERE a.id = :id
        """), {"id": agendamento_id})

        agendamento = result.fetchone()
        if not agendamento:
            raise HTTPException(status_code=404, detail="Agendamento não encontrado")

        # Verificar se usuário tem permissão para acessar este agendamento
        AuthMiddleware.check_medico_access(current_user, agendamento.medico_id)

        return {
            "sucesso": True,
            "agendamento": {
                "id": agendamento.id,
                "data_hora": agendamento.data_hora.isoformat(),
                "duracao_minutos": agendamento.duracao_minutos or 30,
                "status": agendamento.status,
                "tipo_atendimento": agendamento.tipo_atendimento,
                "motivo_consulta": agendamento.motivo_consulta,
                "observacoes": agendamento.observacoes,
                "criado_em": agendamento.criado_em.isoformat(),
                "atualizado_em": agendamento.atualizado_em.isoformat(),
                "forma_pagamento": agendamento.forma_pagamento,
                "valor_consulta": agendamento.valor_consulta,
                "paciente": {
                    "id": agendamento.paciente_id,
                    "nome": agendamento.paciente_nome,
                    "telefone": agendamento.paciente_telefone,
                    "email": agendamento.paciente_email,
                    "cpf": agendamento.paciente_cpf
                },
                "medico": {
                    "id": agendamento.medico_id,
                    "nome": agendamento.medico_nome,
                    "especialidade": agendamento.especialidade,
                    "crm": agendamento.crm
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter agendamento: {str(e)}")

@router.get("/agendamentos/{agendamento_id}/historico")
async def obter_historico_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_db)
):
    """Obtém o histórico de alterações de um agendamento"""
    try:
        result = db.execute(text("""
            SELECT id, acao, descricao, criado_em
            FROM historico_agendamentos
            WHERE agendamento_id = :id
            ORDER BY criado_em DESC
        """), {"id": agendamento_id})

        historico = []
        for row in result:
            historico.append({
                "id": row.id,
                "acao": row.acao,
                "descricao": row.descricao,
                "data_hora": row.criado_em.isoformat()
            })

        return {
            "sucesso": True,
            "historico": historico
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter histórico: {str(e)}")

@router.post("/agendamentos/{agendamento_id}/marcar-falta")
async def marcar_agendamento_como_falta(
    agendamento_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Marca agendamento como falta e envia mensagem empática via WhatsApp
    
    - Atualiza status para 'faltou'
    - Busca próximos horários disponíveis
    - Envia mensagem WhatsApp com sugestões de reagendamento
    """
    try:
        # Importar serviço de falta
        from app.services.falta_service import get_falta_service
        
        # Verificar permissão de acesso
        # Buscar medico_id do agendamento
        agendamento_check = db.execute(text("""
            SELECT medico_id FROM agendamentos WHERE id = :id
        """), {"id": agendamento_id}).fetchone()
        
        if not agendamento_check:
            raise HTTPException(status_code=404, detail="Agendamento não encontrado")
        
        # Verificar permissão (médico só pode marcar falta na própria agenda)
        AuthMiddleware.check_medico_access(current_user, agendamento_check[0])
        
        # Processar falta
        falta_service = get_falta_service(db)
        resultado = await falta_service.marcar_como_falta(agendamento_id)
        
        if not resultado["sucesso"]:
            raise HTTPException(status_code=400, detail=resultado.get("erro", "Erro ao marcar falta"))
        
        return {
            "sucesso": True,
            "mensagem": resultado["mensagem"],
            "whatsapp_enviado": resultado.get("mensagem_whatsapp_enviada", False),
            "horarios_sugeridos": resultado.get("proximos_horarios_sugeridos", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao marcar falta: {str(e)}")
