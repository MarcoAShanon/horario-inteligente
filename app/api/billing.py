"""
API de Billing (ASAAS)
Endpoints para gerenciamento de cobranças e assinaturas via ASAAS
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.services.asaas_service import AsaasService
from app.api.auth import get_current_user
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
import logging

router = APIRouter(prefix="/api/billing", tags=["Billing ASAAS"])
logger = logging.getLogger(__name__)


# ============ SCHEMAS ============

class ClienteAsaasCreate(BaseModel):
    cliente_id: int  # ID do cliente no sistema interno
    nome: Optional[str] = None  # Se não informado, busca do banco
    email: Optional[str] = None
    cpf_cnpj: str
    telefone: Optional[str] = None


class ClienteAsaasResponse(BaseModel):
    cliente_id: int
    asaas_customer_id: str
    nome: str
    email: str


class CobrancaCreate(BaseModel):
    cliente_id: int
    valor: float
    descricao: str
    data_vencimento: date
    forma_pagamento: str = "UNDEFINED"  # BOLETO, PIX, CREDIT_CARD, UNDEFINED
    tipo: str = "AVULSO"  # ASSINATURA, ATIVACAO, AVULSO
    assinatura_id: Optional[int] = None


class CobrancaResponse(BaseModel):
    id: int
    asaas_payment_id: str
    valor: float
    status: str
    data_vencimento: date
    link_boleto: Optional[str]
    link_pix: Optional[str]
    pix_copia_cola: Optional[str]


class AssinaturaAsaasCreate(BaseModel):
    cliente_id: int
    assinatura_id: int  # ID da assinatura no sistema interno
    valor: float
    ciclo: str = "MONTHLY"  # MONTHLY, QUARTERLY, SEMIANNUALLY, YEARLY
    descricao: str
    forma_pagamento: str = "UNDEFINED"
    data_inicio: Optional[date] = None


class AssinaturaAsaasResponse(BaseModel):
    assinatura_id: int
    asaas_subscription_id: str
    valor: float
    ciclo: str
    status: str


# ============ CLIENTES ASAAS ============

@router.post("/customers", response_model=ClienteAsaasResponse)
async def criar_cliente_asaas(dados: ClienteAsaasCreate, db: Session = Depends(get_db)):
    """
    Cria um cliente no ASAAS e vincula ao cliente do sistema.
    Se o cliente já tiver asaas_customer_id, retorna os dados existentes.
    """
    # Buscar cliente no banco
    result = db.execute(
        text("SELECT id, nome, email, telefone, asaas_customer_id FROM clientes WHERE id = :id"),
        {"id": dados.cliente_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    cliente_id, nome, email, telefone, asaas_customer_id = result

    # Se já tem ID ASAAS, retorna
    if asaas_customer_id:
        return ClienteAsaasResponse(
            cliente_id=cliente_id,
            asaas_customer_id=asaas_customer_id,
            nome=nome,
            email=email
        )

    # Criar cliente no ASAAS
    asaas = AsaasService()
    response = await asaas.criar_cliente(
        nome=dados.nome or nome,
        email=dados.email or email,
        cpf_cnpj=dados.cpf_cnpj,
        telefone=dados.telefone or telefone
    )

    if not response["success"]:
        logger.error(f"Erro ao criar cliente ASAAS: {response.get('error')}")
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao criar cliente no ASAAS: {response.get('error')}"
        )

    # Salvar ID ASAAS no banco
    asaas_id = response["data"]["id"]
    db.execute(
        text("UPDATE clientes SET asaas_customer_id = :asaas_id WHERE id = :id"),
        {"asaas_id": asaas_id, "id": cliente_id}
    )
    db.commit()

    logger.info(f"Cliente ASAAS criado: {asaas_id} para cliente interno {cliente_id}")

    return ClienteAsaasResponse(
        cliente_id=cliente_id,
        asaas_customer_id=asaas_id,
        nome=dados.nome or nome,
        email=dados.email or email
    )


@router.get("/customers/{cliente_id}", response_model=ClienteAsaasResponse)
async def buscar_cliente_asaas(cliente_id: int, db: Session = Depends(get_db)):
    """
    Busca dados do cliente no ASAAS.
    """
    result = db.execute(
        text("SELECT id, nome, email, asaas_customer_id FROM clientes WHERE id = :id"),
        {"id": cliente_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    cliente_id, nome, email, asaas_customer_id = result

    if not asaas_customer_id:
        raise HTTPException(status_code=404, detail="Cliente não possui cadastro no ASAAS")

    return ClienteAsaasResponse(
        cliente_id=cliente_id,
        asaas_customer_id=asaas_customer_id,
        nome=nome,
        email=email
    )


# ============ COBRANÇAS ============

@router.post("/charges", response_model=CobrancaResponse)
async def criar_cobranca(dados: CobrancaCreate, db: Session = Depends(get_db)):
    """
    Cria uma nova cobrança no ASAAS.
    """
    # Buscar asaas_customer_id do cliente
    result = db.execute(
        text("SELECT asaas_customer_id FROM clientes WHERE id = :id"),
        {"id": dados.cliente_id}
    ).fetchone()

    if not result or not result[0]:
        raise HTTPException(
            status_code=400,
            detail="Cliente não possui cadastro no ASAAS. Crie o cliente primeiro."
        )

    asaas_customer_id = result[0]

    # Criar cobrança no ASAAS
    asaas = AsaasService()
    response = await asaas.criar_cobranca(
        customer_id=asaas_customer_id,
        valor=dados.valor,
        vencimento=dados.data_vencimento,
        descricao=dados.descricao,
        forma_pagamento=dados.forma_pagamento
    )

    if not response["success"]:
        logger.error(f"Erro ao criar cobranca ASAAS: {response.get('error')}")
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao criar cobrança no ASAAS: {response.get('error')}"
        )

    payment_data = response["data"]

    # Buscar links de pagamento (PIX se disponível)
    link_pix = None
    pix_copia_cola = None

    if dados.forma_pagamento in ["PIX", "UNDEFINED"]:
        pix_response = await asaas.obter_qrcode_pix(payment_data["id"])
        if pix_response["success"]:
            pix_copia_cola = pix_response["data"].get("payload")

    # Salvar pagamento no banco
    db.execute(
        text("""
            INSERT INTO pagamentos (
                cliente_id, assinatura_id, asaas_payment_id, asaas_invoice_url,
                valor, data_vencimento, forma_pagamento, status, descricao, tipo,
                link_boleto, link_pix, pix_copia_cola
            ) VALUES (
                :cliente_id, :assinatura_id, :asaas_payment_id, :invoice_url,
                :valor, :data_vencimento, :forma_pagamento, :status, :descricao, :tipo,
                :link_boleto, :link_pix, :pix_copia_cola
            )
            RETURNING id
        """),
        {
            "cliente_id": dados.cliente_id,
            "assinatura_id": dados.assinatura_id,
            "asaas_payment_id": payment_data["id"],
            "invoice_url": payment_data.get("invoiceUrl"),
            "valor": dados.valor,
            "data_vencimento": dados.data_vencimento,
            "forma_pagamento": dados.forma_pagamento,
            "status": payment_data.get("status", "PENDING"),
            "descricao": dados.descricao,
            "tipo": dados.tipo,
            "link_boleto": payment_data.get("bankSlipUrl"),
            "link_pix": payment_data.get("invoiceUrl"),
            "pix_copia_cola": pix_copia_cola
        }
    )
    result = db.execute(text("SELECT lastval()")).fetchone()
    pagamento_id = result[0]
    db.commit()

    logger.info(f"Cobranca criada: {payment_data['id']} - R$ {dados.valor}")

    return CobrancaResponse(
        id=pagamento_id,
        asaas_payment_id=payment_data["id"],
        valor=dados.valor,
        status=payment_data.get("status", "PENDING"),
        data_vencimento=dados.data_vencimento,
        link_boleto=payment_data.get("bankSlipUrl"),
        link_pix=payment_data.get("invoiceUrl"),
        pix_copia_cola=pix_copia_cola
    )


@router.get("/charges/summary")
async def resumo_cobrancas(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna resumo de cobranças por status.
    Útil para dashboard financeiro.
    """
    query = """
        SELECT
            status,
            COUNT(*) as quantidade,
            COALESCE(SUM(valor), 0) as valor_total
        FROM pagamentos
        WHERE 1=1
    """
    params = {}

    if start_date:
        query += " AND data_vencimento >= :start_date"
        params["start_date"] = start_date

    if end_date:
        query += " AND data_vencimento <= :end_date"
        params["end_date"] = end_date

    query += " GROUP BY status"

    result = db.execute(text(query), params).fetchall()

    summary = {
        "PENDING": {"quantidade": 0, "valor_total": 0},
        "CONFIRMED": {"quantidade": 0, "valor_total": 0},
        "RECEIVED": {"quantidade": 0, "valor_total": 0},
        "OVERDUE": {"quantidade": 0, "valor_total": 0},
        "REFUNDED": {"quantidade": 0, "valor_total": 0},
        "DELETED": {"quantidade": 0, "valor_total": 0}
    }

    for r in result:
        status = r[0] or "UNKNOWN"
        if status in summary:
            summary[status] = {
                "quantidade": r[1],
                "valor_total": float(r[2])
            }

    # Calcular totais
    total_pendente = summary["PENDING"]["valor_total"] + summary.get("OVERDUE", {}).get("valor_total", 0)
    total_recebido = summary["CONFIRMED"]["valor_total"] + summary["RECEIVED"]["valor_total"]

    return {
        "por_status": summary,
        "total_pendente": total_pendente,
        "total_recebido": total_recebido,
        "total_geral": sum(s["valor_total"] for s in summary.values())
    }


