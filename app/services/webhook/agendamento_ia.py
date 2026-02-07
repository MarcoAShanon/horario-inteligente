import re
import logging
from datetime import datetime
import pytz
from sqlalchemy.orm import Session

from app.models.agendamento import Agendamento
from app.models.paciente import Paciente
from app.models.medico import Medico
from app.utils.timezone_helper import make_aware_brazil
from app.services.agendamento_service import AgendamentoService
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

TZ_BRAZIL = pytz.timezone('America/Sao_Paulo')


async def criar_agendamento_from_ia(
    db: Session,
    cliente_id: int,
    telefone: str,
    dados_coletados: dict
) -> Agendamento:
    """
    Cria um agendamento a partir dos dados coletados pela IA.

    Espera dados_coletados com:
    - nome: str (nome do paciente)
    - especialidade: str (opcional)
    - medico_id: int (ID do médico)
    - convenio: str (nome do convênio ou "particular")
    - data_preferida: str (formato "DD/MM/YYYY HH:MM" ou "DD/MM/YYYY")
    """
    try:
        nome = dados_coletados.get("nome")
        medico_id = dados_coletados.get("medico_id")
        convenio = dados_coletados.get("convenio", "particular")
        data_str = dados_coletados.get("data_preferida")
        # Prioriza motivo_consulta, senão usa especialidade como fallback
        motivo_consulta = dados_coletados.get("motivo_consulta") or dados_coletados.get("especialidade", "")

        # Validar dados mínimos
        if not nome or not medico_id or not data_str:
            logger.warning(f"[Agendamento] Dados insuficientes: nome={nome}, medico_id={medico_id}, data={data_str}")
            return None

        # Parsear data/hora
        data_hora = None
        formatos = [
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y %Hh",
            "%d/%m/%Y %H",
            "%d/%m/%Y"
        ]

        for fmt in formatos:
            try:
                data_hora = datetime.strptime(data_str.strip(), fmt)
                break
            except ValueError:
                continue

        if not data_hora:
            # Tentar extrair data e hora separadamente
            match = re.search(r'(\d{2}/\d{2}/\d{4})', data_str)
            if match:
                data_hora = datetime.strptime(match.group(1), "%d/%m/%Y")
                # Procurar hora
                hora_match = re.search(r'(\d{1,2})[h:]?(\d{0,2})?', data_str.replace(match.group(1), ''))
                if hora_match:
                    hora = int(hora_match.group(1))
                    minuto = int(hora_match.group(2)) if hora_match.group(2) else 0
                    data_hora = data_hora.replace(hour=hora, minute=minuto)

        if not data_hora:
            logger.warning(f"[Agendamento] Não foi possível parsear data: {data_str}")
            return None

        # Se não tem hora, definir 9h como padrão
        if data_hora.hour == 0 and data_hora.minute == 0:
            data_hora = data_hora.replace(hour=9, minute=0)

        # Converter para timezone de Brasília (UTC-3)
        data_hora = make_aware_brazil(data_hora)
        logger.info(f"[Agendamento] Data/hora com timezone: {data_hora}")

        # Verificar se médico existe
        medico = db.query(Medico).filter(
            Medico.id == medico_id,
            Medico.cliente_id == cliente_id
        ).first()

        if not medico:
            logger.warning(f"[Agendamento] Médico {medico_id} não encontrado para cliente {cliente_id}")
            return None

        # ========== VERIFICAR DISPONIBILIDADE DO HORÁRIO ==========
        agendamento_service = AgendamentoService(db)
        disponivel = agendamento_service.verificar_disponibilidade_medico(
            medico_id=medico_id,
            data_hora=data_hora,
            duracao_minutos=30
        )

        if not disponivel:
            logger.warning(f"[Agendamento] ❌ Horário INDISPONÍVEL: {data_hora} para médico {medico_id}")
            # Retornar dict com erro para que a IA possa informar o paciente
            return {"erro": "horario_indisponivel", "data_hora": data_hora, "medico_nome": medico.nome}

        logger.info(f"[Agendamento] ✅ Horário disponível: {data_hora} para médico {medico_id}")
        # ==========================================================

        # Buscar ou criar paciente
        telefone_limpo = re.sub(r'[^\d]', '', telefone)
        paciente = db.query(Paciente).filter(
            Paciente.cliente_id == cliente_id,
            Paciente.telefone.like(f"%{telefone_limpo[-8:]}%")
        ).first()

        if not paciente:
            # Criar novo paciente
            paciente = Paciente(
                cliente_id=cliente_id,
                nome=nome,
                telefone=telefone_limpo,
                convenio=convenio if convenio.lower() != "particular" else None
            )
            db.add(paciente)
            db.flush()  # Para obter o ID
            logger.info(f"[Agendamento] Novo paciente criado: {paciente.id} - {nome}")
        else:
            # Atualizar nome se necessário
            if paciente.nome != nome:
                paciente.nome = nome

        # ========== CANCELAR AGENDAMENTOS ANTERIORES (REAGENDAMENTO) ==========
        # Buscar agendamentos futuros do paciente com este médico que ainda não foram realizados
        from datetime import datetime as dt
        import pytz
        tz_brazil = pytz.timezone('America/Sao_Paulo')
        agora = dt.now(tz_brazil)

        agendamentos_anteriores = db.query(Agendamento).filter(
            Agendamento.paciente_id == paciente.id,
            Agendamento.medico_id == medico_id,
            Agendamento.status.in_(['agendado', 'confirmado']),
            Agendamento.data_hora > agora  # Apenas futuros
        ).all()

        if agendamentos_anteriores:
            for ag_anterior in agendamentos_anteriores:
                # IMPORTANTE: Usar "remarcado" (NÃO "cancelado") para manter métricas corretas
                # "remarcado" = paciente mudou data, receita MANTIDA (não é perda)
                # "cancelado" = paciente desistiu, PERDA de receita
                ag_anterior.status = 'remarcado'
                ag_anterior.observacoes = (ag_anterior.observacoes or '') + f' | Remarcado para nova data via WhatsApp em {agora.strftime("%d/%m/%Y %H:%M")}'
                logger.info(f"[Agendamento] 🔄 Remarcação: Marcando como 'remarcado' o agendamento anterior ID={ag_anterior.id} ({ag_anterior.data_hora.strftime('%d/%m/%Y %H:%M')})")

            # Notificar via WebSocket sobre remarcações
            try:
                for ag_anterior in agendamentos_anteriores:
                    await websocket_manager.send_agendamento_atualizado(cliente_id, {
                        "id": ag_anterior.id,
                        "status": "remarcado",
                        "motivo": "Paciente remarcou para nova data"
                    })
            except Exception as ws_error:
                logger.warning(f"[WebSocket] Erro ao notificar remarcação: {ws_error}")
        # ======================================================================

        # Determinar valor e forma de pagamento
        valor = None
        forma_pagamento = 'particular'

        if convenio.lower() == "particular":
            # Buscar valor configurado do médico
            valor = medico.valor_consulta_particular if medico.valor_consulta_particular else 150.00
        else:
            # Buscar índice do convênio no array convenios_aceitos do médico
            convenios = medico.convenios_aceitos or []
            convenio_lower = convenio.lower().strip()
            for i, conv in enumerate(convenios):
                conv_nome = conv.get('nome', '').lower().strip()
                if conv_nome == convenio_lower or convenio_lower in conv_nome or conv_nome in convenio_lower:
                    forma_pagamento = f'convenio_{i}'
                    valor = conv.get('valor')
                    logger.info(f"[Agendamento] Convênio encontrado: {conv.get('nome')} (index={i}, valor={valor})")
                    break
            else:
                # Convênio não encontrado no cadastro, salvar como genérico
                forma_pagamento = 'convenio_0'
                logger.warning(f"[Agendamento] Convênio '{convenio}' não encontrado no cadastro do médico")

        # Criar agendamento (cliente_id é inferido pelo medico/paciente)
        # Indicar se é reagendamento na observação
        is_reagendamento = bool(agendamentos_anteriores)
        observacao_base = "Reagendado" if is_reagendamento else "Agendado"
        observacao = f"{observacao_base} via WhatsApp IA. Convênio: {convenio}"

        agendamento = Agendamento(
            medico_id=medico_id,
            paciente_id=paciente.id,
            data_hora=data_hora,
            status="agendado",
            tipo_atendimento=convenio.lower() if convenio.lower() != "particular" else "particular",
            forma_pagamento=forma_pagamento,
            valor_consulta=str(valor) if valor else None,
            motivo_consulta=motivo_consulta,
            observacoes=observacao
        )
        db.add(agendamento)
        db.commit()
        db.refresh(agendamento)

        logger.info(f"[Agendamento] ✅ Criado: ID={agendamento.id}, Paciente={nome}, Médico={medico.nome}, Data={data_hora}")

        # Notificar via WebSocket para atualizar calendários em tempo real
        try:
            await websocket_manager.send_novo_agendamento(cliente_id, {
                "id": agendamento.id,
                "paciente_nome": nome,
                "medico_id": medico_id,
                "medico_nome": medico.nome,
                "data_hora": data_hora.isoformat(),
                "status": "agendado",
                "tipo_atendimento": agendamento.tipo_atendimento
            })
        except Exception as ws_error:
            logger.warning(f"[WebSocket] Erro ao notificar novo agendamento: {ws_error}")

        return agendamento

    except Exception as e:
        logger.error(f"[Agendamento] Erro ao criar: {e}")
        import traceback
        logger.error(f"[Agendamento] Traceback: {traceback.format_exc()}")
        db.rollback()
        return None
