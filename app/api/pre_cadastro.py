"""
API de Pré-Cadastro para Lançamento
Endpoints para captura de leads interessados no Horário Inteligente
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timedelta
from typing import Optional, Literal, List
import logging
import re
import io
import csv
from html import escape as html_escape

from app.database import get_db
from app.models.pre_cadastro import PreCadastro
from app.services.email_service import get_email_service
from app.api.admin import get_current_admin

# Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1", tags=["Pre-Cadastro"])
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

PROFISSOES_VALIDAS = [
    "Médico(a)",
    "Dentista",
    "Psicólogo(a)",
    "Fisioterapeuta",
    "Nutricionista",
    "Fonoaudiólogo(a)",
    "Outro profissional de saúde"
]

ORIGENS_VALIDAS = [
    "Instagram",
    "Facebook",
    "Indicação de colega",
    "Google",
    "Demo",
    "Outro"
]

USA_SISTEMA_OPCOES = [
    "Não uso nenhum",
    "Sim, uso outro sistema",
    "Uso planilhas/papel"
]


class PreCadastroCreate(BaseModel):
    """Schema para criação de pré-cadastro"""
    nome: str = Field(..., min_length=3, max_length=255, description="Nome completo")
    email: EmailStr = Field(..., description="Email válido")
    whatsapp: str = Field(..., min_length=14, max_length=16, description="WhatsApp no formato (XX) XXXXX-XXXX")
    profissao: str = Field(..., description="Profissão do lead")
    cidade_estado: str = Field(..., min_length=3, max_length=255, description="Cidade/Estado")
    usa_sistema: Optional[str] = Field(None, description="Se usa sistema de gestão")
    nome_sistema_atual: Optional[str] = Field(None, max_length=255, description="Nome do sistema atual")
    origem: Optional[str] = Field(None, description="Como conheceu o Horário Inteligente")
    aceite_comunicacao: bool = Field(True, description="Aceite de comunicação")

    @validator('whatsapp')
    def validar_whatsapp(cls, v):
        """Valida formato do WhatsApp brasileiro"""
        # Remove caracteres não numéricos para validação
        numeros = re.sub(r'\D', '', v)
        if len(numeros) < 10 or len(numeros) > 11:
            raise ValueError('WhatsApp deve ter 10 ou 11 dígitos')
        return v

    @validator('profissao')
    def validar_profissao(cls, v):
        """Valida se profissão é uma das opções válidas"""
        if v not in PROFISSOES_VALIDAS:
            raise ValueError(f'Profissão deve ser uma das opções: {", ".join(PROFISSOES_VALIDAS)}')
        return v

    @validator('aceite_comunicacao')
    def validar_aceite(cls, v):
        """Garante que aceite é obrigatório"""
        if not v:
            raise ValueError('É necessário aceitar o recebimento de comunicações')
        return v

    @validator('origem')
    def validar_origem(cls, v):
        """Valida que origem está na whitelist"""
        if v and v not in ORIGENS_VALIDAS:
            raise ValueError(f'Origem deve ser uma das opções válidas')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "nome": "Dr. João Silva",
                "email": "joao.silva@email.com",
                "whatsapp": "(21) 99999-9999",
                "profissao": "Médico(a)",
                "cidade_estado": "Rio de Janeiro/RJ",
                "usa_sistema": "Não uso nenhum",
                "nome_sistema_atual": None,
                "origem": "Instagram",
                "aceite_comunicacao": True
            }
        }


class PreCadastroResponse(BaseModel):
    """Schema de resposta para pré-cadastro"""
    success: bool
    message: str
    data: Optional[dict] = None


class PreCadastroListItem(BaseModel):
    """Schema para item da lista de pré-cadastros"""
    id: int
    nome: str
    email: str
    whatsapp: str
    profissao: str
    cidade_estado: str
    usa_sistema: Optional[str]
    nome_sistema_atual: Optional[str]
    origem: Optional[str]
    status: str
    data_cadastro: datetime


class PreCadastroStats(BaseModel):
    """Schema para estatísticas de pré-cadastros"""
    total: int
    por_profissao: dict
    por_origem: dict
    por_status: dict
    ultimos_7_dias: int
    hoje: int


# ==================== ENDPOINTS PÚBLICOS ====================

@router.post("/pre-cadastro", response_model=PreCadastroResponse, status_code=201)
@limiter.limit("5/minute")
async def criar_pre_cadastro(
    request: Request,
    dados: PreCadastroCreate,
    db: Session = Depends(get_db)
):
    """
    Cria um novo pré-cadastro de lead

    - Rate limit: 5 requisições por minuto por IP
    - Email deve ser único
    - Envia email de confirmação ao lead
    - Notifica admin sobre novo cadastro
    """
    try:
        # Verificar se email já existe
        existente = db.query(PreCadastro).filter(PreCadastro.email == dados.email.lower()).first()
        if existente:
            raise HTTPException(
                status_code=409,
                detail={
                    "success": False,
                    "message": "Este email já está cadastrado para o pré-lançamento."
                }
            )

        # Capturar IP e User Agent
        ip_origem = request.headers.get("X-Forwarded-For", request.client.host if request.client else None)
        if ip_origem and "," in ip_origem:
            ip_origem = ip_origem.split(",")[0].strip()
        user_agent = request.headers.get("User-Agent", "")[:500]  # Limitar tamanho

        # Sanitizar inputs para prevenir XSS
        nome_sanitizado = html_escape(dados.nome.strip())
        cidade_sanitizada = html_escape(dados.cidade_estado.strip())
        sistema_atual_sanitizado = html_escape(dados.nome_sistema_atual.strip()) if dados.nome_sistema_atual else None

        # Criar pré-cadastro
        pre_cadastro = PreCadastro(
            nome=nome_sanitizado,
            email=dados.email.lower().strip(),
            whatsapp=dados.whatsapp.strip(),
            profissao=dados.profissao,
            cidade_estado=cidade_sanitizada,
            usa_sistema=dados.usa_sistema,
            nome_sistema_atual=sistema_atual_sanitizado,
            origem=dados.origem,
            aceite_comunicacao=dados.aceite_comunicacao,
            status="pendente",
            ip_origem=ip_origem,
            user_agent=user_agent
        )

        db.add(pre_cadastro)
        db.commit()
        db.refresh(pre_cadastro)

        # Log sem dados sensíveis (LGPD)
        logger.info(f"Novo pre-cadastro criado: ID={pre_cadastro.id}, profissao={dados.profissao}")

        # Enviar emails em background (não bloquear resposta)
        email_service = get_email_service()

        # Email de confirmação ao lead
        try:
            email_service.send_pre_cadastro_confirmation(
                to_email=dados.email,
                to_name=dados.nome.split()[0]  # Primeiro nome
            )
        except Exception as e:
            logger.error(f"Erro ao enviar email de confirmacao: {e}")

        # Notificação ao admin (email e Telegram)
        try:
            total = db.query(PreCadastro).count()
            lead_data = {
                "nome": dados.nome,
                "email": dados.email,
                "whatsapp": dados.whatsapp,
                "profissao": dados.profissao,
                "cidade_estado": dados.cidade_estado,
                "usa_sistema": dados.usa_sistema,
                "nome_sistema_atual": dados.nome_sistema_atual,
                "origem": dados.origem,
                "data_cadastro": datetime.now().strftime("%d/%m/%Y %H:%M")
            }

            # Email para admin
            email_service.send_admin_notification_pre_cadastro(
                lead_data=lead_data,
                total_cadastros=total
            )

            # Telegram para admin
            email_service.send_telegram_pre_cadastro(
                lead_data=lead_data,
                total_cadastros=total
            )
        except Exception as e:
            logger.error(f"Erro ao enviar notificacao admin: {e}")

        return PreCadastroResponse(
            success=True,
            message="Pré-cadastro realizado com sucesso! Verifique seu email.",
            data={
                "id": pre_cadastro.id,
                "nome": pre_cadastro.nome,
                "email": pre_cadastro.email
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar pre-cadastro: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "Erro interno ao processar cadastro. Tente novamente."
            }
        )


# ==================== ENDPOINTS ADMIN ====================

@router.get("/pre-cadastros", response_model=List[PreCadastroListItem])
async def listar_pre_cadastros(
    request: Request,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    profissao: Optional[str] = Query(None),
    origem: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    data_inicio: Optional[str] = Query(None, description="Formato: YYYY-MM-DD"),
    data_fim: Optional[str] = Query(None, description="Formato: YYYY-MM-DD")
):
    """
    Lista pré-cadastros com filtros (apenas admin)

    - Paginação: skip e limit
    - Filtros: profissão, origem, status, período
    """
    try:
        query = db.query(PreCadastro)

        # Aplicar filtros
        if profissao:
            query = query.filter(PreCadastro.profissao == profissao)
        if origem:
            query = query.filter(PreCadastro.origem == origem)
        if status:
            query = query.filter(PreCadastro.status == status)
        if data_inicio:
            try:
                dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
                query = query.filter(PreCadastro.data_cadastro >= dt_inicio)
            except ValueError:
                pass
        if data_fim:
            try:
                dt_fim = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(PreCadastro.data_cadastro < dt_fim)
            except ValueError:
                pass

        # Ordenar por data mais recente
        query = query.order_by(PreCadastro.data_cadastro.desc())

        # Paginação
        pre_cadastros = query.offset(skip).limit(limit).all()

        return [
            PreCadastroListItem(
                id=pc.id,
                nome=pc.nome,
                email=pc.email,
                whatsapp=pc.whatsapp,
                profissao=pc.profissao,
                cidade_estado=pc.cidade_estado,
                usa_sistema=pc.usa_sistema,
                nome_sistema_atual=pc.nome_sistema_atual,
                origem=pc.origem,
                status=pc.status,
                data_cadastro=pc.data_cadastro
            )
            for pc in pre_cadastros
        ]

    except Exception as e:
        logger.error(f"Erro ao listar pre-cadastros: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar pré-cadastros")


@router.get("/pre-cadastros/stats", response_model=PreCadastroStats)
async def estatisticas_pre_cadastros(
    request: Request,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Retorna estatísticas dos pré-cadastros (apenas admin)
    """
    try:
        # Total
        total = db.query(PreCadastro).count()

        # Por profissão
        por_profissao_result = db.query(
            PreCadastro.profissao,
            func.count(PreCadastro.id)
        ).group_by(PreCadastro.profissao).all()
        por_profissao = {p: c for p, c in por_profissao_result}

        # Por origem
        por_origem_result = db.query(
            PreCadastro.origem,
            func.count(PreCadastro.id)
        ).group_by(PreCadastro.origem).all()
        por_origem = {o or "Não informado": c for o, c in por_origem_result}

        # Por status
        por_status_result = db.query(
            PreCadastro.status,
            func.count(PreCadastro.id)
        ).group_by(PreCadastro.status).all()
        por_status = {s: c for s, c in por_status_result}

        # Últimos 7 dias
        data_7_dias = datetime.now() - timedelta(days=7)
        ultimos_7_dias = db.query(PreCadastro).filter(
            PreCadastro.data_cadastro >= data_7_dias
        ).count()

        # Hoje
        hoje_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        hoje = db.query(PreCadastro).filter(
            PreCadastro.data_cadastro >= hoje_inicio
        ).count()

        return PreCadastroStats(
            total=total,
            por_profissao=por_profissao,
            por_origem=por_origem,
            por_status=por_status,
            ultimos_7_dias=ultimos_7_dias,
            hoje=hoje
        )

    except Exception as e:
        logger.error(f"Erro ao buscar estatisticas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar estatísticas")