@router.get("/charges/{pagamento_id}", response_model=CobrancaResponse)
async def buscar_cobranca(pagamento_id: int, db: Session = Depends(get_db)):
    """
    Busca uma cobrança pelo ID interno.
    """
    result = db.execute(
        text("""
            SELECT id, asaas_payment_id, valor, status, data_vencimento,
                   link_boleto, link_pix, pix_copia_cola
            FROM pagamentos WHERE id = :id
        """),
        {"id": pagamento_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    return CobrancaResponse(
        id=result[0],
        asaas_payment_id=result[1],
        valor=float(result[2]),
        status=result[3],
        data_vencimento=result[4],
        link_boleto=result[5],
        link_pix=result[6],
        pix_copia_cola=result[7]
    )


@router.get("/charges/cliente/{cliente_id}")
async def listar_cobrancas_cliente(
    cliente_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista cobranças de um cliente.
    """
    query = """
        SELECT id, asaas_payment_id, valor, status, data_vencimento,
               link_boleto, link_pix, pix_copia_cola, tipo, descricao
        FROM pagamentos
        WHERE cliente_id = :cliente_id
    """
    params = {"cliente_id": cliente_id}

    if status:
        query += " AND status = :status"
        params["status"] = status

    query += " ORDER BY data_vencimento DESC"

    result = db.execute(text(query), params).fetchall()

    return [
        {
            "id": r[0],
            "asaas_payment_id": r[1],
            "valor": float(r[2]),
            "status": r[3],
            "data_vencimento": str(r[4]),
            "link_boleto": r[5],
            "link_pix": r[6],
            "pix_copia_cola": r[7],
            "tipo": r[8],
            "descricao": r[9]
        }
        for r in result
    ]


# ============ LISTAGEM DE COBRANÇAS (ADMIN) ============

class CobrancaListItem(BaseModel):
    id: int
    asaas_payment_id: str
    cliente_id: int
    cliente_nome: str
    valor: float
    status: str
    vencimento: str
    data_pagamento: Optional[str]
    invoice_url: Optional[str]
    tipo: Optional[str]
    descricao: Optional[str]


class CobrancaListResponse(BaseModel):
    items: List[CobrancaListItem]
    total: int
    page: int
    per_page: int


# ============ SCHEMAS ÁREA DO CLIENTE ============

class FaturaItem(BaseModel):
    id: int
    asaas_payment_id: str
    valor: float
    status: str
    vencimento: str
    data_pagamento: Optional[str]
    invoice_url: Optional[str]
    tipo: Optional[str]
    descricao: Optional[str]


class AssinaturaInfo(BaseModel):
    id: int
    plano: str
    valor_mensal: float
    status: str
    data_inicio: Optional[str]
    proxima_cobranca: Optional[str]
    asaas_subscription_id: Optional[str]


class MinhaAssinaturaResponse(BaseModel):
    cliente: dict
    assinatura: Optional[AssinaturaInfo]
    faturas: List[FaturaItem]
    resumo: dict


# ============ ÁREA DO CLIENTE ============

@router.get("/minha-assinatura", response_model=MinhaAssinaturaResponse)
async def minha_assinatura(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna informações da assinatura e faturas do cliente logado.
    Baseado no cliente_id do token JWT.
    """
    cliente_id = current_user.get("cliente_id")

    if not cliente_id:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a um cliente"
        )

    # Buscar dados do cliente
    cliente_result = db.execute(
        text("""
            SELECT id, nome, email, plano, asaas_customer_id, ativo
            FROM clientes WHERE id = :id
        """),
        {"id": cliente_id}
    ).fetchone()

    if not cliente_result:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    cliente_info = {
        "id": cliente_result[0],
        "nome": cliente_result[1],
        "email": cliente_result[2],
        "plano": cliente_result[3],
        "asaas_customer_id": cliente_result[4],
        "ativo": cliente_result[5]
    }

    # Buscar assinatura ativa
    assinatura_result = db.execute(
        text("""
            SELECT a.id, COALESCE(p.nome, 'Plano não definido') as plano_nome,
                   a.valor_mensal, a.status, a.data_inicio,
                   a.asaas_subscription_id
            FROM assinaturas a
            LEFT JOIN planos p ON p.id = a.plano_id
            WHERE a.cliente_id = :cliente_id AND a.status = 'ativa'
            ORDER BY a.criado_em DESC
            LIMIT 1
        """),
        {"cliente_id": cliente_id}
    ).fetchone()

    assinatura_info = None
    if assinatura_result:
        assinatura_info = AssinaturaInfo(
            id=assinatura_result[0],
            plano=assinatura_result[1] or "Não definido",
            valor_mensal=float(assinatura_result[2]) if assinatura_result[2] else 0,
            status=assinatura_result[3] or "ativa",
            data_inicio=str(assinatura_result[4]) if assinatura_result[4] else None,
            proxima_cobranca=None,  # Campo não existe na tabela
            asaas_subscription_id=assinatura_result[5]
        )

    # Buscar faturas do cliente (últimas 12)
    faturas_result = db.execute(
        text("""
            SELECT id, asaas_payment_id, valor, status, data_vencimento,
                   data_pagamento, asaas_invoice_url, tipo, descricao
            FROM pagamentos
            WHERE cliente_id = :cliente_id
            ORDER BY data_vencimento DESC
            LIMIT 12
        """),
        {"cliente_id": cliente_id}
    ).fetchall()

    faturas = [
        FaturaItem(
            id=f[0],
            asaas_payment_id=f[1] or "",
            valor=float(f[2]) if f[2] else 0,
            status=f[3] or "UNKNOWN",
            vencimento=str(f[4]) if f[4] else "",
            data_pagamento=str(f[5]) if f[5] else None,
            invoice_url=f[6],
            tipo=f[7],
            descricao=f[8]
        )
        for f in faturas_result
    ]

    # Calcular resumo
    total_pendente = sum(f.valor for f in faturas if f.status in ["PENDING", "OVERDUE"])
    total_pago = sum(f.valor for f in faturas if f.status in ["CONFIRMED", "RECEIVED"])

    resumo = {
        "total_faturas": len(faturas),
        "pendentes": len([f for f in faturas if f.status in ["PENDING", "OVERDUE"]]),
        "pagas": len([f for f in faturas if f.status in ["CONFIRMED", "RECEIVED"]]),
        "valor_pendente": total_pendente,
        "valor_pago": total_pago
    }

    return MinhaAssinaturaResponse(
        cliente=cliente_info,
        assinatura=assinatura_info,
        faturas=faturas,
        resumo=resumo
    )


@router.get("/minhas-faturas")
async def minhas_faturas(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todas as faturas do cliente logado.
    Opcionalmente filtra por status.
    """
    cliente_id = current_user.get("cliente_id")

    if not cliente_id:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a um cliente"
        )

    query = """
        SELECT id, asaas_payment_id, valor, status, data_vencimento,
               data_pagamento, asaas_invoice_url, tipo, descricao
        FROM pagamentos
        WHERE cliente_id = :cliente_id
    """
    params = {"cliente_id": cliente_id}

    if status:
        query += " AND status = :status"
        params["status"] = status

    query += " ORDER BY data_vencimento DESC"

    result = db.execute(text(query), params).fetchall()

    return [
        {
            "id": r[0],
            "asaas_payment_id": r[1],
            "valor": float(r[2]) if r[2] else 0,
            "status": r[3],
            "vencimento": str(r[4]) if r[4] else None,
            "data_pagamento": str(r[5]) if r[5] else None,
            "invoice_url": r[6],
            "tipo": r[7],
            "descricao": r[8]
        }
        for r in result
    ]


@router.get("/charges", response_model=CobrancaListResponse)
async def listar_cobrancas(
    status: Optional[str] = None,
    cliente_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    tipo: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db)
):
    """
    Lista todas as cobranças com filtros opcionais.

    Parâmetros:
    - status: PENDING, CONFIRMED, RECEIVED, OVERDUE, REFUNDED, DELETED
    - cliente_id: Filtrar por cliente específico
    - start_date/end_date: Período de vencimento
    - tipo: ASSINATURA, ATIVACAO, AVULSO
    - page/per_page: Paginação
    """
    # Construir query base
    query = """
        SELECT p.id, p.asaas_payment_id, p.cliente_id, c.nome as cliente_nome,
               p.valor, p.status, p.data_vencimento, p.data_pagamento,
               p.asaas_invoice_url, p.tipo, p.descricao
        FROM pagamentos p
        LEFT JOIN clientes c ON c.id = p.cliente_id
        WHERE 1=1
    """
    count_query = """
        SELECT COUNT(*) FROM pagamentos p WHERE 1=1
    """
    params = {}

    # Aplicar filtros
    if status:
        query += " AND p.status = :status"
        count_query += " AND p.status = :status"
        params["status"] = status

    if cliente_id:
        query += " AND p.cliente_id = :cliente_id"
        count_query += " AND p.cliente_id = :cliente_id"
        params["cliente_id"] = cliente_id

    if start_date:
        query += " AND p.data_vencimento >= :start_date"
        count_query += " AND p.data_vencimento >= :start_date"
        params["start_date"] = start_date

    if end_date:
        query += " AND p.data_vencimento <= :end_date"
        count_query += " AND p.data_vencimento <= :end_date"
        params["end_date"] = end_date

    if tipo:
        query += " AND p.tipo = :tipo"
        count_query += " AND p.tipo = :tipo"
        params["tipo"] = tipo

    # Ordenação e paginação
    query += " ORDER BY p.data_vencimento DESC, p.id DESC"
    query += " LIMIT :limit OFFSET :offset"
    params["limit"] = per_page
    params["offset"] = (page - 1) * per_page

    # Executar queries
    result = db.execute(text(query), params).fetchall()
    total = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]}).scalar()

    items = [
        CobrancaListItem(
            id=r[0],
            asaas_payment_id=r[1] or "",
            cliente_id=r[2],
            cliente_nome=r[3] or "Cliente não identificado",
            valor=float(r[4]) if r[4] else 0,
            status=r[5] or "UNKNOWN",
            vencimento=str(r[6]) if r[6] else "",
            data_pagamento=str(r[7]) if r[7] else None,
            invoice_url=r[8],
            tipo=r[9],
            descricao=r[10]
        )
        for r in result
    ]

    return CobrancaListResponse(
        items=items,
        total=total or 0,
        page=page,
        per_page=per_page
    )


@router.delete("/charges/{pagamento_id}")
async def cancelar_cobranca(pagamento_id: int, db: Session = Depends(get_db)):
    """
    Cancela uma cobrança no ASAAS.
    """
    result = db.execute(
        text("SELECT asaas_payment_id FROM pagamentos WHERE id = :id"),
        {"id": pagamento_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    asaas_payment_id = result[0]

    asaas = AsaasService()
    response = await asaas.cancelar_cobranca(asaas_payment_id)

    if not response["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao cancelar cobrança: {response.get('error')}"
        )

    # Atualizar status no banco
    db.execute(
        text("UPDATE pagamentos SET status = 'DELETED' WHERE id = :id"),
        {"id": pagamento_id}
    )
    db.commit()

    return {"success": True, "message": "Cobrança cancelada com sucesso"}


# ============ ASSINATURAS ============

@router.post("/subscriptions", response_model=AssinaturaAsaasResponse)
async def criar_assinatura_asaas(dados: AssinaturaAsaasCreate, db: Session = Depends(get_db)):
    """
    Cria uma assinatura no ASAAS e vincula à assinatura do sistema.
    """
    # Buscar asaas_customer_id do cliente
    result = db.execute(
        text("SELECT asaas_customer_id FROM clientes WHERE id = :id"),
        {"id": dados.cliente_id}
    ).fetchone()

    if not result or not result[0]:
        raise HTTPException(
            status_code=400,
            detail="Cliente não possui cadastro no ASAAS. Crie o cliente primeiro."
        )

    asaas_customer_id = result[0]

    # Verificar se assinatura existe
    assinatura = db.execute(
        text("SELECT id, asaas_subscription_id FROM assinaturas WHERE id = :id"),
        {"id": dados.assinatura_id}
    ).fetchone()

    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    if assinatura[1]:
        raise HTTPException(
            status_code=400,
            detail="Assinatura já possui vínculo com ASAAS"
        )

    # Criar assinatura no ASAAS
    asaas = AsaasService()
    response = await asaas.criar_assinatura(
        customer_id=asaas_customer_id,
        valor=dados.valor,
        ciclo=dados.ciclo,
        descricao=dados.descricao,
        forma_pagamento=dados.forma_pagamento,
        data_proxima_cobranca=dados.data_inicio
    )

    if not response["success"]:
        logger.error(f"Erro ao criar assinatura ASAAS: {response.get('error')}")
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao criar assinatura no ASAAS: {response.get('error')}"
        )

    subscription_data = response["data"]

    # Atualizar assinatura no banco com ID ASAAS
    db.execute(
        text("UPDATE assinaturas SET asaas_subscription_id = :asaas_id WHERE id = :id"),
        {"asaas_id": subscription_data["id"], "id": dados.assinatura_id}
    )
    db.commit()

    logger.info(f"Assinatura ASAAS criada: {subscription_data['id']}")

    return AssinaturaAsaasResponse(
        assinatura_id=dados.assinatura_id,
        asaas_subscription_id=subscription_data["id"],
        valor=dados.valor,
        ciclo=dados.ciclo,
        status=subscription_data.get("status", "ACTIVE")
    )


@router.get("/subscriptions/{assinatura_id}", response_model=AssinaturaAsaasResponse)
async def buscar_assinatura_asaas(assinatura_id: int, db: Session = Depends(get_db)):
    """
    Busca dados da assinatura no ASAAS.
    """
    result = db.execute(
        text("""
            SELECT a.id, a.asaas_subscription_id, a.valor_mensal, a.status
            FROM assinaturas a
            WHERE a.id = :id
        """),
        {"id": assinatura_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    if not result[1]:
        raise HTTPException(status_code=404, detail="Assinatura não possui vínculo com ASAAS")

    # Buscar dados atualizados no ASAAS
    asaas = AsaasService()
    response = await asaas.buscar_assinatura(result[1])

    if not response["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao buscar assinatura no ASAAS: {response.get('error')}"
        )

    subscription_data = response["data"]

    return AssinaturaAsaasResponse(
        assinatura_id=result[0],
        asaas_subscription_id=result[1],
        valor=float(subscription_data.get("value", result[2])),
        ciclo=subscription_data.get("cycle", "MONTHLY"),
        status=subscription_data.get("status", result[3])
    )


@router.delete("/subscriptions/{assinatura_id}")
async def cancelar_assinatura_asaas(assinatura_id: int, db: Session = Depends(get_db)):
    """
    Cancela uma assinatura no ASAAS.
    """
    result = db.execute(
        text("SELECT asaas_subscription_id FROM assinaturas WHERE id = :id"),
        {"id": assinatura_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    if not result[0]:
        raise HTTPException(status_code=404, detail="Assinatura não possui vínculo com ASAAS")

    asaas_subscription_id = result[0]

    asaas = AsaasService()
    response = await asaas.cancelar_assinatura(asaas_subscription_id)

    if not response["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao cancelar assinatura: {response.get('error')}"
        )

    # Atualizar status no banco
    db.execute(
        text("UPDATE assinaturas SET status = 'cancelada' WHERE id = :id"),
        {"id": assinatura_id}
    )
    db.commit()

    return {"success": True, "message": "Assinatura cancelada com sucesso"}


@router.put("/subscriptions/{assinatura_id}")
async def atualizar_assinatura_asaas(
    assinatura_id: int,
    valor: Optional[float] = None,
    ciclo: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Atualiza uma assinatura no ASAAS.
    """
    result = db.execute(
        text("SELECT asaas_subscription_id FROM assinaturas WHERE id = :id"),
        {"id": assinatura_id}
    ).fetchone()

    if not result or not result[0]:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada ou sem vínculo ASAAS")

    asaas_subscription_id = result[0]

    dados_atualizacao = {}
    if valor is not None:
        dados_atualizacao["value"] = valor
    if ciclo is not None:
        dados_atualizacao["cycle"] = ciclo

    if not dados_atualizacao:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    asaas = AsaasService()
    response = await asaas.atualizar_assinatura(asaas_subscription_id, dados_atualizacao)

    if not response["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao atualizar assinatura: {response.get('error')}"
        )

    # Atualizar valor no banco local se alterado
    if valor is not None:
        db.execute(
            text("UPDATE assinaturas SET valor_mensal = :valor WHERE id = :id"),
            {"valor": valor, "id": assinatura_id}
        )
        db.commit()

    return {"success": True, "message": "Assinatura atualizada com sucesso"}


# ============ TAXA DE ATIVAÇÃO ============

@router.post("/activation-fee/{cliente_id}")
async def criar_cobranca_ativacao(
    cliente_id: int,
    desconto_percentual: float = 0,
    forma_pagamento: str = "PIX",
    db: Session = Depends(get_db)
):
    """
    Cria cobrança de taxa de ativação para um cliente.
    """
    # Buscar assinatura e taxa de ativação
    result = db.execute(
        text("""
            SELECT a.id, a.taxa_ativacao, a.taxa_ativacao_paga, c.asaas_customer_id
            FROM assinaturas a
            JOIN clientes c ON c.id = a.cliente_id
            WHERE a.cliente_id = :cliente_id AND a.status = 'ativa'
            ORDER BY a.criado_em DESC
            LIMIT 1
        """),
        {"cliente_id": cliente_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Assinatura ativa não encontrada")

    assinatura_id, taxa_ativacao, taxa_paga, asaas_customer_id = result

    if taxa_paga:
        raise HTTPException(status_code=400, detail="Taxa de ativação já foi paga")

    if not asaas_customer_id:
        raise HTTPException(status_code=400, detail="Cliente não possui cadastro no ASAAS")

    # Calcular valor com desconto
    taxa_final = float(taxa_ativacao) * (1 - desconto_percentual / 100)

    # Criar cobrança
    asaas = AsaasService()
    response = await asaas.criar_cobranca(
        customer_id=asaas_customer_id,
        valor=taxa_final,
        vencimento=date.today(),
        descricao="Taxa de Ativação - Horário Inteligente",
        forma_pagamento=forma_pagamento
    )

    if not response["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao criar cobrança: {response.get('error')}"
        )

    payment_data = response["data"]

    # Buscar PIX se disponível
    pix_copia_cola = None
    if forma_pagamento in ["PIX", "UNDEFINED"]:
        pix_response = await asaas.obter_qrcode_pix(payment_data["id"])
        if pix_response["success"]:
            pix_copia_cola = pix_response["data"].get("payload")

    # Salvar no banco
    db.execute(
        text("""
            INSERT INTO pagamentos (
                cliente_id, assinatura_id, asaas_payment_id, asaas_invoice_url,
                valor, data_vencimento, forma_pagamento, status, descricao, tipo,
                link_boleto, pix_copia_cola
            ) VALUES (
                :cliente_id, :assinatura_id, :asaas_payment_id, :invoice_url,
                :valor, :data_vencimento, :forma_pagamento, :status, :descricao, 'ATIVACAO',
                :link_boleto, :pix_copia_cola
            )
        """),
        {
            "cliente_id": cliente_id,
            "assinatura_id": assinatura_id,
            "asaas_payment_id": payment_data["id"],
            "invoice_url": payment_data.get("invoiceUrl"),
            "valor": taxa_final,
            "data_vencimento": date.today(),
            "forma_pagamento": forma_pagamento,
            "status": payment_data.get("status", "PENDING"),
            "descricao": "Taxa de Ativação - Horário Inteligente",
            "link_boleto": payment_data.get("bankSlipUrl"),
            "pix_copia_cola": pix_copia_cola
        }
    )
    db.commit()

    return {
        "success": True,
        "asaas_payment_id": payment_data["id"],
        "valor": taxa_final,
        "invoice_url": payment_data.get("invoiceUrl"),
        "pix_copia_cola": pix_copia_cola,
        "bank_slip_url": payment_data.get("bankSlipUrl")
    }


# ============ ENDPOINTS PARA INADIMPLENTES ============

@router.get("/faturas-pendentes/{cliente_id}")
async def obter_faturas_pendentes(
    cliente_id: int,
    db: Session = Depends(get_db)
):
    """
    Retorna faturas pendentes (PENDING ou OVERDUE) de um cliente.
    Usado pela página de conta suspensa para exibir informações de pagamento.

    Este endpoint é liberado mesmo para clientes inadimplentes.
    """
    try:
        # Buscar faturas pendentes ou vencidas
        result = db.execute(
            text("""
                SELECT
                    p.id,
                    p.asaas_payment_id,
                    p.valor,
                    p.data_vencimento,
                    p.status,
                    p.descricao,
                    p.asaas_invoice_url,
                    p.link_boleto,
                    p.pix_copia_cola,
                    c.nome as cliente_nome
                FROM pagamentos p
                JOIN clientes c ON c.id = p.cliente_id
                WHERE p.cliente_id = :cliente_id
                AND p.status IN ('PENDING', 'OVERDUE')
                ORDER BY p.data_vencimento ASC
            """),
            {"cliente_id": cliente_id}
        ).fetchall()

        faturas = []
        for row in result:
            faturas.append({
                "id": row[0],
                "asaas_payment_id": row[1],
                "valor": float(row[2]) if row[2] else 0,
                "vencimento": str(row[3]) if row[3] else None,
                "status": row[4],
                "descricao": row[5] or "Mensalidade",
                "invoice_url": row[6],
                "link_boleto": row[7],
                "pix_copia_cola": row[8],
                "cliente_nome": row[9]
            })

        # Calcular total pendente
        total_pendente = sum(f["valor"] for f in faturas)

        return {
            "cliente_id": cliente_id,
            "faturas": faturas,
            "total_faturas": len(faturas),
            "total_pendente": total_pendente
        }

    except Exception as e:
        logger.error(f"Erro ao buscar faturas pendentes: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar faturas: {str(e)}"
        )


@router.get("/link-pagamento/{cliente_id}")
async def obter_link_pagamento(
    cliente_id: int,
    db: Session = Depends(get_db)
):
    """
    Retorna o link de pagamento da fatura mais antiga pendente.
    Usado para redirecionar cliente inadimplente para pagamento.
    """
    try:
        # Buscar fatura mais antiga pendente
        result = db.execute(
            text("""
                SELECT
                    asaas_payment_id,
                    asaas_invoice_url,
                    valor,
                    data_vencimento
                FROM pagamentos
                WHERE cliente_id = :cliente_id
                AND status IN ('PENDING', 'OVERDUE')
                ORDER BY data_vencimento ASC
                LIMIT 1
            """),
            {"cliente_id": cliente_id}
        ).fetchone()

        if not result:
            return {
                "success": False,
                "message": "Nenhuma fatura pendente encontrada",
                "link": None
            }

        return {
            "success": True,
            "asaas_payment_id": result[0],
            "link": result[1],
            "valor": float(result[2]) if result[2] else 0,
            "vencimento": str(result[3]) if result[3] else None
        }

    except Exception as e:
        logger.error(f"Erro ao buscar link de pagamento: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar link: {str(e)}"
        )


@router.get("/verificar-status/{cliente_id}")
async def verificar_status_cliente(
    cliente_id: int,
    db: Session = Depends(get_db)
):
    """
    Verifica se o cliente está ativo ou suspenso.
    Usado pela página de conta suspensa para atualizar status após pagamento.
    """
    try:
        result = db.execute(
            text("""
                SELECT
                    c.ativo,
                    c.nome,
                    a.status as assinatura_status
                FROM clientes c
                LEFT JOIN assinaturas a ON a.cliente_id = c.id AND a.status != 'cancelada'
                WHERE c.id = :cliente_id
            """),
            {"cliente_id": cliente_id}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        return {
            "cliente_id": cliente_id,
            "nome": result[1],
            "ativo": result[0],
            "assinatura_status": result[2],
            "pode_acessar": result[0] == True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao verificar status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao verificar status: {str(e)}"
        )
