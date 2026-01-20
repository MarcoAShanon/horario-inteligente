"""
API REST de Lembretes Inteligentes
Horário Inteligente SaaS

Endpoints para gerenciar lembretes de consultas com IA conversacional.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.services.lembrete_service import lembrete_service
from app.models.lembrete import Lembrete, TipoLembrete, StatusLembrete
from app.models import Agendamento, Paciente, Medico
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/lembretes", tags=["Lembretes Inteligentes"])


# ============ SCHEMAS ============

class LembreteResponse(BaseModel):
    id: int
    agendamento_id: int
    tipo: str
    status: str
    enviado_em: Optional[datetime]
    message_id: Optional[str]
    template_usado: Optional[str]
    respondido_em: Optional[datetime]
    resposta_texto: Optional[str]
    intencao_detectada: Optional[str]
    tentativas_envio: int
    ultimo_erro: Optional[str]
    lembrete_1h_solicitado: bool
    criado_em: datetime

    class Config:
        from_attributes = True


class LembreteDetailResponse(LembreteResponse):
    paciente_nome: Optional[str] = None
    medico_nome: Optional[str] = None
    data_consulta: Optional[datetime] = None


class EstatisticasResponse(BaseModel):
    total: int
    pendentes: int
    enviados_aguardando: int
    confirmados: int
    remarcados: int
    cancelados: int
    timestamp: str


class CriarLembreteRequest(BaseModel):
    agendamento_id: int
    tipos: List[str] = ["24h"]


class ReenviarResponse(BaseModel):
    success: bool
    message: str
    message_id: Optional[str] = None


# ============ ENDPOINTS ============

@router.get("/agendamento/{agendamento_id}", response_model=List[LembreteDetailResponse])
async def listar_lembretes_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lista todos os lembretes de um agendamento específico"""
    cliente_id = current_user["cliente_id"]

    # Verificar se o agendamento pertence ao cliente
    agendamento = db.query(Agendamento).filter(
        Agendamento.id == agendamento_id,
        Agendamento.cliente_id == cliente_id
    ).first()

    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    # Buscar lembretes
    lembretes = lembrete_service.get_lembretes_agendamento(db, agendamento_id)

    # Buscar dados complementares
    paciente = db.query(Paciente).filter(Paciente.id == agendamento.paciente_id).first()
    medico = db.query(Medico).filter(Medico.id == agendamento.medico_id).first()

    result = []
    for lembrete in lembretes:
        result.append({
            "id": lembrete.id,
            "agendamento_id": lembrete.agendamento_id,
            "tipo": lembrete.tipo,
            "status": lembrete.status,
            "enviado_em": lembrete.enviado_em,
            "message_id": lembrete.message_id,
            "template_usado": lembrete.template_usado,
            "respondido_em": lembrete.respondido_em,
            "resposta_texto": lembrete.resposta_texto,
            "intencao_detectada": lembrete.intencao_detectada,
            "tentativas_envio": lembrete.tentativas_envio,
            "ultimo_erro": lembrete.ultimo_erro,
            "lembrete_1h_solicitado": lembrete.lembrete_1h_solicitado,
            "criado_em": lembrete.criado_em,
            "paciente_nome": paciente.nome if paciente else None,
            "medico_nome": medico.nome if medico else None,
            "data_consulta": agendamento.data_hora
        })

    return result


