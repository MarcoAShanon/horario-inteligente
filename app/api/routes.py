"""
APIs CRUD para Sistema de Agendamento Médico
Desenvolvido por Marco
"""

from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.cliente import Cliente
from app.models.medico import Medico
from app.models.paciente import Paciente
from app.models.agendamento import Agendamento
from app.models.convenio import Convenio
from app.services.agendamento_service import AgendamentoService

router = APIRouter()

# Schemas Pydantic
class ClienteResponse(BaseModel):
    id: int
    nome: str
    email: str
    plano: str
    ativo: bool
    valor_mensalidade: str
    criado_em: datetime
    
    class Config:
        from_attributes = True

class MedicoResponse(BaseModel):
    id: int
    nome: str
    crm: str
    especialidade: str
    calendario_id: Optional[str]
    convenios_aceitos: Optional[List[str]]
    horarios_atendimento: Optional[dict]
    ativo: bool
    
    class Config:
        from_attributes = True

# ENDPOINTS - CLIENTES
@router.get("/clientes", response_model=List[ClienteResponse])
def listar_clientes(db: Session = Depends(get_db)):
    """Lista todas as clínicas cadastradas."""
    clientes = db.query(Cliente).filter(Cliente.ativo == True).all()
    return clientes

@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
def obter_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtém dados de uma clínica específica."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente

# ENDPOINTS - MÉDICOS
@router.get("/medicos", response_model=List[MedicoResponse])
def listar_medicos(
    cliente_id: int = Query(..., description="ID da clínica"),
    db: Session = Depends(get_db)
):
    """Lista médicos de uma clínica."""
    medicos = db.query(Medico).filter(
        Medico.cliente_id == cliente_id,
        Medico.ativo == True
    ).all()
    return medicos

@router.get("/medicos/{medico_id}", response_model=MedicoResponse)
def obter_medico(medico_id: int, db: Session = Depends(get_db)):
    """Obtém dados de um médico específico."""
    medico = db.query(Medico).filter(Medico.id == medico_id).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico não encontrado")
    return medico

# ENDPOINTS - CONVÊNIOS
@router.get("/convenios")
def listar_convenios(
    cliente_id: int = Query(..., description="ID da clínica"),
    db: Session = Depends(get_db)
):
    """Lista convênios aceitos pela clínica."""
    convenios = db.query(Convenio).filter(
        Convenio.cliente_id == cliente_id,
        Convenio.ativo == True
    ).all()
    
    return {
        "cliente_id": cliente_id,
        "convenios": [
            {
                "id": c.id,
                "nome": c.nome,
                "codigo": c.codigo,
                "ativo": c.ativo
            }
            for c in convenios
        ]
    }

# Chat IA Request/Response Models
class ChatRequest(BaseModel):
    mensagem: str
    telefone: str
    cliente_id: int
    contexto_conversa: Optional[List[dict]] = []

class ChatResponse(BaseModel):
    resposta: str
    intencao: str
    proxima_acao: str
    dados_coletados: dict
    paciente_existente: bool

# ENDPOINTS - CHAT IA
@router.post("/chat/processar", response_model=ChatResponse)
def processar_mensagem_chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Processa mensagem do chat com IA."""
    try:
        from app.services.anthropic_service import AnthropicService
        
        anthropic_service = AnthropicService(db, request.cliente_id)
        
        resultado = anthropic_service.processar_mensagem(
            mensagem=request.mensagem,
            telefone=request.telefone,
            contexto_conversa=request.contexto_conversa
        )
        
        return ChatResponse(**resultado)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao processar mensagem: {str(e)}"
        )

# ENDPOINTS - SISTEMA
@router.get("/sistema/status")
def status_sistema(db: Session = Depends(get_db)):
    """Verifica status geral do sistema."""
    try:
        total_clientes = db.query(Cliente).filter(Cliente.ativo == True).count()
        total_medicos = db.query(Medico).filter(Medico.ativo == True).count()

        return {
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "estatisticas": {
                "clientes_ativos": total_clientes,
                "medicos_ativos": total_medicos
            },
            "servicos": {
                "banco_dados": "ok",
                "api_fastapi": "ok"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no sistema: {str(e)}")


# ENDPOINTS - ÁUDIO TTS (Text-to-Speech) e STT (Speech-to-Text)
class TTSRequest(BaseModel):
    texto: str

class STTRequest(BaseModel):
    audio: str  # Base64 encoded audio

@router.post("/chat/audio/transcrever")
async def transcrever_audio(request: STTRequest):
    """
    Transcreve áudio para texto usando OpenAI Whisper.
    Recebe áudio em base64 e retorna o texto transcrito.
    """
    try:
        from app.services.openai_audio_service import get_audio_service
        import base64
        import tempfile
        import os

        audio_service = get_audio_service()

        if not audio_service:
            raise HTTPException(
                status_code=503,
                detail="Serviço de áudio não disponível"
            )

        # Decodificar áudio base64
        try:
            audio_bytes = base64.b64decode(request.audio)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Áudio base64 inválido: {str(e)}"
            )

        if len(audio_bytes) < 100:
            raise HTTPException(
                status_code=400,
                detail="Áudio muito curto ou vazio"
            )

        # Salvar temporariamente (Whisper aceita webm, mp3, wav, etc)
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        try:
            # Transcrever com Whisper
            texto = await audio_service.transcrever_audio(temp_path)

            if not texto or texto.strip() == "":
                return {
                    "status": "success",
                    "texto": "",
                    "message": "Nenhuma fala detectada"
                }

            return {
                "status": "success",
                "texto": texto.strip()
            }

        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao transcrever áudio: {str(e)}"
        )


@router.post("/chat/audio")
async def gerar_audio_tts(request: TTSRequest):
    """
    Gera áudio TTS usando OpenAI.
    Retorna o áudio em formato base64 para reprodução no navegador.
    """
    try:
        from app.services.openai_audio_service import get_audio_service
        import base64
        import os

        audio_service = get_audio_service()

        if not audio_service:
            raise HTTPException(
                status_code=503,
                detail="Serviço de áudio não disponível"
            )

        # Gerar áudio
        audio_path = await audio_service.texto_para_audio(request.texto)

        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(
                status_code=500,
                detail="Erro ao gerar áudio"
            )

        # Ler arquivo e converter para base64
        with open(audio_path, 'rb') as f:
            audio_bytes = f.read()

        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        # Limpar arquivo temporário
        audio_service.limpar_audio(audio_path)

        return {
            "status": "success",
            "audio": audio_base64,
            "format": "mp3",
            "mime_type": "audio/mpeg"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar áudio: {str(e)}"
        )


# ENDPOINTS - FORMULÁRIO DE CONTATO
class ContatoRequest(BaseModel):
    nome: str
    email: str
    telefone: str
    especialidade: Optional[str] = None
    mensagem: Optional[str] = None

@router.post("/contato")
def enviar_contato(request: ContatoRequest):
    """Recebe dados do formulário de contato e envia por email."""
    try:
        from app.services.email_service import get_email_service

        email_service = get_email_service()

        sucesso = email_service.send_contact_form(
            nome=request.nome,
            email=request.email,
            telefone=request.telefone,
            especialidade=request.especialidade or "",
            mensagem=request.mensagem or ""
        )

        if sucesso:
            return {
                "status": "success",
                "message": "Mensagem enviada com sucesso! Entraremos em contato em breve."
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Erro ao enviar mensagem. Tente novamente."
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar contato: {str(e)}"
        )
