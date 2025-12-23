"""
API para Gestão de Custos Operacionais
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import logging

from app.database import get_db
from app.services.auditoria_service import get_auditoria_service

router = APIRouter(prefix="/api/interno/custos", tags=["Custos Operacionais"])
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

class CustoCreate(BaseModel):
    data_lancamento: str  # YYYY-MM-DD
    data_vencimento: Optional[str] = None
    categoria: str
    subcategoria: Optional[str] = None
    centro_custo: Optional[str] = None
    descricao: str
    valor: float
    fornecedor: Optional[str] = None
    fornecedor_cnpj: Optional[str] = None
    numero_documento: Optional[str] = None
    comprovante_url: Optional[str] = None
    recorrencia: str = 'unico'  # unico, mensal, bimestral, trimestral, semestral, anual
    total_parcelas: Optional[int] = None


class CustoUpdate(BaseModel):
    data_lancamento: Optional[str] = None
    data_vencimento: Optional[str] = None
    data_pagamento: Optional[str] = None
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    centro_custo: Optional[str] = None
    descricao: Optional[str] = None
    valor: Optional[float] = None
    valor_pago: Optional[float] = None
    fornecedor: Optional[str] = None
    fornecedor_cnpj: Optional[str] = None
    numero_documento: Optional[str] = None
    comprovante_url: Optional[str] = None
    status: Optional[str] = None  # pendente, pago, cancelado, atrasado


class RegistrarPagamento(BaseModel):
    data_pagamento: str  # YYYY-MM-DD
    valor_pago: float


# ==================== CONSTANTES ====================

CATEGORIAS = [
    'infraestrutura',
    'apis',
    'comunicacao',
    'servicos',
    'marketing',
    'pessoal',
    'impostos',
    'outros'
]

RECORRENCIAS = ['unico', 'mensal', 'bimestral', 'trimestral', 'semestral', 'anual']

STATUS_VALIDOS = ['pendente', 'pago', 'cancelado', 'atrasado']


# ==================== ENDPOINTS ====================

@router.get("")
async def listar_custos(
    categoria: Optional[str] = None,
    status: Optional[str] = None,
    fornecedor: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    limite: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Lista custos operacionais com filtros"""
    query = """
        SELECT
            id, data_lancamento, data_vencimento, data_pagamento,
            categoria, subcategoria, centro_custo, descricao,
            valor, valor_pago, fornecedor, status, recorrencia,
            parcela_atual, total_parcelas, criado_em
        FROM custos_operacionais
        WHERE 1=1
    """
    params = {"limite": limite, "offset": offset}

    if categoria:
        query += " AND categoria = :categoria"
        params["categoria"] = categoria

    if status:
        query += " AND status = :status"
        params["status"] = status

    if fornecedor:
        query += " AND fornecedor ILIKE :fornecedor"
        params["fornecedor"] = f"%{fornecedor}%"

    if data_inicio:
        query += " AND data_lancamento >= :data_inicio"
        params["data_inicio"] = data_inicio

    if data_fim:
        query += " AND data_lancamento <= :data_fim"
        params["data_fim"] = data_fim

    query += " ORDER BY data_lancamento DESC LIMIT :limite OFFSET :offset"

    result = db.execute(text(query), params).fetchall()

    return [
        {
            "id": row[0],
            "data_lancamento": row[1].isoformat() if row[1] else None,
            "data_vencimento": row[2].isoformat() if row[2] else None,
            "data_pagamento": row[3].isoformat() if row[3] else None,
            "categoria": row[4],
            "subcategoria": row[5],
            "centro_custo": row[6],
            "descricao": row[7],
            "valor": float(row[8]) if row[8] else 0,
            "valor_pago": float(row[9]) if row[9] else None,
            "fornecedor": row[10],
            "status": row[11],
            "recorrencia": row[12],
            "parcela_atual": row[13],
            "total_parcelas": row[14],
            "criado_em": row[15].isoformat() if row[15] else None
        }
        for row in result
    ]


@router.get("/categorias")
async def listar_categorias():
    """Lista categorias disponíveis"""
    return {"categorias": CATEGORIAS}