@router.get("/estatisticas", response_model=EstatisticasResponse)
async def get_estatisticas(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Retorna estatísticas gerais dos lembretes"""
    stats = lembrete_service.get_estatisticas(db)
    return stats


@router.get("/{lembrete_id}", response_model=LembreteDetailResponse)
async def get_lembrete(
    lembrete_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Retorna detalhes de um lembrete específico"""
    cliente_id = current_user["cliente_id"]

    lembrete = db.query(Lembrete).filter(Lembrete.id == lembrete_id).first()

    if not lembrete:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")

    # Verificar se pertence ao cliente
    agendamento = db.query(Agendamento).filter(
        Agendamento.id == lembrete.agendamento_id,
        Agendamento.cliente_id == cliente_id
    ).first()

    if not agendamento:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")

    # Buscar dados complementares
    paciente = db.query(Paciente).filter(Paciente.id == agendamento.paciente_id).first()
    medico = db.query(Medico).filter(Medico.id == agendamento.medico_id).first()

    return {
        "id": lembrete.id,
        "agendamento_id": lembrete.agendamento_id,
        "tipo": lembrete.tipo,
        "status": lembrete.status,
        "enviado_em": lembrete.enviado_em,
        "message_id": lembrete.message_id,
        "template_usado": lembrete.template_usado,
        "respondido_em": lembrete.respondido_em,
        "resposta_texto": lembrete.resposta_texto,
        "intencao_detectada": lembrete.intencao_detectada,
        "tentativas_envio": lembrete.tentativas_envio,
        "ultimo_erro": lembrete.ultimo_erro,
        "lembrete_1h_solicitado": lembrete.lembrete_1h_solicitado,
        "criado_em": lembrete.criado_em,
        "paciente_nome": paciente.nome if paciente else None,
        "medico_nome": medico.nome if medico else None,
        "data_consulta": agendamento.data_hora
    }


@router.post("", response_model=List[LembreteResponse])
async def criar_lembretes(
    request: CriarLembreteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cria lembretes para um agendamento"""
    cliente_id = current_user["cliente_id"]

    # Verificar se o agendamento pertence ao cliente
    agendamento = db.query(Agendamento).filter(
        Agendamento.id == request.agendamento_id,
        Agendamento.cliente_id == cliente_id
    ).first()

    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    # Validar tipos
    tipos_validos = [t.value for t in TipoLembrete]
    for tipo in request.tipos:
        if tipo not in tipos_validos:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de lembrete inválido: {tipo}. Valores válidos: {tipos_validos}"
            )

    # Criar lembretes
    lembretes = lembrete_service.criar_lembretes_para_agendamento(
        db=db,
        agendamento_id=request.agendamento_id,
        tipos=request.tipos
    )

    return [
        {
            "id": l.id,
            "agendamento_id": l.agendamento_id,
            "tipo": l.tipo,
            "status": l.status,
            "enviado_em": l.enviado_em,
            "message_id": l.message_id,
            "template_usado": l.template_usado,
            "respondido_em": l.respondido_em,
            "resposta_texto": l.resposta_texto,
            "intencao_detectada": l.intencao_detectada,
            "tentativas_envio": l.tentativas_envio,
            "ultimo_erro": l.ultimo_erro,
            "lembrete_1h_solicitado": l.lembrete_1h_solicitado,
            "criado_em": l.criado_em
        }
        for l in lembretes
    ]


@router.post("/{lembrete_id}/reenviar", response_model=ReenviarResponse)
async def reenviar_lembrete(
    lembrete_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Reenvia um lembrete específico"""
    cliente_id = current_user["cliente_id"]

    lembrete = db.query(Lembrete).filter(Lembrete.id == lembrete_id).first()

    if not lembrete:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")

    # Verificar se pertence ao cliente
    agendamento = db.query(Agendamento).filter(
        Agendamento.id == lembrete.agendamento_id,
        Agendamento.cliente_id == cliente_id
    ).first()

    if not agendamento:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")

    # Verificar status do agendamento
    if agendamento.status not in ["agendado", "confirmado"]:
        raise HTTPException(
            status_code=400,
            detail="Não é possível reenviar lembrete para consulta cancelada ou realizada"
        )

    # Resetar status para pendente e reenviar
    lembrete.status = StatusLembrete.PENDENTE.value
    lembrete.tentativas_envio = 0
    lembrete.ultimo_erro = None
    db.commit()

    # Enviar
    sucesso, resultado = await lembrete_service.enviar_lembrete(db, lembrete)

    if sucesso:
        return {
            "success": True,
            "message": "Lembrete reenviado com sucesso",
            "message_id": resultado
        }
    else:
        return {
            "success": False,
            "message": f"Erro ao reenviar: {resultado}",
            "message_id": None
        }


@router.delete("/{lembrete_id}")
async def cancelar_lembrete(
    lembrete_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cancela um lembrete pendente"""
    cliente_id = current_user["cliente_id"]

    lembrete = db.query(Lembrete).filter(Lembrete.id == lembrete_id).first()

    if not lembrete:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")

    # Verificar se pertence ao cliente
    agendamento = db.query(Agendamento).filter(
        Agendamento.id == lembrete.agendamento_id,
        Agendamento.cliente_id == cliente_id
    ).first()

    if not agendamento:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")

    # Só pode cancelar lembretes pendentes
    if lembrete.status != StatusLembrete.PENDENTE.value:
        raise HTTPException(
            status_code=400,
            detail="Apenas lembretes pendentes podem ser cancelados"
        )

    # Deletar o lembrete
    db.delete(lembrete)
    db.commit()

    return {"message": "Lembrete cancelado com sucesso"}


@router.get("", response_model=List[LembreteDetailResponse])
async def listar_lembretes(
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lista lembretes com filtros opcionais"""
    cliente_id = current_user["cliente_id"]

    # Base query com join para filtrar por cliente
    query = db.query(Lembrete).join(
        Agendamento, Lembrete.agendamento_id == Agendamento.id
    ).filter(Agendamento.cliente_id == cliente_id)

    # Aplicar filtros
    if status:
        try:
            status_enum = StatusLembrete(status)
            query = query.filter(Lembrete.status == status_enum.value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status}")

    if tipo:
        try:
            tipo_enum = TipoLembrete(tipo)
            query = query.filter(Lembrete.tipo == tipo_enum.value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Tipo inválido: {tipo}")

    # Ordenar e limitar
    lembretes = query.order_by(Lembrete.criado_em.desc()).limit(limit).all()

    result = []
    for lembrete in lembretes:
        agendamento = db.query(Agendamento).filter(
            Agendamento.id == lembrete.agendamento_id
        ).first()

        paciente = db.query(Paciente).filter(
            Paciente.id == agendamento.paciente_id
        ).first() if agendamento else None

        medico = db.query(Medico).filter(
            Medico.id == agendamento.medico_id
        ).first() if agendamento else None

        result.append({
            "id": lembrete.id,
            "agendamento_id": lembrete.agendamento_id,
            "tipo": lembrete.tipo,
            "status": lembrete.status,
            "enviado_em": lembrete.enviado_em,
            "message_id": lembrete.message_id,
            "template_usado": lembrete.template_usado,
            "respondido_em": lembrete.respondido_em,
            "resposta_texto": lembrete.resposta_texto,
            "intencao_detectada": lembrete.intencao_detectada,
            "tentativas_envio": lembrete.tentativas_envio,
            "ultimo_erro": lembrete.ultimo_erro,
            "lembrete_1h_solicitado": lembrete.lembrete_1h_solicitado,
            "criado_em": lembrete.criado_em,
            "paciente_nome": paciente.nome if paciente else None,
            "medico_nome": medico.nome if medico else None,
            "data_consulta": agendamento.data_hora if agendamento else None
        })

    return result
