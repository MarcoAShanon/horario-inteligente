"""
API Financeira - Painel Financeiro
Endpoints exclusivos para gestão financeira do SaaS Horário Inteligente
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
import logging
import bcrypt
import jwt
import os

from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/financeiro", tags=["Financeiro"])
logger = logging.getLogger(__name__)

# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("ERRO CRITICO: SECRET_KEY nao configurada. Defina a variavel de ambiente SECRET_KEY no arquivo .env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hora


# ==================== AUTENTICAÇÃO ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha está correta"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_financeiro_token(user_id: int, email: str, perfil: str) -> str:
    """Cria token JWT para usuário financeiro"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "email": email,
        "perfil": perfil,  # 'financeiro' ou 'super_admin'
        "tipo": "gestao_interna",  # Diferente dos usuários de clínicas
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_financeiro(request: Request, db: Session = Depends(get_db)):
    """Dependency para obter usuário financeiro autenticado (legado e unificado)"""
    # Extrair token do header
    auth_header = request.headers.get('Authorization') or request.headers.get('authorization')

    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não fornecido"
        )

    token = auth_header.split(' ')[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Caminho 1: Token unificado (tem source_table)
        source_table = payload.get('source_table')
        if source_table:
            user_type = payload.get('user_type')
            user_id = payload.get('sub') or payload.get('user_id')
            is_super_admin = payload.get('is_super_admin', False)

            # Validar: financeiro ou super_admin
            if user_type != 'financeiro' and not is_super_admin and user_type != 'admin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Perfil sem permissão para acesso financeiro"
                )

            # Buscar na tabela correta
            if source_table == 'usuarios_internos':
                result = db.execute(
                    text("SELECT id, nome, email, perfil, ativo FROM usuarios_internos WHERE id = :id"),
                    {"id": user_id}
                ).fetchone()
            elif source_table == 'super_admins':
                result = db.execute(
                    text("SELECT id, nome, email, 'admin' as perfil, ativo FROM super_admins WHERE id = :id"),
                    {"id": user_id}
                ).fetchone()
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tipo de usuário sem permissão financeira"
                )

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário não encontrado"
                )

            if not result[4]:  # ativo
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Conta desativada"
                )

            return {
                "id": result[0],
                "nome": result[1],
                "email": result[2],
                "perfil": result[3],
                "ativo": result[4]
            }

        # Caminho 2: Token legado (tipo=gestao_interna)
        user_id = payload.get('user_id')
        perfil = payload.get('perfil')
        tipo = payload.get('tipo')

        # Validar se é usuário de gestão interna
        if tipo != 'gestao_interna':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso restrito à gestão interna"
            )

        # Validar perfil (financeiro ou super_admin)
        if perfil not in ['financeiro', 'super_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Perfil sem permissão para acesso financeiro"
            )

        # Buscar usuário no banco
        result = db.execute(
            text("SELECT id, nome, email, perfil, ativo FROM super_admins WHERE id = :id"),
            {"id": user_id}
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado"
            )

        if not result[4]:  # ativo
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conta desativada"
            )

        return {
            "id": result[0],
            "nome": result[1],
            "email": result[2],
            "perfil": result[3],
            "ativo": result[4]
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )


@router.post("/auth/login")
async def financeiro_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login de usuário financeiro - DEPRECADO. Use /api/auth/login com JSON."""
    from app.api.auth import _unified_login_logic
    try:
        result = await _unified_login_logic(form_data.username, form_data.password, db, request)

        logger.info(f"Login financeiro (legado) bem-sucedido: {form_data.username}")

        return {
            "access_token": result["access_token"],
            "token_type": "bearer",
            "user": result["user"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no login financeiro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar login"
        )


# ==================== MÉTRICAS GERAIS ====================

@router.get("/dashboard/metricas")
async def get_metricas_gerais(
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """Retorna métricas gerais do negócio

    MRR calculado a partir das assinaturas:
    - Base do plano + profissionais adicionais + serviços extras
    """
    try:
        # Total de clientes ativos (excluir demo)
        result_clientes_ativos = db.execute(
            text("SELECT COUNT(*) FROM clientes WHERE ativo = true AND is_demo = false")
        ).scalar()

        # Total de clientes inativos (excluir demo)
        result_clientes_inativos = db.execute(
            text("SELECT COUNT(*) FROM clientes WHERE ativo = false AND is_demo = false")
        ).scalar()

        # Total de médicos ativos (excluir demo)
        result_medicos = db.execute(
            text("""
                SELECT COUNT(*) FROM medicos m
                JOIN clientes c ON m.cliente_id = c.id
                WHERE m.ativo = true AND c.is_demo = false
            """)
        ).scalar()

        # Total de agendamentos este mês - excluir cancelado, remarcado, faltou e demo
        result_agendamentos_mes = db.execute(
            text("""
                SELECT COUNT(*) FROM agendamentos a
                WHERE EXTRACT(MONTH FROM a.data_hora) = EXTRACT(MONTH FROM CURRENT_DATE)
                AND EXTRACT(YEAR FROM a.data_hora) = EXTRACT(YEAR FROM CURRENT_DATE)
                AND a.status NOT IN ('cancelado', 'remarcado', 'faltou')
                AND a.medico_id NOT IN (
                    SELECT m.id FROM medicos m
                    JOIN clientes c ON m.cliente_id = c.id
                    WHERE c.is_demo = true
                )
            """)
        ).scalar()

        # Novos clientes últimos 7 dias (excluir demo)
        result_novos_clientes = db.execute(
            text("""
                SELECT COUNT(*) FROM clientes
                WHERE criado_em >= CURRENT_DATE - INTERVAL '7 days'
                AND is_demo = false
            """)
        ).scalar()

        clientes_ativos = result_clientes_ativos or 0
        medicos_ativos = result_medicos or 0

        # ============ MRR BASEADO EM ASSINATURAS ============
        # Buscar assinaturas ativas com dados do plano (excluir demo)
        result_assinaturas = db.execute(
            text("""
                SELECT
                    a.id,
                    a.valor_mensal,
                    a.valor_profissional_adicional,
                    a.profissionais_contratados,
                    a.numero_virtual_salvy,
                    a.valor_numero_virtual,
                    p.profissionais_inclusos
                FROM assinaturas a
                JOIN planos p ON p.id = a.plano_id
                WHERE a.status = 'ativa'
                AND a.data_fim IS NULL
                AND a.cliente_id NOT IN (SELECT id FROM clientes WHERE is_demo = true)
            """)
        ).fetchall()

        mrr_base = Decimal('0')
        mrr_adicionais = Decimal('0')
        mrr_servicos = Decimal('0')
        total_profissionais_adicionais = 0

        for assinatura in result_assinaturas:
            valor_mensal = Decimal(str(assinatura[1] or 0))
            valor_prof_adicional = Decimal(str(assinatura[2] or 50))
            profissionais_contratados = assinatura[3] or 1
            numero_virtual = assinatura[4] or False
            valor_numero_virtual = Decimal(str(assinatura[5] or 40))
            profissionais_inclusos = assinatura[6] or 1

            # Base do plano
            mrr_base += valor_mensal

            # Profissionais adicionais
            adicionais = max(0, profissionais_contratados - profissionais_inclusos)
            mrr_adicionais += adicionais * valor_prof_adicional
            total_profissionais_adicionais += adicionais

            # Serviços extras (número virtual)
            if numero_virtual:
                mrr_servicos += valor_numero_virtual

        mrr = mrr_base + mrr_adicionais + mrr_servicos
        assinaturas_ativas = len(result_assinaturas)

        # Ticket médio por assinatura
        ticket_medio = float(mrr) / assinaturas_ativas if assinaturas_ativas > 0 else 0

        return {
            "success": True,
            "data": {
                "clientes_ativos": clientes_ativos,
                "clientes_inativos": result_clientes_inativos or 0,
                "total_clientes": clientes_ativos + (result_clientes_inativos or 0),
                "total_medicos": medicos_ativos,
                "agendamentos_mes": result_agendamentos_mes or 0,
                "novos_clientes_7dias": result_novos_clientes or 0,
                "assinaturas_ativas": assinaturas_ativas,
                "mrr": round(float(mrr), 2),
                "mrr_detalhes": {
                    "base": round(float(mrr_base), 2),
                    "adicionais": round(float(mrr_adicionais), 2),
                    "servicos": round(float(mrr_servicos), 2),
                    "profissionais_adicionais": total_profissionais_adicionais
                },
                "ticket_medio": round(ticket_medio, 2)
            }
        }

    except Exception as e:
        logger.error(f"Erro ao buscar métricas gerais: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar métricas"
        )


@router.get("/dashboard/clientes")
async def get_clientes_detalhado(
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """Retorna lista detalhada de clientes com informações financeiras"""
    try:
        result = db.execute(
            text("""
                SELECT
                    c.id,
                    c.nome,
                    c.subdomain,
                    c.plano,
                    c.ativo,
                    c.criado_em,
                    COUNT(DISTINCT m.id) as total_medicos,
                    COUNT(DISTINCT CASE WHEN m.ativo = true THEN m.id END) as medicos_ativos
                FROM clientes c
                LEFT JOIN medicos m ON m.cliente_id = c.id
                WHERE c.is_demo = false
                GROUP BY c.id, c.nome, c.subdomain, c.plano, c.ativo, c.criado_em
                ORDER BY c.criado_em DESC
            """)
        ).fetchall()

        # Valores conforme Plano de Negócios v1.1
        VALOR_BASE_CLIENTE = 150.00
        VALOR_PROFISSIONAL_ADICIONAL = 50.00

        clientes = []
        for row in result:
            medicos_ativos = row[7] or 0
            # R$ 150 base + R$ 50 por profissional adicional (além do 1º)
            profissionais_adicionais = max(0, medicos_ativos - 1)
            valor_mensal = VALOR_BASE_CLIENTE + (profissionais_adicionais * VALOR_PROFISSIONAL_ADICIONAL)

            clientes.append({
                "id": row[0],
                "nome": row[1],
                "subdomain": row[2],
                "plano": row[3],
                "ativo": row[4],
                "criado_em": row[5].strftime("%Y-%m-%d") if row[5] else None,
                "total_medicos": row[6] or 0,
                "medicos_ativos": medicos_ativos,
                "valor_mensal": valor_mensal,
                "profissionais_adicionais": profissionais_adicionais,
                "url": f"https://{row[2]}.horariointeligente.com.br"
            })

        return {
            "success": True,
            "data": clientes,
            "total": len(clientes)
        }

    except Exception as e:
        logger.error(f"Erro ao buscar clientes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar lista de clientes"
        )


@router.get("/dashboard/custos")
async def get_custos_operacionais(
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """Retorna custos operacionais estimados incluindo despesas cadastradas

    Valores atualizados conforme Plano de Negócios v1.1:
    - IA Claude Haiku: R$ 0,50/cliente/mês (~385 chamadas × R$ 0,0012)
    - Infraestrutura: R$ 173,41 (VPS R$ 160 + Domínio R$ 5,42 + Email R$ 7,99)
    - Custos variáveis por cliente: R$ 19,49
    """
    try:
        # Total de clientes ativos (base para cálculo de custos, excluir demo)
        result_clientes = db.execute(
            text("SELECT COUNT(*) FROM clientes WHERE ativo = true AND is_demo = false")
        ).scalar()
        total_clientes = result_clientes or 0

        # Total de médicos ativos (excluir demo)
        result_medicos = db.execute(
            text("""
                SELECT COUNT(*) FROM medicos m
                JOIN clientes c ON m.cliente_id = c.id
                WHERE m.ativo = true AND c.is_demo = false
            """)
        ).scalar()
        total_medicos = result_medicos or 0

        # ============ CUSTOS FIXOS (Plano de Negócios) ============
        # Infraestrutura mensal
        CUSTO_VPS = 160.00          # VPS Hostinger
        CUSTO_DOMINIO = 5.42        # Domínio .com.br (R$ 65/ano ÷ 12)
        CUSTO_EMAIL = 7.99          # E-mail profissional Hostinger
        CUSTO_INFRAESTRUTURA = CUSTO_VPS + CUSTO_DOMINIO + CUSTO_EMAIL  # R$ 173,41

        # ============ CUSTOS VARIÁVEIS POR CLIENTE ============
        # Conforme Plano de Negócios v1.1
        CUSTO_WHATSAPP_API = 4.00       # ~80 lembretes utility × R$ 0,05
        CUSTO_CLAUDE_HAIKU = 0.50       # ~385 chamadas × R$ 0,0012
        CUSTO_GATEWAY_PAGAMENTO = 5.99  # PagSeguro 3,99% sobre R$ 150
        CUSTO_SIMPLES_NACIONAL = 9.00   # 6% sobre R$ 150
        CUSTO_VARIAVEL_CLIENTE = CUSTO_WHATSAPP_API + CUSTO_CLAUDE_HAIKU + CUSTO_GATEWAY_PAGAMENTO + CUSTO_SIMPLES_NACIONAL  # R$ 19,49

        # Total de custos variáveis
        custo_variaveis_total = total_clientes * CUSTO_VARIAVEL_CLIENTE
        custo_ia_total = total_clientes * CUSTO_CLAUDE_HAIKU

        # ============ DESPESAS CADASTRADAS ============
        # Buscar despesas cadastradas (fixas recorrentes)
        # Considera periodicidade: anuais são divididas por 12
        result_despesas_fixas = db.execute(
            text("""
                SELECT
                    COALESCE(SUM(
                        CASE
                            WHEN periodicidade = 'anual' THEN valor / 12
                            ELSE valor
                        END
                    ), 0) as total
                FROM despesas
                WHERE categoria = 'fixa'
                AND recorrente = true
                AND status != 'cancelado'
            """)
        ).scalar()

        # Buscar despesas variáveis do mês atual
        result_despesas_variaveis = db.execute(
            text("""
                SELECT COALESCE(SUM(valor), 0) as total
                FROM despesas
                WHERE categoria = 'variavel'
                AND status != 'cancelado'
                AND EXTRACT(MONTH FROM data_vencimento) = EXTRACT(MONTH FROM CURRENT_DATE)
                AND EXTRACT(YEAR FROM data_vencimento) = EXTRACT(YEAR FROM CURRENT_DATE)
            """)
        ).scalar()

        despesas_fixas_cadastradas = float(result_despesas_fixas or 0)
        despesas_variaveis_cadastradas = float(result_despesas_variaveis or 0)
        despesas_total = despesas_fixas_cadastradas + despesas_variaveis_cadastradas

        # ============ CUSTO TOTAL ============
        custo_fixo_total = CUSTO_INFRAESTRUTURA + despesas_fixas_cadastradas
        custo_total = custo_fixo_total + custo_variaveis_total + despesas_variaveis_cadastradas

        # ============ RECEITA BASEADA EM ASSINATURAS ============
        # Buscar assinaturas ativas e calcular MRR real (excluir demo)
        result_assinaturas = db.execute(
            text("""
                SELECT
                    a.valor_mensal,
                    a.valor_profissional_adicional,
                    a.profissionais_contratados,
                    a.numero_virtual_salvy,
                    a.valor_numero_virtual,
                    p.profissionais_inclusos
                FROM assinaturas a
                JOIN planos p ON p.id = a.plano_id
                WHERE a.status = 'ativa'
                AND a.data_fim IS NULL
                AND a.cliente_id NOT IN (SELECT id FROM clientes WHERE is_demo = true)
            """)
        ).fetchall()

        receita = Decimal('0')
        for assinatura in result_assinaturas:
            valor_mensal = Decimal(str(assinatura[0] or 0))
            valor_prof_adicional = Decimal(str(assinatura[1] or 50))
            profissionais_contratados = assinatura[2] or 1
            numero_virtual = assinatura[3] or False
            valor_numero_virtual = Decimal(str(assinatura[4] or 40))
            profissionais_inclusos = assinatura[5] or 1

            receita += valor_mensal
            adicionais = max(0, profissionais_contratados - profissionais_inclusos)
            receita += adicionais * valor_prof_adicional
            if numero_virtual:
                receita += valor_numero_virtual

        assinaturas_ativas = len(result_assinaturas)
        receita_por_assinatura = float(receita) / assinaturas_ativas if assinaturas_ativas > 0 else 0

        # ============ MARGEM E LUCRO ============
        margem_por_cliente = receita_por_assinatura - CUSTO_VARIAVEL_CLIENTE
        lucro = float(receita) - custo_total
        margem_percentual = (margem_por_cliente / receita_por_assinatura * 100) if receita_por_assinatura > 0 else 0

        # Break-even: quantos clientes para cobrir custos fixos
        break_even = int((custo_fixo_total / margem_por_cliente) + 1) if margem_por_cliente > 0 else 0

        return {
            "success": True,
            "data": {
                "total_clientes": total_clientes,
                "total_medicos": total_medicos,
                "custos": {
                    "ia_claude": {
                        "por_cliente": CUSTO_CLAUDE_HAIKU,
                        "total": round(custo_ia_total, 2),
                        "modelo": "Claude Haiku",
                        "chamadas_estimadas": 385
                    },
                    "infraestrutura": {
                        "servidor_vps": CUSTO_VPS,
                        "dominio": CUSTO_DOMINIO,
                        "email": CUSTO_EMAIL,
                        "total": CUSTO_INFRAESTRUTURA
                    },
                    "custos_variaveis_cliente": {
                        "whatsapp_api": CUSTO_WHATSAPP_API,
                        "claude_haiku": CUSTO_CLAUDE_HAIKU,
                        "gateway_pagamento": CUSTO_GATEWAY_PAGAMENTO,
                        "simples_nacional": CUSTO_SIMPLES_NACIONAL,
                        "total_por_cliente": CUSTO_VARIAVEL_CLIENTE,
                        "total": round(custo_variaveis_total, 2)
                    },
                    "despesas_cadastradas": {
                        "fixas": despesas_fixas_cadastradas,
                        "variaveis": despesas_variaveis_cadastradas,
                        "total": despesas_total
                    },
                    "custos_fixos_total": round(custo_fixo_total, 2),
                    "custos_variaveis_total": round(custo_variaveis_total + despesas_variaveis_cadastradas, 2),
                    "total_mensal": round(custo_total, 2)
                },
                "receita": {
                    "mrr": round(float(receita), 2),
                    "por_assinatura": round(receita_por_assinatura, 2),
                    "assinaturas_ativas": assinaturas_ativas
                },
                "lucro": {
                    "mensal": round(lucro, 2),
                    "margem_por_cliente": round(margem_por_cliente, 2),
                    "margem_percentual": round(margem_percentual, 2)
                },
                "analise": {
                    "break_even_assinaturas": break_even,
                    "assinaturas_atuais": assinaturas_ativas,
                    "status_break_even": "Atingido" if assinaturas_ativas >= break_even else f"Faltam {break_even - assinaturas_ativas} assinaturas"
                }
            }
        }

    except Exception as e:
        logger.error(f"Erro ao calcular custos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao calcular custos operacionais"
        )


@router.get("/relatorios/faturamento")
async def get_relatorio_faturamento(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """Retorna relatório de faturamento por período"""
    try:
        # Usar mês/ano atual se não especificado
        if not mes or not ano:
            hoje = date.today()
            mes = hoje.month
            ano = hoje.year

        # Buscar dados de faturamento por cliente
        # NOTA: Excluir status cancelado, remarcado e faltou do total
        result = db.execute(
            text("""
                SELECT
                    c.id,
                    c.nome,
                    c.subdomain,
                    COUNT(DISTINCT m.id) as medicos_ativos,
                    COUNT(CASE WHEN a.status NOT IN ('cancelado', 'remarcado', 'faltou') THEN a.id END) as total_agendamentos,
                    COUNT(CASE WHEN a.status IN ('realizado', 'realizada', 'concluido', 'concluida') THEN 1 END) as agendamentos_realizados
                FROM clientes c
                LEFT JOIN medicos m ON m.cliente_id = c.id AND m.ativo = true
                LEFT JOIN agendamentos a ON a.medico_id = m.id
                    AND EXTRACT(MONTH FROM a.data_hora) = :mes
                    AND EXTRACT(YEAR FROM a.data_hora) = :ano
                WHERE c.ativo = true AND c.is_demo = false
                GROUP BY c.id, c.nome, c.subdomain
                ORDER BY c.nome
            """),
            {"mes": mes, "ano": ano}
        ).fetchall()

        # Valores conforme Plano de Negócios v1.1
        VALOR_BASE_CLIENTE = 150.00
        VALOR_PROFISSIONAL_ADICIONAL = 50.00

        relatorio = []
        for row in result:
            medicos_ativos = row[3] or 0
            # R$ 150 base + R$ 50 por profissional adicional
            profissionais_adicionais = max(0, medicos_ativos - 1)
            faturamento = VALOR_BASE_CLIENTE + (profissionais_adicionais * VALOR_PROFISSIONAL_ADICIONAL)

            relatorio.append({
                "cliente_id": row[0],
                "cliente_nome": row[1],
                "subdomain": row[2],
                "medicos_ativos": medicos_ativos,
                "profissionais_adicionais": profissionais_adicionais,
                "faturamento_mensal": faturamento,
                "agendamentos": {
                    "total": row[4] or 0,
                    "realizados": row[5] or 0
                }
            })

        total_faturamento = sum(item['faturamento_mensal'] for item in relatorio)

        return {
            "success": True,
            "periodo": {
                "mes": mes,
                "ano": ano
            },
            "data": relatorio,
            "resumo": {
                "total_clientes": len(relatorio),
                "faturamento_total": total_faturamento
            }
        }

    except Exception as e:
        logger.error(f"Erro ao gerar relatório de faturamento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar relatório"
        )


# ==================== GESTÃO DE DESPESAS ====================

@router.get("/despesas")
async def listar_despesas(
    categoria: Optional[str] = None,  # 'fixa' ou 'variavel'
    status: Optional[str] = None,  # 'pendente', 'pago', 'cancelado'
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """Lista todas as despesas com filtros opcionais"""
    try:
        query = "SELECT * FROM despesas WHERE 1=1"
        params = {}

        if categoria:
            query += " AND categoria = :categoria"
            params["categoria"] = categoria

        if status:
            query += " AND status = :status"
            params["status"] = status

        if mes and ano:
            query += """ AND (
                EXTRACT(MONTH FROM data_vencimento) = :mes
                AND EXTRACT(YEAR FROM data_vencimento) = :ano
            )"""
            params["mes"] = mes
            params["ano"] = ano

        query += " ORDER BY data_vencimento DESC, criado_em DESC"

        result = db.execute(text(query), params).fetchall()

        despesas = []
        for row in result:
            despesas.append({
                "id": row[0],
                "descricao": row[1],
                "categoria": row[2],
                "tipo": row[3],
                "valor": float(row[4]) if row[4] else 0,
                "data_vencimento": row[5].strftime("%Y-%m-%d") if row[5] else None,
                "data_pagamento": row[6].strftime("%Y-%m-%d") if row[6] else None,
                "recorrente": row[7],
                "dia_recorrencia": row[8],
                "status": row[9],
                "observacoes": row[10],
                "comprovante_url": row[11],
                "criado_em": row[12].strftime("%Y-%m-%d %H:%M") if row[12] else None,
                "periodicidade": row[14] if len(row) > 14 else "mensal"
            })

        # Calcular totais
        total_fixas = sum(d['valor'] for d in despesas if d['categoria'] == 'fixa')
        total_variaveis = sum(d['valor'] for d in despesas if d['categoria'] == 'variavel')
        total_pendente = sum(d['valor'] for d in despesas if d['status'] == 'pendente')
        total_pago = sum(d['valor'] for d in despesas if d['status'] == 'pago')

        return {
            "success": True,
            "data": despesas,
            "resumo": {
                "total_despesas": len(despesas),
                "total_fixas": round(total_fixas, 2),
                "total_variaveis": round(total_variaveis, 2),
                "total_pendente": round(total_pendente, 2),
                "total_pago": round(total_pago, 2),
                "total_geral": round(total_fixas + total_variaveis, 2)
            }
        }

    except Exception as e:
        logger.error(f"Erro ao listar despesas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar despesas"
        )


@router.post("/despesas")
async def criar_despesa(
    request: Request,
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """Cria uma nova despesa"""
    try:
        data = await request.json()

        # Validar campos obrigatórios
        if not data.get('descricao'):
            raise HTTPException(status_code=400, detail="Descrição é obrigatória")
        if not data.get('categoria'):
            raise HTTPException(status_code=400, detail="Categoria é obrigatória (fixa ou variavel)")
        if not data.get('valor'):
            raise HTTPException(status_code=400, detail="Valor é obrigatório")

        # Inserir despesa
        result = db.execute(
            text("""
                INSERT INTO despesas (
                    descricao, categoria, tipo, valor, data_vencimento,
                    recorrente, dia_recorrencia, periodicidade, status, observacoes, criado_por
                ) VALUES (
                    :descricao, :categoria, :tipo, :valor, :data_vencimento,
                    :recorrente, :dia_recorrencia, :periodicidade, :status, :observacoes, :criado_por
                ) RETURNING id
            """),
            {
                "descricao": data['descricao'],
                "categoria": data['categoria'],
                "tipo": data.get('tipo'),
                "valor": data['valor'],
                "data_vencimento": data.get('data_vencimento'),
                "recorrente": data.get('recorrente', False),
                "dia_recorrencia": data.get('dia_recorrencia'),
                "periodicidade": data.get('periodicidade', 'mensal'),
                "status": data.get('status', 'pendente'),
                "observacoes": data.get('observacoes'),
                "criado_por": current_user['id']
            }
        )

        despesa_id = result.fetchone()[0]
        db.commit()

        logger.info(f"Despesa criada: ID {despesa_id} por {current_user['email']}")

        return {
            "success": True,
            "message": "Despesa criada com sucesso",
            "id": despesa_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar despesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar despesa"
        )


@router.put("/despesas/{despesa_id}")
async def atualizar_despesa(
    despesa_id: int,
    request: Request,
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """Atualiza uma despesa existente"""
    try:
        data = await request.json()

        # Verificar se despesa existe
        exists = db.execute(
            text("SELECT id FROM despesas WHERE id = :id"),
            {"id": despesa_id}
        ).fetchone()

        if not exists:
            raise HTTPException(status_code=404, detail="Despesa não encontrada")

        # Montar query de update dinamicamente
        updates = []
        params = {"id": despesa_id}

        campos = ['descricao', 'categoria', 'tipo', 'valor', 'data_vencimento',
                  'data_pagamento', 'recorrente', 'dia_recorrencia', 'periodicidade', 'status', 'observacoes']

        for campo in campos:
            if campo in data:
                updates.append(f"{campo} = :{campo}")
                params[campo] = data[campo]

        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

        updates.append("atualizado_em = NOW()")

        query = f"UPDATE despesas SET {', '.join(updates)} WHERE id = :id"
        db.execute(text(query), params)
        db.commit()

        logger.info(f"Despesa {despesa_id} atualizada por {current_user['email']}")

        return {
            "success": True,
            "message": "Despesa atualizada com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar despesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar despesa"
        )


@router.delete("/despesas/{despesa_id}")
async def deletar_despesa(
    despesa_id: int,
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """Deleta uma despesa"""
    try:
        # Verificar se despesa existe
        exists = db.execute(
            text("SELECT id FROM despesas WHERE id = :id"),
            {"id": despesa_id}
        ).fetchone()

        if not exists:
            raise HTTPException(status_code=404, detail="Despesa não encontrada")

        db.execute(text("DELETE FROM despesas WHERE id = :id"), {"id": despesa_id})
        db.commit()

        logger.info(f"Despesa {despesa_id} deletada por {current_user['email']}")

        return {
            "success": True,
            "message": "Despesa deletada com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao deletar despesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao deletar despesa"
        )


@router.post("/despesas/{despesa_id}/pagar")
async def marcar_como_pago(
    despesa_id: int,
    request: Request,
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """Marca uma despesa como paga"""
    try:
        data = await request.json() if request.headers.get('content-type') == 'application/json' else {}
        data_pagamento = data.get('data_pagamento', date.today().isoformat())

        # Verificar se despesa existe
        exists = db.execute(
            text("SELECT id FROM despesas WHERE id = :id"),
            {"id": despesa_id}
        ).fetchone()

        if not exists:
            raise HTTPException(status_code=404, detail="Despesa não encontrada")

        db.execute(
            text("""
                UPDATE despesas
                SET status = 'pago', data_pagamento = :data_pagamento, atualizado_em = NOW()
                WHERE id = :id
            """),
            {"id": despesa_id, "data_pagamento": data_pagamento}
        )
        db.commit()

        logger.info(f"Despesa {despesa_id} marcada como paga por {current_user['email']}")

        return {
            "success": True,
            "message": "Despesa marcada como paga"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao marcar despesa como paga: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar despesa"
        )


@router.get("/despesas/resumo-mensal")
async def resumo_despesas_mensal(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """Retorna resumo mensal de despesas para integração com custos"""
    try:
        if not mes or not ano:
            hoje = date.today()
            mes = hoje.month
            ano = hoje.year

        # Despesas fixas (recorrentes - contam todo mês)
        # Considera periodicidade: anuais são divididas por 12
        result_fixas = db.execute(
            text("""
                SELECT COALESCE(SUM(
                    CASE
                        WHEN periodicidade = 'anual' THEN valor / 12
                        ELSE valor
                    END
                ), 0) as total
                FROM despesas
                WHERE categoria = 'fixa'
                AND recorrente = true
                AND status != 'cancelado'
            """)
        ).scalar()

        # Despesas variáveis do mês específico
        result_variaveis = db.execute(
            text("""
                SELECT COALESCE(SUM(valor), 0) as total
                FROM despesas
                WHERE categoria = 'variavel'
                AND status != 'cancelado'
                AND EXTRACT(MONTH FROM data_vencimento) = :mes
                AND EXTRACT(YEAR FROM data_vencimento) = :ano
            """),
            {"mes": mes, "ano": ano}
        ).scalar()

        # Despesas fixas não recorrentes do mês
        result_fixas_mes = db.execute(
            text("""
                SELECT COALESCE(SUM(valor), 0) as total
                FROM despesas
                WHERE categoria = 'fixa'
                AND recorrente = false
                AND status != 'cancelado'
                AND EXTRACT(MONTH FROM data_vencimento) = :mes
                AND EXTRACT(YEAR FROM data_vencimento) = :ano
            """),
            {"mes": mes, "ano": ano}
        ).scalar()

        total_fixas = float(result_fixas or 0) + float(result_fixas_mes or 0)
        total_variaveis = float(result_variaveis or 0)

        return {
            "success": True,
            "periodo": {"mes": mes, "ano": ano},
            "data": {
                "despesas_fixas": round(total_fixas, 2),
                "despesas_variaveis": round(total_variaveis, 2),
                "total_despesas": round(total_fixas + total_variaveis, 2)
            }
        }

    except Exception as e:
        logger.error(f"Erro ao calcular resumo mensal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao calcular resumo"
        )


# ==================== TRIBUTAÇÃO E FATOR R ====================

def calcular_irrf(base: float) -> dict:
    """
    Calcula IRRF conforme tabela progressiva 2025.
    Base = Pró-labore - INSS

    Tabela IRRF 2025:
    - Até R$ 2.428,80: Isento
    - De R$ 2.428,81 até R$ 2.826,65: 7,5% - R$ 182,16
    - De R$ 2.826,66 até R$ 3.751,05: 15% - R$ 394,16
    - De R$ 3.751,06 até R$ 4.664,68: 22,5% - R$ 675,49
    - Acima de R$ 4.664,68: 27,5% - R$ 908,73
    """
    faixas = [
        (2428.80, 0, 0, "Isento"),
        (2826.65, 0.075, 182.16, "7,5%"),
        (3751.05, 0.15, 394.16, "15%"),
        (4664.68, 0.225, 675.49, "22,5%"),
        (float('inf'), 0.275, 908.73, "27,5%")
    ]

    for limite, aliquota, deducao, faixa_nome in faixas:
        if base <= limite:
            if aliquota == 0:
                return {
                    "valor": 0,
                    "aliquota_efetiva": 0,
                    "faixa": faixa_nome,
                    "base_calculo": round(base, 2)
                }
            valor = (base * aliquota) - deducao
            aliquota_efetiva = (valor / base) * 100 if base > 0 else 0
            return {
                "valor": round(max(0, valor), 2),
                "aliquota_efetiva": round(aliquota_efetiva, 2),
                "faixa": faixa_nome,
                "base_calculo": round(base, 2)
            }

    return {"valor": 0, "aliquota_efetiva": 0, "faixa": "Erro", "base_calculo": base}


@router.get("/simulador/fator-r")
async def simular_fator_r(
    receita_mensal: float,
    pro_labore: Optional[float] = None,
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """
    Simula Fator R e determina enquadramento tributário.

    Fator R = (Folha de Pagamento / Receita Bruta) × 100

    Se Fator R >= 28%: Anexo III (~6%)
    Se Fator R < 28%: Anexo V (~15,5%)

    Parâmetros:
    - receita_mensal: Receita bruta mensal (MRR)
    - pro_labore: Valor do pró-labore (opcional - se não informado, calcula ideal)
    """
    try:
        SALARIO_MINIMO = 1518.00
        ALIQUOTA_INSS = 0.11

        # Se não informou pró-labore, sugerir o mínimo para Anexo III
        if pro_labore is None:
            pro_labore_sugerido = receita_mensal * 0.28
            pro_labore = max(pro_labore_sugerido, SALARIO_MINIMO)

        # Garantir mínimo de 1 SM
        pro_labore = max(pro_labore, SALARIO_MINIMO)

        # Calcular Fator R
        fator_r = (pro_labore / receita_mensal) * 100 if receita_mensal > 0 else 0

        # Determinar anexo
        if fator_r >= 28:
            anexo = "III"
            aliquota_simples = 6.0
            descricao = "Tributação favorável - Serviços tributados como indústria"
        else:
            anexo = "V"
            aliquota_simples = 15.5
            descricao = "Tributação desfavorável - Serviços profissionais"

        # Calcular INSS
        inss = pro_labore * ALIQUOTA_INSS

        # Calcular IRRF (base = pró-labore - INSS)
        base_irrf = pro_labore - inss
        irrf_calculo = calcular_irrf(base_irrf)

        # Calcular DAS (Simples Nacional)
        das = receita_mensal * (aliquota_simples / 100)

        # Totais
        total_tributos = inss + irrf_calculo['valor'] + das
        liquido_socio = pro_labore - inss - irrf_calculo['valor']

        # Comparativo com outro anexo
        if anexo == "III":
            das_outro = receita_mensal * 0.155
            economia = das_outro - das
            mensagem_economia = f"Você está economizando R$ {economia:.2f}/mês com Anexo III"
        else:
            pro_labore_ideal = receita_mensal * 0.28
            das_anexo_iii = receita_mensal * 0.06
            economia_potencial = das - das_anexo_iii
            mensagem_economia = f"Aumente pró-labore para R$ {pro_labore_ideal:.2f} para economizar R$ {economia_potencial:.2f}/mês"

        # Pro-labore ideal para Anexo III
        pro_labore_ideal_anexo_iii = max(receita_mensal * 0.28, SALARIO_MINIMO)

        return {
            "success": True,
            "entrada": {
                "receita_mensal": receita_mensal,
                "pro_labore": pro_labore
            },
            "fator_r": {
                "valor": round(fator_r, 2),
                "minimo_anexo_iii": 28.0,
                "status": "OK" if fator_r >= 28 else "ATENÇÃO"
            },
            "enquadramento": {
                "anexo": anexo,
                "aliquota": aliquota_simples,
                "descricao": descricao
            },
            "encargos": {
                "inss": {
                    "aliquota": 11,
                    "valor": round(inss, 2),
                    "descricao": "INSS sobre pró-labore"
                },
                "irrf": {
                    "base_calculo": round(base_irrf, 2),
                    "faixa": irrf_calculo['faixa'],
                    "aliquota_efetiva": irrf_calculo['aliquota_efetiva'],
                    "valor": irrf_calculo['valor']
                },
                "das_simples": {
                    "anexo": anexo,
                    "aliquota": aliquota_simples,
                    "valor": round(das, 2)
                }
            },
            "resumo": {
                "total_tributos": round(total_tributos, 2),
                "percentual_carga": round((total_tributos / receita_mensal) * 100, 2) if receita_mensal > 0 else 0,
                "liquido_socio": round(liquido_socio, 2),
                "lucro_apos_tributos": round(receita_mensal - total_tributos, 2)
            },
            "recomendacao": mensagem_economia,
            "pro_labore_sugerido": {
                "para_anexo_iii": round(pro_labore_ideal_anexo_iii, 2),
                "minimo_legal": SALARIO_MINIMO
            }
        }

    except Exception as e:
        logger.error(f"Erro ao simular Fator R: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao simular tributação"
        )


@router.get("/simulador/cenarios")
async def simular_cenarios_crescimento(
    clientes_inicial: int = 10,
    clientes_final: int = 50,
    passo: int = 10,
    ticket_medio: float = 150.00,
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """
    Simula cenários de crescimento com análise tributária.

    Mostra projeções de:
    - MRR por quantidade de clientes
    - Pró-labore ideal para Anexo III
    - Tributos em cada cenário
    - Lucro líquido
    """
    try:
        SALARIO_MINIMO = 1518.00
        ALIQUOTA_INSS = 0.11
        CUSTO_VARIAVEL_CLIENTE = 19.49

        # Buscar custos fixos
        result_despesas = db.execute(
            text("""
                SELECT COALESCE(SUM(
                    CASE WHEN periodicidade = 'anual' THEN valor / 12 ELSE valor END
                ), 0)
                FROM despesas
                WHERE categoria = 'fixa' AND recorrente = true AND status != 'cancelado'
            """)
        ).scalar()

        custos_fixos_cadastrados = float(result_despesas or 0)
        custos_infra = 173.41  # VPS + Domínio + Email
        custos_fixos_total = custos_infra + custos_fixos_cadastrados

        cenarios = []

        for num_clientes in range(clientes_inicial, clientes_final + 1, passo):
            mrr = num_clientes * ticket_medio
            custos_variaveis = num_clientes * CUSTO_VARIAVEL_CLIENTE

            # Pro-labore ideal para Anexo III
            pro_labore_ideal = max(mrr * 0.28, SALARIO_MINIMO)

            # INSS
            inss = pro_labore_ideal * ALIQUOTA_INSS

            # IRRF
            base_irrf = pro_labore_ideal - inss
            irrf_calc = calcular_irrf(base_irrf)

            # DAS (Anexo III = 6%)
            das = mrr * 0.06

            # Totais
            total_tributos = inss + irrf_calc['valor'] + das
            custo_total = custos_fixos_total + custos_variaveis + total_tributos
            lucro_liquido = mrr - custo_total

            # Margem líquida
            margem_liquida = (lucro_liquido / mrr) * 100 if mrr > 0 else 0

            cenarios.append({
                "clientes": num_clientes,
                "mrr": round(mrr, 2),
                "custos": {
                    "fixos": round(custos_fixos_total, 2),
                    "variaveis": round(custos_variaveis, 2),
                    "tributos": round(total_tributos, 2),
                    "total": round(custo_total, 2)
                },
                "tributacao": {
                    "pro_labore_ideal": round(pro_labore_ideal, 2),
                    "inss": round(inss, 2),
                    "irrf": round(irrf_calc['valor'], 2),
                    "das": round(das, 2),
                    "anexo": "III"
                },
                "resultado": {
                    "lucro_liquido": round(lucro_liquido, 2),
                    "margem_liquida": round(margem_liquida, 2)
                }
            })

        # Encontrar break-even
        break_even = None
        for c in cenarios:
            if c['resultado']['lucro_liquido'] > 0:
                break_even = c['clientes']
                break

        return {
            "success": True,
            "parametros": {
                "ticket_medio": ticket_medio,
                "custos_fixos": round(custos_fixos_total, 2),
                "custo_variavel_cliente": CUSTO_VARIAVEL_CLIENTE
            },
            "cenarios": cenarios,
            "analise": {
                "break_even_estimado": break_even,
                "melhor_cenario": cenarios[-1] if cenarios else None
            }
        }

    except Exception as e:
        logger.error(f"Erro ao simular cenários: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao simular cenários"
        )


@router.get("/simulador/equilibrio-tributario")
async def simular_equilibrio_tributario(
    ticket_medio: float = 150.00,
    clientes_max: int = 200,
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """
    Simulador de Equilíbrio Tributário: Anexo III vs Anexo V

    Compara dois cenários:
    - Anexo III: Pró-labore = 28% da receita (Fator R >= 28%, DAS 6%)
    - Anexo V: Pró-labore = Salário Mínimo (Fator R baixo, DAS 15,5%)

    Identifica o ponto de equilíbrio onde um se torna mais vantajoso que o outro.
    """
    try:
        SALARIO_MINIMO = 1518.00
        ALIQUOTA_INSS = 0.11
        ALIQUOTA_DAS_III = 0.06
        ALIQUOTA_DAS_V = 0.155
        CUSTO_VARIAVEL_CLIENTE = 19.49

        # Buscar custos fixos
        result_despesas = db.execute(
            text("""
                SELECT COALESCE(SUM(
                    CASE WHEN periodicidade = 'anual' THEN valor / 12 ELSE valor END
                ), 0)
                FROM despesas
                WHERE categoria = 'fixa' AND recorrente = true AND status != 'cancelado'
            """)
        ).scalar()

        custos_fixos_cadastrados = float(result_despesas or 0)
        custos_infra = 173.41
        custos_fixos_total = custos_infra + custos_fixos_cadastrados

        comparativos = []
        ponto_equilibrio = None
        ponto_equilibrio_lucro = None

        for n_clientes in range(5, clientes_max + 1, 5):
            receita = n_clientes * ticket_medio
            custos_variaveis = n_clientes * CUSTO_VARIAVEL_CLIENTE

            # ============ CENÁRIO ANEXO III ============
            # Pró-labore = 28% da receita (mínimo 1 SM)
            pro_labore_iii = max(receita * 0.28, SALARIO_MINIMO)
            fator_r_iii = (pro_labore_iii / receita) * 100

            inss_iii = pro_labore_iii * ALIQUOTA_INSS
            irrf_iii = calcular_irrf(pro_labore_iii - inss_iii)['valor']
            das_iii = receita * ALIQUOTA_DAS_III

            custo_total_iii = custos_fixos_total + custos_variaveis + inss_iii + das_iii + pro_labore_iii
            lucro_iii = receita - custo_total_iii
            liquido_socio_iii = pro_labore_iii - inss_iii - irrf_iii

            # ============ CENÁRIO ANEXO V ============
            # Pró-labore = Salário Mínimo
            pro_labore_v = SALARIO_MINIMO
            fator_r_v = (pro_labore_v / receita) * 100

            inss_v = pro_labore_v * ALIQUOTA_INSS
            irrf_v = calcular_irrf(pro_labore_v - inss_v)['valor']
            das_v = receita * ALIQUOTA_DAS_V

            custo_total_v = custos_fixos_total + custos_variaveis + inss_v + das_v + pro_labore_v
            lucro_v = receita - custo_total_v
            liquido_socio_v = pro_labore_v - inss_v - irrf_v

            # ============ COMPARAÇÃO ============
            diferenca_lucro = lucro_v - lucro_iii
            diferenca_liquido_socio = liquido_socio_iii - liquido_socio_v
            melhor_opcao = "Anexo III" if lucro_iii >= lucro_v else "Anexo V"

            # Identificar ponto de equilíbrio (quando Anexo V passa a ser melhor)
            if ponto_equilibrio is None and lucro_v > lucro_iii:
                ponto_equilibrio = n_clientes
                ponto_equilibrio_lucro = {
                    "clientes": n_clientes,
                    "receita": receita,
                    "lucro_anexo_iii": round(lucro_iii, 2),
                    "lucro_anexo_v": round(lucro_v, 2),
                    "diferenca": round(diferenca_lucro, 2)
                }

            comparativos.append({
                "clientes": n_clientes,
                "receita": round(receita, 2),
                "anexo_iii": {
                    "pro_labore": round(pro_labore_iii, 2),
                    "fator_r": round(fator_r_iii, 1),
                    "inss": round(inss_iii, 2),
                    "irrf": round(irrf_iii, 2),
                    "das": round(das_iii, 2),
                    "custo_total": round(custo_total_iii, 2),
                    "lucro": round(lucro_iii, 2),
                    "liquido_socio": round(liquido_socio_iii, 2)
                },
                "anexo_v": {
                    "pro_labore": round(pro_labore_v, 2),
                    "fator_r": round(fator_r_v, 1),
                    "inss": round(inss_v, 2),
                    "irrf": round(irrf_v, 2),
                    "das": round(das_v, 2),
                    "custo_total": round(custo_total_v, 2),
                    "lucro": round(lucro_v, 2),
                    "liquido_socio": round(liquido_socio_v, 2)
                },
                "comparacao": {
                    "melhor_opcao": melhor_opcao,
                    "diferenca_lucro": round(diferenca_lucro, 2),
                    "economia_pro_labore": round(pro_labore_iii - pro_labore_v, 2),
                    "custo_extra_das": round(das_v - das_iii, 2)
                }
            })

        # Análise final
        # Se nunca encontrou ponto de equilíbrio, Anexo III é sempre melhor
        if ponto_equilibrio is None:
            analise = {
                "conclusao": "Anexo III é sempre mais vantajoso nesta faixa de clientes",
                "recomendacao": "Mantenha o pró-labore em 28% da receita para economizar impostos",
                "ponto_equilibrio": None
            }
        else:
            # Calcular economia anual se usar estratégia correta
            economia_anual = 0
            for c in comparativos:
                if c['clientes'] < ponto_equilibrio:
                    # Antes do equilíbrio, Anexo III é melhor
                    pass
                else:
                    # Após equilíbrio, Anexo V é melhor
                    economia_anual += c['comparacao']['diferenca_lucro']

            analise = {
                "conclusao": f"A partir de {ponto_equilibrio} clientes (R$ {ponto_equilibrio * ticket_medio:,.0f}/mês), o Anexo V se torna mais vantajoso",
                "recomendacao": f"Com menos de {ponto_equilibrio} clientes: use Anexo III (pró-labore 28%). Com {ponto_equilibrio}+ clientes: considere pró-labore mínimo.",
                "ponto_equilibrio": ponto_equilibrio_lucro,
                "observacao": "No Anexo V você paga mais DAS, mas economiza no pró-labore. O lucro líquido da empresa é maior, porém o sócio recebe menos diretamente."
            }

        return {
            "success": True,
            "parametros": {
                "ticket_medio": ticket_medio,
                "custos_fixos": round(custos_fixos_total, 2),
                "custo_variavel_cliente": CUSTO_VARIAVEL_CLIENTE,
                "salario_minimo": SALARIO_MINIMO,
                "aliquota_das_anexo_iii": "6%",
                "aliquota_das_anexo_v": "15,5%"
            },
            "ponto_equilibrio": ponto_equilibrio,
            "analise": analise,
            "comparativos": comparativos,
            "resumo_rapido": [
                {"clientes": c["clientes"], "receita": c["receita"],
                 "lucro_iii": c["anexo_iii"]["lucro"], "lucro_v": c["anexo_v"]["lucro"],
                 "melhor": c["comparacao"]["melhor_opcao"]}
                for c in comparativos if c["clientes"] in [10, 20, 30, 40, 50, 75, 100, 150, 200]
            ]
        }

    except Exception as e:
        logger.error(f"Erro ao simular equilíbrio tributário: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao simular equilíbrio tributário"
        )


@router.get("/alertas/fator-r")
async def verificar_alerta_fator_r(
    current_user: Dict = Depends(get_current_financeiro),
    db: Session = Depends(get_db)
):
    """
    Verifica situação atual do Fator R e emite alertas.

    Retorna status:
    - OK: Fator R >= 28% (Anexo III mantido)
    - ATENÇÃO: Fator R entre 25% e 28% (risco de perder Anexo III)
    - CRÍTICO: Fator R < 25% (tributação desfavorável)
    """
    try:
        SALARIO_MINIMO = 1518.00

        # Calcular MRR atual das assinaturas (excluir demo)
        result_assinaturas = db.execute(
            text("""
                SELECT
                    a.valor_mensal,
                    a.valor_profissional_adicional,
                    a.profissionais_contratados,
                    a.numero_virtual_salvy,
                    a.valor_numero_virtual,
                    p.profissionais_inclusos
                FROM assinaturas a
                JOIN planos p ON p.id = a.plano_id
                WHERE a.status = 'ativa'
                AND a.data_fim IS NULL
                AND a.cliente_id NOT IN (SELECT id FROM clientes WHERE is_demo = true)
            """)
        ).fetchall()

        mrr = Decimal('0')
        for assinatura in result_assinaturas:
            valor_mensal = Decimal(str(assinatura[0] or 0))
            valor_prof_adicional = Decimal(str(assinatura[1] or 50))
            profissionais_contratados = assinatura[2] or 1
            numero_virtual = assinatura[3] or False
            valor_numero_virtual = Decimal(str(assinatura[4] or 40))
            profissionais_inclusos = assinatura[5] or 1

            mrr += valor_mensal
            adicionais = max(0, profissionais_contratados - profissionais_inclusos)
            mrr += adicionais * valor_prof_adicional
            if numero_virtual:
                mrr += valor_numero_virtual

        mrr = float(mrr)

        # Se MRR = 0, não há o que calcular
        if mrr == 0:
            return {
                "success": True,
                "mrr_atual": 0,
                "status": "N/A",
                "nivel": "info",
                "mensagem": "Sem receita recorrente. Aguardando primeiros clientes.",
                "pro_labore_atual": SALARIO_MINIMO,
                "fator_r": 0,
                "pro_labore_ideal": SALARIO_MINIMO,
                "economia_mensal_anexo_iii": 0
            }

        # Buscar pró-labore atual (despesa fixa cadastrada)
        result_pro_labore = db.execute(
            text("""
                SELECT valor FROM despesas
                WHERE (LOWER(descricao) LIKE '%pro-labore%' OR LOWER(descricao) LIKE '%pró-labore%')
                AND categoria = 'fixa'
                AND recorrente = true
                AND status != 'cancelado'
                LIMIT 1
            """)
        ).fetchone()

        # Se não encontrou pró-labore, procurar INSS (que é 11% do pró-labore)
        if not result_pro_labore:
            result_inss = db.execute(
                text("""
                    SELECT valor FROM despesas
                    WHERE LOWER(descricao) LIKE '%inss%'
                    AND categoria = 'fixa'
                    AND recorrente = true
                    AND status != 'cancelado'
                    LIMIT 1
                """)
            ).fetchone()
            if result_inss:
                # INSS = 11% do pró-labore, então pró-labore = INSS / 0.11
                pro_labore_atual = float(result_inss[0]) / 0.11
            else:
                pro_labore_atual = SALARIO_MINIMO
        else:
            pro_labore_atual = float(result_pro_labore[0])

        # Calcular Fator R
        fator_r = (pro_labore_atual / mrr) * 100 if mrr > 0 else 0

        # Calcular pró-labore ideal para Anexo III
        pro_labore_ideal = max(mrr * 0.28, SALARIO_MINIMO)

        # Determinar status
        if fator_r >= 28:
            status_fator = "OK"
            nivel = "success"
            mensagem = f"Fator R em {fator_r:.1f}% - Anexo III mantido"
        elif fator_r >= 25:
            status_fator = "ATENÇÃO"
            nivel = "warning"
            aumento = pro_labore_ideal - pro_labore_atual
            mensagem = f"Fator R em {fator_r:.1f}% - Aumente pró-labore em R$ {aumento:.2f} para garantir Anexo III"
        else:
            status_fator = "CRÍTICO"
            nivel = "error"
            aumento = pro_labore_ideal - pro_labore_atual
            economia = mrr * 0.095  # Diferença entre 15,5% e 6%
            mensagem = f"Fator R em {fator_r:.1f}% - URGENTE: Aumente pró-labore em R$ {aumento:.2f} para economizar R$ {economia:.2f}/mês"

        # Calcular economia do Anexo III vs V
        economia_mensal = mrr * 0.095  # 15,5% - 6% = 9,5%

        return {
            "success": True,
            "mrr_atual": mrr,
            "pro_labore_atual": round(pro_labore_atual, 2),
            "fator_r": round(fator_r, 2),
            "status": status_fator,
            "nivel": nivel,
            "mensagem": mensagem,
            "pro_labore_ideal": round(pro_labore_ideal, 2),
            "economia_mensal_anexo_iii": round(economia_mensal, 2),
            "comparativo": {
                "anexo_iii": {
                    "aliquota": 6.0,
                    "das": round(mrr * 0.06, 2)
                },
                "anexo_v": {
                    "aliquota": 15.5,
                    "das": round(mrr * 0.155, 2)
                },
                "diferenca": round(economia_mensal, 2)
            }
        }

    except Exception as e:
        logger.error(f"Erro ao verificar Fator R: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao verificar alerta de Fator R"
        )


@router.get("/health")
async def health_check():
    """Health check do serviço financeiro"""
    return {
        "status": "ok",
        "service": "financeiro",
        "timestamp": datetime.utcnow().isoformat()
    }
