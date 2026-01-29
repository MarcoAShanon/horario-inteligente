"""
API REST de Conversas WhatsApp
Horário Inteligente SaaS

Endpoints para gerenciar conversas e mensagens do painel de atendimento.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
import pytz

from app.database import get_db

# Timezone Brasil
TZ_BRAZIL = pytz.timezone('America/Sao_Paulo')

def converter_para_brasil(dt):
    """Converte datetime UTC para horário de Brasília."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume UTC se não tem timezone
        dt = pytz.utc.localize(dt)
    return dt.astimezone(TZ_BRAZIL).isoformat()
from app.services.conversa_service import ConversaService
from app.models.conversa import Conversa, StatusConversa
from app.models.mensagem import Mensagem, DirecaoMensagem, RemetenteMensagem, TipoMensagem
from app.api.auth import get_current_user
from app.services.websocket_manager import websocket_manager


router = APIRouter(prefix="/api/conversas", tags=["Conversas WhatsApp"])


# ============ SCHEMAS ============

class MensagemResponse(BaseModel):
    id: int
    direcao: str
    remetente: str
    tipo: str
    conteudo: str
    midia_url: Optional[str]
    timestamp: datetime
    lida: bool

    class Config:
        from_attributes = True


class ConversaResponse(BaseModel):
    id: int
    paciente_telefone: str
    paciente_nome: Optional[str]
    status: str
    atendente_id: Optional[int]
    ultima_mensagem_at: datetime
    criado_em: datetime
    nao_lidas: int = 0
    ultima_mensagem: Optional[str] = None
    # Campos de urgência
    urgencia_nivel: Optional[str] = "normal"
    urgencia_motivo: Optional[str] = None
    urgencia_resolvida: bool = True

    class Config:
        from_attributes = True


class ConversaDetailResponse(ConversaResponse):
    mensagens: List[MensagemResponse] = []


class EnviarMensagemRequest(BaseModel):
    conteudo: str
    tipo: str = "texto"
    template_name: Optional[str] = None  # Nome do template Meta (obrigatório se janela expirada)
    template_params: Optional[List[str]] = None  # Parâmetros do template


class StatsResponse(BaseModel):
    total_ativas: int
    total_assumidas: int
    total_nao_lidas: int


class JanelaStatusResponse(BaseModel):
    """Status da janela de 24h da Meta para envio de mensagens"""
    ativa: bool
    expira_em: Optional[str] = None  # Ex: "4h32min"
    timestamp_expiracao: Optional[datetime] = None
    ultima_mensagem_paciente: Optional[datetime] = None
    pode_mensagem_livre: bool
    mensagem: str


# ============ ENDPOINTS ============