@router.get("/resumo")
async def resumo_custos(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Resumo de custos por categoria"""
    from datetime import datetime

    if not mes:
        mes = datetime.now().month
    if not ano:
        ano = datetime.now().year

    # Total por categoria
    result = db.execute(text("""
        SELECT
            categoria,
            COUNT(*) as quantidade,
            SUM(valor) as total_valor,
            SUM(CASE WHEN status = 'pago' THEN valor_pago ELSE 0 END) as total_pago
        FROM custos_operacionais
        WHERE EXTRACT(MONTH FROM data_lancamento) = :mes
        AND EXTRACT(YEAR FROM data_lancamento) = :ano
        AND status != 'cancelado'
        GROUP BY categoria
        ORDER BY total_valor DESC
    """), {"mes": mes, "ano": ano}).fetchall()

    categorias = [
        {
            "categoria": row[0],
            "quantidade": row[1],
            "total_valor": float(row[2]) if row[2] else 0,
            "total_pago": float(row[3]) if row[3] else 0
        }
        for row in result
    ]

    # Totais gerais
    totais = db.execute(text("""
        SELECT
            COUNT(*) as total_lancamentos,
            SUM(valor) as total_valor,
            SUM(CASE WHEN status = 'pago' THEN valor_pago ELSE 0 END) as total_pago,
            SUM(CASE WHEN status = 'pendente' THEN valor ELSE 0 END) as total_pendente,
            SUM(CASE WHEN status = 'atrasado' THEN valor ELSE 0 END) as total_atrasado
        FROM custos_operacionais
        WHERE EXTRACT(MONTH FROM data_lancamento) = :mes
        AND EXTRACT(YEAR FROM data_lancamento) = :ano
        AND status != 'cancelado'
    """), {"mes": mes, "ano": ano}).fetchone()

    return {
        "periodo": f"{mes:02d}/{ano}",
        "totais": {
            "lancamentos": totais[0] or 0,
            "valor_total": float(totais[1]) if totais[1] else 0,
            "valor_pago": float(totais[2]) if totais[2] else 0,
            "valor_pendente": float(totais[3]) if totais[3] else 0,
            "valor_atrasado": float(totais[4]) if totais[4] else 0
        },
        "por_categoria": categorias
    }


@router.get("/{custo_id}")
async def obter_custo(
    custo_id: int,
    db: Session = Depends(get_db)
):
    """Obtém detalhes de um custo"""
    result = db.execute(text("""
        SELECT
            c.id, c.data_lancamento, c.data_vencimento, c.data_pagamento,
            c.categoria, c.subcategoria, c.centro_custo, c.descricao,
            c.valor, c.valor_pago, c.fornecedor, c.fornecedor_cnpj,
            c.numero_documento, c.comprovante_url, c.recorrencia,
            c.parcela_atual, c.total_parcelas, c.lancamento_pai_id,
            c.status, c.criado_por, c.criado_em, c.atualizado_em,
            u.nome as criado_por_nome
        FROM custos_operacionais c
        LEFT JOIN usuarios_internos u ON u.id = c.criado_por
        WHERE c.id = :id
    """), {"id": custo_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Custo não encontrado")

    return {
        "id": result[0],
        "data_lancamento": result[1].isoformat() if result[1] else None,
        "data_vencimento": result[2].isoformat() if result[2] else None,
        "data_pagamento": result[3].isoformat() if result[3] else None,
        "categoria": result[4],
        "subcategoria": result[5],
        "centro_custo": result[6],
        "descricao": result[7],
        "valor": float(result[8]) if result[8] else 0,
        "valor_pago": float(result[9]) if result[9] else None,
        "fornecedor": result[10],
        "fornecedor_cnpj": result[11],
        "numero_documento": result[12],
        "comprovante_url": result[13],
        "recorrencia": result[14],
        "parcela_atual": result[15],
        "total_parcelas": result[16],
        "lancamento_pai_id": result[17],
        "status": result[18],
        "criado_por": result[19],
        "criado_por_nome": result[22],
        "criado_em": result[20].isoformat() if result[20] else None,
        "atualizado_em": result[21].isoformat() if result[21] else None
    }


@router.post("")
async def criar_custo(
    dados: CustoCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Cria um novo lançamento de custo"""
    # Validar categoria
    if dados.categoria not in CATEGORIAS:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria inválida. Valores aceitos: {', '.join(CATEGORIAS)}"
        )

    # Validar recorrência
    if dados.recorrencia not in RECORRENCIAS:
        raise HTTPException(
            status_code=400,
            detail=f"Recorrência inválida. Valores aceitos: {', '.join(RECORRENCIAS)}"
        )

    # Criar custo
    result = db.execute(text("""
        INSERT INTO custos_operacionais (
            data_lancamento, data_vencimento, categoria, subcategoria,
            centro_custo, descricao, valor, fornecedor, fornecedor_cnpj,
            numero_documento, comprovante_url, recorrencia, total_parcelas,
            parcela_atual, status
        ) VALUES (
            :data_lancamento, :data_vencimento, :categoria, :subcategoria,
            :centro_custo, :descricao, :valor, :fornecedor, :fornecedor_cnpj,
            :numero_documento, :comprovante_url, :recorrencia, :total_parcelas,
            1, 'pendente'
        ) RETURNING id
    """), {
        "data_lancamento": dados.data_lancamento,
        "data_vencimento": dados.data_vencimento,
        "categoria": dados.categoria,
        "subcategoria": dados.subcategoria,
        "centro_custo": dados.centro_custo,
        "descricao": dados.descricao,
        "valor": dados.valor,
        "fornecedor": dados.fornecedor,
        "fornecedor_cnpj": dados.fornecedor_cnpj,
        "numero_documento": dados.numero_documento,
        "comprovante_url": dados.comprovante_url,
        "recorrencia": dados.recorrencia,
        "total_parcelas": dados.total_parcelas
    })

    custo_id = result.fetchone()[0]
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='criar',
        recurso='custo_operacional',
        recurso_id=custo_id,
        usuario_tipo='sistema',
        dados_novos={
            "categoria": dados.categoria,
            "descricao": dados.descricao,
            "valor": dados.valor
        },
        ip_address=request.client.host if request.client else None,
        descricao=f"Custo criado: {dados.descricao} - R$ {dados.valor:.2f}"
    )

    logger.info(f"Custo operacional criado: {dados.descricao} - R$ {dados.valor:.2f}")

    return {
        "sucesso": True,
        "mensagem": "Custo criado com sucesso",
        "id": custo_id
    }


