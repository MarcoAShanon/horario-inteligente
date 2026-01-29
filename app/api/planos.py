"""
API de Planos e Assinaturas
Endpoints para gestão de planos e assinaturas de clientes

Nota: Usa SQL raw para evitar problemas de circular import com os models ORM
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.api.admin import get_current_admin
from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import date
import logging

router = APIRouter(prefix="/api/interno/planos", tags=["Planos e Assinaturas"])
logger = logging.getLogger(__name__)


# ============ SCHEMAS ============

class PlanoResponse(BaseModel):
    id: int
    codigo: str
    nome: str
    descricao: Optional[str]
    valor_mensal: float
    profissionais_inclusos: int
    valor_profissional_adicional: float
    taxa_ativacao: float
    ativo: bool

    class Config:
        from_attributes = True


class CriarAssinaturaRequest(BaseModel):
    cliente_id: int
    plano_codigo: str
    profissionais_contratados: int = 1
    numero_virtual_salvy: bool = False
    desconto_ativacao_percentual: float = 0
    motivo_desconto_ativacao: Optional[str] = None
    dia_vencimento: int = 10


# ============ HELPER FUNCTIONS ============

def calcular_valor_total_assinatura(
    valor_mensal: float,
    profissionais_contratados: int,
    profissionais_inclusos: int,
    valor_profissional_adicional: float,
    numero_virtual_salvy: bool
) -> float:
    """Calcula o valor total mensal da assinatura"""
    adicionais = max(0, profissionais_contratados - profissionais_inclusos)
    valor_adicionais = adicionais * valor_profissional_adicional
    valor_virtual = 40.00 if numero_virtual_salvy else 0
    return valor_mensal + valor_adicionais + valor_virtual


def calcular_taxa_ativacao_final(taxa_ativacao: float, desconto_percentual: float) -> float:
    """Calcula taxa de ativação com desconto"""
    desconto = taxa_ativacao * (desconto_percentual / 100)
    return taxa_ativacao - desconto


# ============ ENDPOINTS DE PLANOS ============

@router.get("/", response_model=List[PlanoResponse])
def listar_planos(admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Lista todos os planos disponíveis"""
    result = db.execute(text("""
        SELECT id, codigo, nome, descricao, valor_mensal,
               profissionais_inclusos, valor_profissional_adicional,
               taxa_ativacao, ativo
        FROM planos WHERE ativo = true
    """)).fetchall()

    return [
        PlanoResponse(
            id=p[0],
            codigo=p[1],
            nome=p[2],
            descricao=p[3],
            valor_mensal=float(p[4]),
            profissionais_inclusos=p[5],
            valor_profissional_adicional=float(p[6]),
            taxa_ativacao=float(p[7]),
            ativo=p[8]
        )
        for p in result
    ]