@router.get("/pre-cadastros/export")
async def exportar_pre_cadastros(
    request: Request,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
    formato: str = Query("csv", description="Formato de exportação (csv)")
):
    """
    Exporta pré-cadastros em CSV (apenas admin)
    """
    try:
        pre_cadastros = db.query(PreCadastro).order_by(PreCadastro.data_cadastro.desc()).all()

        # Criar CSV em memória
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "ID", "Nome", "Email", "WhatsApp", "Profissão", "Cidade/Estado",
            "Usa Sistema", "Sistema Atual", "Origem", "Status", "Data Cadastro"
        ])

        # Dados
        for pc in pre_cadastros:
            writer.writerow([
                pc.id,
                pc.nome,
                pc.email,
                pc.whatsapp,
                pc.profissao,
                pc.cidade_estado,
                pc.usa_sistema or "",
                pc.nome_sistema_atual or "",
                pc.origem or "",
                pc.status,
                pc.data_cadastro.strftime("%d/%m/%Y %H:%M") if pc.data_cadastro else ""
            ])

        output.seek(0)

        # Retornar como arquivo
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=pre-cadastros-{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )

    except Exception as e:
        logger.error(f"Erro ao exportar pre-cadastros: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao exportar dados")


@router.patch("/pre-cadastros/{pre_cadastro_id}/status")
async def atualizar_status(
    request: Request,
    pre_cadastro_id: int,
    novo_status: str = Query(..., description="Novo status: pendente, confirmado, convertido"),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Atualiza o status de um pré-cadastro (apenas admin)
    """
    try:
        if novo_status not in ["pendente", "confirmado", "convertido"]:
            raise HTTPException(
                status_code=400,
                detail="Status inválido. Use: pendente, confirmado ou convertido"
            )

        pre_cadastro = db.query(PreCadastro).filter(PreCadastro.id == pre_cadastro_id).first()
        if not pre_cadastro:
            raise HTTPException(status_code=404, detail="Pré-cadastro não encontrado")

        pre_cadastro.status = novo_status
        db.commit()

        logger.info(f"Status atualizado: ID {pre_cadastro_id} -> {novo_status}")

        return {"success": True, "message": f"Status atualizado para {novo_status}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar status: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao atualizar status")