@router.put("/{custo_id}")
async def atualizar_custo(
    custo_id: int,
    dados: CustoUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Atualiza um custo"""
    # Verificar se existe
    custo_atual = db.execute(text("""
        SELECT id, descricao, valor, status FROM custos_operacionais WHERE id = :id
    """), {"id": custo_id}).fetchone()

    if not custo_atual:
        raise HTTPException(status_code=404, detail="Custo não encontrado")

    # Validar status se fornecido
    if dados.status and dados.status not in STATUS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Status inválido. Valores aceitos: {', '.join(STATUS_VALIDOS)}"
        )

    # Validar categoria se fornecida
    if dados.categoria and dados.categoria not in CATEGORIAS:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria inválida. Valores aceitos: {', '.join(CATEGORIAS)}"
        )

    # Montar update dinâmico
    updates = []
    params = {"id": custo_id}

    campos = [
        'data_lancamento', 'data_vencimento', 'data_pagamento',
        'categoria', 'subcategoria', 'centro_custo', 'descricao',
        'valor', 'valor_pago', 'fornecedor', 'fornecedor_cnpj',
        'numero_documento', 'comprovante_url', 'status'
    ]

    for campo in campos:
        valor = getattr(dados, campo, None)
        if valor is not None:
            updates.append(f"{campo} = :{campo}")
            params[campo] = valor

    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    updates.append("atualizado_em = NOW()")

    query = f"UPDATE custos_operacionais SET {', '.join(updates)} WHERE id = :id"
    db.execute(text(query), params)
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='atualizar',
        recurso='custo_operacional',
        recurso_id=custo_id,
        usuario_tipo='sistema',
        dados_anteriores={"descricao": custo_atual[1], "valor": float(custo_atual[2])},
        dados_novos=dados.dict(exclude_none=True),
        ip_address=request.client.host if request.client else None,
        descricao=f"Custo atualizado: ID={custo_id}"
    )

    logger.info(f"Custo operacional atualizado: ID={custo_id}")

    return {"sucesso": True, "mensagem": "Custo atualizado com sucesso"}


@router.post("/{custo_id}/pagar")
async def registrar_pagamento(
    custo_id: int,
    dados: RegistrarPagamento,
    request: Request,
    db: Session = Depends(get_db)
):
    """Registra pagamento de um custo"""
    custo = db.execute(text("""
        SELECT id, descricao, valor, status FROM custos_operacionais WHERE id = :id
    """), {"id": custo_id}).fetchone()

    if not custo:
        raise HTTPException(status_code=404, detail="Custo não encontrado")

    if custo[3] == 'pago':
        raise HTTPException(status_code=400, detail="Custo já foi pago")

    if custo[3] == 'cancelado':
        raise HTTPException(status_code=400, detail="Custo foi cancelado")

    db.execute(text("""
        UPDATE custos_operacionais
        SET data_pagamento = :data_pagamento, valor_pago = :valor_pago,
            status = 'pago', atualizado_em = NOW()
        WHERE id = :id
    """), {
        "id": custo_id,
        "data_pagamento": dados.data_pagamento,
        "valor_pago": dados.valor_pago
    })
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='atualizar',
        recurso='custo_operacional',
        recurso_id=custo_id,
        usuario_tipo='sistema',
        dados_novos={"status": "pago", "valor_pago": dados.valor_pago},
        ip_address=request.client.host if request.client else None,
        descricao=f"Pagamento registrado: {custo[1]} - R$ {dados.valor_pago:.2f}"
    )

    logger.info(f"Pagamento registrado: {custo[1]} - R$ {dados.valor_pago:.2f}")

    return {"sucesso": True, "mensagem": "Pagamento registrado com sucesso"}


@router.delete("/{custo_id}")
async def cancelar_custo(
    custo_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Cancela um custo (soft delete)"""
    custo = db.execute(text("""
        SELECT id, descricao, status FROM custos_operacionais WHERE id = :id
    """), {"id": custo_id}).fetchone()

    if not custo:
        raise HTTPException(status_code=404, detail="Custo não encontrado")

    if custo[2] == 'pago':
        raise HTTPException(status_code=400, detail="Não é possível cancelar um custo já pago")

    db.execute(text("""
        UPDATE custos_operacionais SET status = 'cancelado', atualizado_em = NOW() WHERE id = :id
    """), {"id": custo_id})
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='deletar',
        recurso='custo_operacional',
        recurso_id=custo_id,
        usuario_tipo='sistema',
        ip_address=request.client.host if request.client else None,
        descricao=f"Custo cancelado: {custo[1]}"
    )

    logger.info(f"Custo operacional cancelado: {custo[1]}")

    return {"sucesso": True, "mensagem": "Custo cancelado com sucesso"}