@router.get("/{codigo}", response_model=PlanoResponse)
def obter_plano(codigo: str, admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Obtém detalhes de um plano específico"""
    result = db.execute(text("""
        SELECT id, codigo, nome, descricao, valor_mensal,
               profissionais_inclusos, valor_profissional_adicional,
               taxa_ativacao, ativo
        FROM planos WHERE codigo = :codigo
    """), {"codigo": codigo}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    return PlanoResponse(
        id=result[0],
        codigo=result[1],
        nome=result[2],
        descricao=result[3],
        valor_mensal=float(result[4]),
        profissionais_inclusos=result[5],
        valor_profissional_adicional=float(result[6]),
        taxa_ativacao=float(result[7]),
        ativo=result[8]
    )


# ============ ENDPOINTS DE ASSINATURAS ============

@router.post("/assinaturas")
def criar_assinatura(dados: CriarAssinaturaRequest, admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Cria uma nova assinatura para um cliente"""

    # Buscar plano
    plano = db.execute(text("""
        SELECT id, codigo, nome, valor_mensal, profissionais_inclusos,
               valor_profissional_adicional, taxa_ativacao
        FROM planos WHERE codigo = :codigo
    """), {"codigo": dados.plano_codigo}).fetchone()

    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    plano_id = plano[0]
    plano_codigo = plano[1]
    plano_nome = plano[2]
    valor_mensal = float(plano[3])
    profissionais_inclusos = plano[4]
    valor_profissional_adicional = float(plano[5])
    taxa_ativacao = float(plano[6])

    # Verificar se cliente existe
    cliente_exists = db.execute(
        text("SELECT id FROM clientes WHERE id = :id"),
        {"id": dados.cliente_id}
    ).fetchone()
    if not cliente_exists:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Verificar se cliente já tem assinatura ativa
    assinatura_existente = db.execute(
        text("SELECT id FROM assinaturas WHERE cliente_id = :cliente_id AND status = 'ativa'"),
        {"cliente_id": dados.cliente_id}
    ).fetchone()

    if assinatura_existente:
        raise HTTPException(status_code=400, detail="Cliente já possui assinatura ativa")

    # Inserir assinatura
    result = db.execute(text("""
        INSERT INTO assinaturas (
            cliente_id, plano_id, valor_mensal, valor_profissional_adicional,
            profissionais_contratados, taxa_ativacao, desconto_ativacao_percentual,
            motivo_desconto_ativacao, numero_virtual_salvy, dia_vencimento,
            data_inicio, status
        ) VALUES (
            :cliente_id, :plano_id, :valor_mensal, :valor_profissional_adicional,
            :profissionais_contratados, :taxa_ativacao, :desconto_ativacao_percentual,
            :motivo_desconto_ativacao, :numero_virtual_salvy, :dia_vencimento,
            :data_inicio, 'ativa'
        ) RETURNING id
    """), {
        "cliente_id": dados.cliente_id,
        "plano_id": plano_id,
        "valor_mensal": valor_mensal,
        "valor_profissional_adicional": valor_profissional_adicional,
        "profissionais_contratados": dados.profissionais_contratados,
        "taxa_ativacao": taxa_ativacao,
        "desconto_ativacao_percentual": dados.desconto_ativacao_percentual,
        "motivo_desconto_ativacao": dados.motivo_desconto_ativacao,
        "numero_virtual_salvy": dados.numero_virtual_salvy,
        "dia_vencimento": dados.dia_vencimento,
        "data_inicio": date.today()
    })

    assinatura_id = result.fetchone()[0]
    db.commit()

    logger.info(f"Assinatura criada: id={assinatura_id}, cliente_id={dados.cliente_id}, plano={dados.plano_codigo}")

    valor_total = calcular_valor_total_assinatura(
        valor_mensal, dados.profissionais_contratados,
        profissionais_inclusos, valor_profissional_adicional,
        dados.numero_virtual_salvy
    )
    taxa_final = calcular_taxa_ativacao_final(taxa_ativacao, dados.desconto_ativacao_percentual)

    return {
        "success": True,
        "data": {
            "id": assinatura_id,
            "cliente_id": dados.cliente_id,
            "plano_id": plano_id,
            "plano_codigo": plano_codigo,
            "plano_nome": plano_nome,
            "valor_mensal": valor_mensal,
            "valor_total_mensal": valor_total,
            "profissionais_contratados": dados.profissionais_contratados,
            "taxa_ativacao": taxa_ativacao,
            "taxa_ativacao_final": taxa_final,
            "taxa_ativacao_paga": False,
            "numero_virtual_salvy": dados.numero_virtual_salvy,
            "status": "ativa",
            "data_inicio": date.today().isoformat()
        }
    }


@router.get("/assinaturas/todas")
def listar_assinaturas(
    status_filter: Optional[str] = None,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lista todas as assinaturas com filtro opcional de status"""
    if status_filter:
        query = text("""
            SELECT a.id, a.cliente_id, a.plano_id, p.codigo, p.nome,
                   a.valor_mensal, a.profissionais_contratados,
                   p.profissionais_inclusos, a.valor_profissional_adicional,
                   a.numero_virtual_salvy, a.taxa_ativacao_paga, a.status, a.data_inicio
            FROM assinaturas a
            JOIN planos p ON a.plano_id = p.id
            WHERE a.status = :status
        """)
        result = db.execute(query, {"status": status_filter}).fetchall()
    else:
        query = text("""
            SELECT a.id, a.cliente_id, a.plano_id, p.codigo, p.nome,
                   a.valor_mensal, a.profissionais_contratados,
                   p.profissionais_inclusos, a.valor_profissional_adicional,
                   a.numero_virtual_salvy, a.taxa_ativacao_paga, a.status, a.data_inicio
            FROM assinaturas a
            JOIN planos p ON a.plano_id = p.id
        """)
        result = db.execute(query).fetchall()

    data = []
    for a in result:
        valor_total = calcular_valor_total_assinatura(
            float(a[5]), a[6], a[7], float(a[8]), a[9]
        )
        data.append({
            "id": a[0],
            "cliente_id": a[1],
            "plano_id": a[2],
            "plano_codigo": a[3],
            "plano_nome": a[4],
            "valor_mensal": float(a[5]),
            "valor_total_mensal": valor_total,
            "profissionais_contratados": a[6],
            "taxa_ativacao_paga": a[10],
            "numero_virtual_salvy": a[9],
            "status": a[11],
            "data_inicio": a[12].isoformat() if a[12] else None
        })

    return {"success": True, "data": data, "total": len(data)}


@router.get("/assinaturas/{cliente_id}")
def obter_assinatura_cliente(cliente_id: int, admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Obtém a assinatura ativa de um cliente"""
    result = db.execute(text("""
        SELECT a.id, a.cliente_id, a.plano_id, p.codigo, p.nome,
               a.valor_mensal, a.profissionais_contratados,
               p.profissionais_inclusos, a.valor_profissional_adicional,
               a.numero_virtual_salvy, a.taxa_ativacao, a.desconto_ativacao_percentual,
               a.taxa_ativacao_paga, a.status, a.data_inicio
        FROM assinaturas a
        JOIN planos p ON a.plano_id = p.id
        WHERE a.cliente_id = :cliente_id AND a.status = 'ativa'
    """), {"cliente_id": cliente_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    valor_total = calcular_valor_total_assinatura(
        float(result[5]), result[6], result[7], float(result[8]), result[9]
    )
    taxa_final = calcular_taxa_ativacao_final(float(result[10]), float(result[11]))

    return {
        "success": True,
        "data": {
            "id": result[0],
            "cliente_id": result[1],
            "plano_id": result[2],
            "plano_codigo": result[3],
            "plano_nome": result[4],
            "valor_mensal": float(result[5]),
            "valor_total_mensal": valor_total,
            "profissionais_contratados": result[6],
            "taxa_ativacao": float(result[10]),
            "taxa_ativacao_final": taxa_final,
            "taxa_ativacao_paga": result[12],
            "numero_virtual_salvy": result[9],
            "status": result[13],
            "data_inicio": result[14].isoformat() if result[14] else None
        }
    }


@router.post("/assinaturas/{assinatura_id}/pagar-ativacao")
def registrar_pagamento_ativacao(assinatura_id: int, admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Registra pagamento da taxa de ativação"""
    result = db.execute(
        text("SELECT id FROM assinaturas WHERE id = :id"),
        {"id": assinatura_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    db.execute(
        text("UPDATE assinaturas SET taxa_ativacao_paga = true WHERE id = :id"),
        {"id": assinatura_id}
    )
    db.commit()

    logger.info(f"Taxa de ativação registrada como paga: assinatura_id={assinatura_id}")

    return {"success": True, "message": "Taxa de ativação registrada como paga"}


@router.post("/assinaturas/{assinatura_id}/cancelar")
def cancelar_assinatura(
    assinatura_id: int,
    motivo: str = "Cancelamento solicitado",
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cancela uma assinatura"""
    result = db.execute(
        text("SELECT id FROM assinaturas WHERE id = :id"),
        {"id": assinatura_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    db.execute(text("""
        UPDATE assinaturas
        SET status = 'cancelada', data_fim = :data_fim, motivo_cancelamento = :motivo
        WHERE id = :id
    """), {"id": assinatura_id, "data_fim": date.today(), "motivo": motivo})
    db.commit()

    logger.info(f"Assinatura cancelada: assinatura_id={assinatura_id}, motivo={motivo}")

    return {"success": True, "message": "Assinatura cancelada"}


# ============ SIMULAÇÃO ============

@router.get("/simulacao/{plano_codigo}")
def simular_assinatura(
    plano_codigo: str,
    profissionais: int = 1,
    numero_virtual: bool = False,
    desconto_ativacao: float = 0,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Simula valores de uma assinatura antes de criar"""
    plano = db.execute(text("""
        SELECT codigo, nome, valor_mensal, profissionais_inclusos,
               valor_profissional_adicional, taxa_ativacao
        FROM planos WHERE codigo = :codigo
    """), {"codigo": plano_codigo}).fetchone()

    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    valor_base = float(plano[2])
    profissionais_inclusos = plano[3]
    valor_profissional_adicional = float(plano[4])
    taxa_ativacao_original = float(plano[5])

    # Calcular valores
    adicionais = max(0, profissionais - profissionais_inclusos)
    valor_adicionais = adicionais * valor_profissional_adicional
    valor_numero_virtual = 40.00 if numero_virtual else 0
    valor_mensal_total = valor_base + valor_adicionais + valor_numero_virtual

    taxa_ativacao_desconto = taxa_ativacao_original * (desconto_ativacao / 100)
    taxa_ativacao_final = taxa_ativacao_original - taxa_ativacao_desconto

    # Custos variáveis (do Plano de Negócios v1.1)
    custos_variaveis = 19.49
    margem = valor_mensal_total - custos_variaveis
    margem_percentual = (margem / valor_mensal_total) * 100 if valor_mensal_total > 0 else 0

    return {
        "plano": {
            "codigo": plano[0],
            "nome": plano[1],
            "valor_base": valor_base,
            "profissionais_inclusos": profissionais_inclusos
        },
        "configuracao": {
            "profissionais_contratados": profissionais,
            "profissionais_adicionais": adicionais,
            "numero_virtual": numero_virtual
        },
        "valores": {
            "valor_base": valor_base,
            "valor_adicionais": valor_adicionais,
            "valor_numero_virtual": valor_numero_virtual,
            "valor_mensal_total": valor_mensal_total
        },
        "taxa_ativacao": {
            "valor_original": taxa_ativacao_original,
            "desconto_percentual": desconto_ativacao,
            "valor_desconto": taxa_ativacao_desconto,
            "valor_final": taxa_ativacao_final
        },
        "analise_financeira": {
            "custos_variaveis": custos_variaveis,
            "margem_bruta": round(margem, 2),
            "margem_percentual": round(margem_percentual, 1)
        }
    }


# ============ MÉTRICAS ============

@router.get("/metricas/mrr")
def calcular_mrr(admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Calcula MRR baseado em assinaturas ativas"""

    result = db.execute(text("""
        SELECT a.cliente_id, p.codigo, a.valor_mensal, a.profissionais_contratados,
               p.profissionais_inclusos, a.valor_profissional_adicional, a.numero_virtual_salvy
        FROM assinaturas a
        JOIN planos p ON a.plano_id = p.id
        WHERE a.status = 'ativa'
    """)).fetchall()

    mrr_total = 0.0
    detalhes = []

    for a in result:
        valor_total = calcular_valor_total_assinatura(
            float(a[2]), a[3], a[4], float(a[5]), a[6]
        )
        mrr_total += valor_total
        detalhes.append({
            "cliente_id": a[0],
            "plano": a[1],
            "valor_mensal": valor_total,
            "profissionais": a[3],
            "numero_virtual": a[6]
        })

    return {
        "success": True,
        "data": {
            "mrr_total": round(mrr_total, 2),
            "total_assinaturas_ativas": len(result),
            "ticket_medio": round(mrr_total / len(result), 2) if result else 0,
            "detalhes": detalhes
        }
    }