@router.get("", response_model=List[ConversaResponse])
async def listar_conversas(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lista todas as conversas do cliente (tenant)"""
    cliente_id = current_user["cliente_id"]

    status_enum = None
    if status:
        try:
            status_enum = StatusConversa(status)
        except ValueError:
            pass

    conversas = ConversaService.listar_conversas(db, cliente_id, status_enum, limit)

    # Enriquecer com contagem de não lidas e última mensagem
    result = []
    for conv in conversas:
        # Contar não lidas desta conversa
        nao_lidas = db.query(Mensagem).filter(
            Mensagem.conversa_id == conv.id,
            Mensagem.direcao == DirecaoMensagem.ENTRADA,
            Mensagem.lida == False
        ).count()

        # Pegar última mensagem
        ultima = db.query(Mensagem).filter(
            Mensagem.conversa_id == conv.id
        ).order_by(Mensagem.timestamp.desc()).first()

        conv_dict = {
            "id": conv.id,
            "paciente_telefone": conv.paciente_telefone,
            "paciente_nome": conv.paciente_nome,
            "status": conv.status.value,
            "atendente_id": conv.atendente_id,
            "ultima_mensagem_at": conv.ultima_mensagem_at,
            "criado_em": conv.criado_em,
            "nao_lidas": nao_lidas,
            "ultima_mensagem": ultima.conteudo[:50] + "..." if ultima and len(ultima.conteudo) > 50 else (ultima.conteudo if ultima else None),
            # Campos de urgência
            "urgencia_nivel": conv.urgencia_nivel.value if conv.urgencia_nivel else "normal",
            "urgencia_motivo": conv.urgencia_motivo,
            "urgencia_resolvida": conv.urgencia_resolvida if conv.urgencia_resolvida is not None else True
        }
        result.append(conv_dict)

    return result


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Estatísticas das conversas"""
    cliente_id = current_user["cliente_id"]

    total_ativas = db.query(Conversa).filter(
        Conversa.cliente_id == cliente_id,
        Conversa.status == StatusConversa.IA_ATIVA
    ).count()

    total_assumidas = db.query(Conversa).filter(
        Conversa.cliente_id == cliente_id,
        Conversa.status == StatusConversa.HUMANO_ASSUMIU
    ).count()

    total_nao_lidas = ConversaService.contar_nao_lidas(db, cliente_id)

    return {
        "total_ativas": total_ativas,
        "total_assumidas": total_assumidas,
        "total_nao_lidas": total_nao_lidas
    }


@router.get("/{conversa_id}/janela-status", response_model=JanelaStatusResponse)
async def verificar_janela_24h(
    conversa_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Verifica status da janela de 24h da Meta para envio de mensagens.

    Regras da Meta:
    - Dentro de 24h após última mensagem do paciente → Pode enviar mensagem livre
    - Fora de 24h → Obrigatório usar template aprovado
    """
    conversa = db.query(Conversa).filter(
        Conversa.id == conversa_id,
        Conversa.cliente_id == current_user["cliente_id"]
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    # Calcular status da janela
    janela_ativa = False
    expira_em = None
    timestamp_expiracao = None
    mensagem = ""

    if conversa.ultima_mensagem_paciente_at:
        # Janela de 24h
        expiracao = conversa.ultima_mensagem_paciente_at + timedelta(hours=24)
        agora = datetime.utcnow()

        if agora < expiracao:
            janela_ativa = True
            tempo_restante = expiracao - agora
            horas = int(tempo_restante.total_seconds() // 3600)
            minutos = int((tempo_restante.total_seconds() % 3600) // 60)
            expira_em = f"{horas}h{minutos:02d}min"
            timestamp_expiracao = expiracao
            mensagem = f"Janela ativa. Você pode enviar mensagens livres. Expira em {expira_em}."
        else:
            mensagem = "Janela expirada. Use um template aprovado para iniciar nova conversa."
    else:
        mensagem = "Paciente ainda não enviou mensagens. Use um template aprovado."

    return {
        "ativa": janela_ativa,
        "expira_em": expira_em,
        "timestamp_expiracao": timestamp_expiracao,
        "ultima_mensagem_paciente": conversa.ultima_mensagem_paciente_at,
        "pode_mensagem_livre": janela_ativa,
        "mensagem": mensagem
    }


@router.get("/{conversa_id}", response_model=ConversaDetailResponse)
async def get_conversa(
    conversa_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Detalhes de uma conversa com mensagens"""
    conversa = db.query(Conversa).filter(
        Conversa.id == conversa_id,
        Conversa.cliente_id == current_user["cliente_id"]
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    # Marcar mensagens como lidas
    ConversaService.marcar_mensagens_como_lidas(db, conversa_id)

    # Buscar mensagens
    mensagens = ConversaService.buscar_mensagens(db, conversa_id)

    return {
        "id": conversa.id,
        "paciente_telefone": conversa.paciente_telefone,
        "paciente_nome": conversa.paciente_nome,
        "status": conversa.status.value,
        "atendente_id": conversa.atendente_id,
        "ultima_mensagem_at": conversa.ultima_mensagem_at,
        "criado_em": conversa.criado_em,
        "nao_lidas": 0,  # Acabamos de marcar como lidas
        # Campos de urgência
        "urgencia_nivel": conversa.urgencia_nivel.value if conversa.urgencia_nivel else "normal",
        "urgencia_motivo": conversa.urgencia_motivo,
        "urgencia_resolvida": conversa.urgencia_resolvida if conversa.urgencia_resolvida is not None else True,
        "mensagens": [
            {
                "id": m.id,
                "direcao": m.direcao.value,
                "remetente": m.remetente.value,
                "tipo": m.tipo.value,
                "conteudo": m.conteudo,
                "midia_url": m.midia_url,
                "timestamp": converter_para_brasil(m.timestamp),
                "lida": m.lida
            }
            for m in mensagens
        ]
    }


@router.post("/{conversa_id}/mensagens", response_model=MensagemResponse)
async def enviar_mensagem(
    conversa_id: int,
    request: EnviarMensagemRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Envia mensagem manual (atendente).

    Respeita a janela de 24h da Meta:
    - Se janela ativa: pode enviar mensagem livre
    - Se janela expirada: obrigatório usar template aprovado
    """
    conversa = db.query(Conversa).filter(
        Conversa.id == conversa_id,
        Conversa.cliente_id == current_user["cliente_id"]
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    # Verificar janela de 24h
    janela_ativa = False
    if conversa.ultima_mensagem_paciente_at:
        expiracao = conversa.ultima_mensagem_paciente_at + timedelta(hours=24)
        janela_ativa = datetime.utcnow() < expiracao

    # Se janela expirada e não tem template, bloquear
    if not janela_ativa and not request.template_name:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "janela_expirada",
                "message": "A janela de 24h expirou. É necessário usar um template aprovado pela Meta.",
                "janela_ativa": False
            }
        )

    # Enviar via WhatsApp (API Oficial Meta)
    from app.services.whatsapp_official_service import WhatsAppOfficialService
    whatsapp = WhatsAppOfficialService()

    try:
        if request.template_name:
            # Enviar via template
            result = await whatsapp.send_template(
                to=conversa.paciente_telefone,
                template_name=request.template_name,
                parameters=request.template_params or []
            )
        else:
            # Enviar mensagem livre (janela ativa)
            result = await whatsapp.send_text(to=conversa.paciente_telefone, message=request.conteudo)

        if not result.success:
            raise HTTPException(status_code=500, detail=f"Erro ao enviar WhatsApp: {result.error}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar WhatsApp: {str(e)}")

    # Salvar no banco
    mensagem = ConversaService.adicionar_mensagem(
        db=db,
        conversa_id=conversa_id,
        direcao=DirecaoMensagem.SAIDA,
        remetente=RemetenteMensagem.ATENDENTE,
        conteudo=request.conteudo,
        tipo=TipoMensagem(request.tipo)
    )

    # Notificar via WebSocket (para outros atendentes vendo a mesma conversa)
    await websocket_manager.send_nova_mensagem(
        cliente_id=current_user["cliente_id"],
        conversa_id=conversa_id,
        mensagem={
            "id": mensagem.id,
            "direcao": "saida",
            "remetente": "atendente",
            "tipo": request.tipo,
            "conteudo": request.conteudo,
            "timestamp": converter_para_brasil(mensagem.timestamp)
        }
    )

    return {
        "id": mensagem.id,
        "direcao": mensagem.direcao.value,
        "remetente": mensagem.remetente.value,
        "tipo": mensagem.tipo.value,
        "conteudo": mensagem.conteudo,
        "midia_url": mensagem.midia_url,
        "timestamp": converter_para_brasil(mensagem.timestamp),
        "lida": mensagem.lida
    }


@router.put("/{conversa_id}/assumir")
async def assumir_conversa(
    conversa_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Atendente assume a conversa (desativa IA)"""
    conversa = db.query(Conversa).filter(
        Conversa.id == conversa_id,
        Conversa.cliente_id == current_user["cliente_id"]
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    # Passa o tipo do atendente (medico ou secretaria)
    atendente_tipo = current_user.get("tipo", "medico")
    conversa = ConversaService.assumir_conversa(db, conversa_id, current_user["id"], atendente_tipo)

    return {"message": "Conversa assumida com sucesso", "status": conversa.status.value}


@router.put("/{conversa_id}/devolver-ia")
async def devolver_para_ia(
    conversa_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Devolve a conversa para a IA"""
    conversa = db.query(Conversa).filter(
        Conversa.id == conversa_id,
        Conversa.cliente_id == current_user["cliente_id"]
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    conversa = ConversaService.devolver_para_ia(db, conversa_id)

    return {"message": "Conversa devolvida para IA", "status": conversa.status.value}


@router.put("/{conversa_id}/encerrar")
async def encerrar_conversa(
    conversa_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Encerra a conversa"""
    conversa = db.query(Conversa).filter(
        Conversa.id == conversa_id,
        Conversa.cliente_id == current_user["cliente_id"]
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    conversa = ConversaService.encerrar_conversa(db, conversa_id)

    return {"message": "Conversa encerrada", "status": conversa.status.value}
