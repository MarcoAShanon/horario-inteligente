"""
API para Gestão de Parceiros Comerciais
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from decimal import Decimal
import json
import logging

from app.database import get_db
from app.services.auditoria_service import get_auditoria_service

router = APIRouter(prefix="/api/interno/parceiros", tags=["Parceiros Comerciais"])
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

class DadosBancarios(BaseModel):
    banco: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = None  # 'corrente', 'poupanca'
    titular: Optional[str] = None
    cpf_cnpj_titular: Optional[str] = None
    pix: Optional[str] = None


class ParceiroCreate(BaseModel):
    nome: str
    tipo_pessoa: str = 'PJ'  # 'PF' ou 'PJ'
    cpf_cnpj: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    percentual_comissao: float = 0
    valor_fixo_comissao: Optional[float] = None
    tipo_comissao: str = 'percentual'  # 'percentual' ou 'fixo'
    dados_bancarios: Optional[DadosBancarios] = None
    observacoes: Optional[str] = None


class ParceiroUpdate(BaseModel):
    nome: Optional[str] = None
    tipo_pessoa: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    percentual_comissao: Optional[float] = None
    valor_fixo_comissao: Optional[float] = None
    tipo_comissao: Optional[str] = None
    dados_bancarios: Optional[DadosBancarios] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class VincularCliente(BaseModel):
    cliente_id: int
    data_vinculo: str  # YYYY-MM-DD
    percentual_comissao_override: Optional[float] = None
    observacoes: Optional[str] = None


# ==================== ENDPOINTS ====================

@router.get("")
async def listar_parceiros(
    ativo: Optional[bool] = None,
    tipo_pessoa: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lista todos os parceiros comerciais"""
    query = """
        SELECT
            p.id, p.nome, p.tipo_pessoa, p.cpf_cnpj, p.email, p.telefone,
            p.percentual_comissao, p.tipo_comissao, p.ativo, p.criado_em,
            (SELECT COUNT(*) FROM clientes_parceiros cp WHERE cp.parceiro_id = p.id AND cp.ativo = true) as total_clientes
        FROM parceiros_comerciais p
        WHERE 1=1
    """
    params = {}

    if ativo is not None:
        query += " AND p.ativo = :ativo"
        params["ativo"] = ativo

    if tipo_pessoa:
        query += " AND p.tipo_pessoa = :tipo_pessoa"
        params["tipo_pessoa"] = tipo_pessoa

    query += " ORDER BY p.nome"

    result = db.execute(text(query), params).fetchall()

    return [
        {
            "id": row[0],
            "nome": row[1],
            "tipo_pessoa": row[2],
            "cpf_cnpj": row[3],
            "email": row[4],
            "telefone": row[5],
            "percentual_comissao": float(row[6]) if row[6] else 0,
            "tipo_comissao": row[7],
            "ativo": row[8],
            "criado_em": row[9].isoformat() if row[9] else None,
            "total_clientes": row[10]
        }
        for row in result
    ]


@router.get("/{parceiro_id}")
async def obter_parceiro(
    parceiro_id: int,
    db: Session = Depends(get_db)
):
    """Obtém detalhes de um parceiro comercial"""
    result = db.execute(text("""
        SELECT
            id, nome, tipo_pessoa, cpf_cnpj, email, telefone, endereco,
            percentual_comissao, valor_fixo_comissao, tipo_comissao,
            dados_bancarios, observacoes, ativo, criado_em, atualizado_em
        FROM parceiros_comerciais
        WHERE id = :id
    """), {"id": parceiro_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")

    # Buscar clientes vinculados
    clientes = db.execute(text("""
        SELECT
            cp.id, cp.cliente_id, c.nome as cliente_nome, cp.data_vinculo,
            cp.percentual_comissao_override, cp.ativo
        FROM clientes_parceiros cp
        JOIN clientes c ON c.id = cp.cliente_id
        WHERE cp.parceiro_id = :parceiro_id
        ORDER BY cp.data_vinculo DESC
    """), {"parceiro_id": parceiro_id}).fetchall()

    return {
        "id": result[0],
        "nome": result[1],
        "tipo_pessoa": result[2],
        "cpf_cnpj": result[3],
        "email": result[4],
        "telefone": result[5],
        "endereco": result[6],
        "percentual_comissao": float(result[7]) if result[7] else 0,
        "valor_fixo_comissao": float(result[8]) if result[8] else None,
        "tipo_comissao": result[9],
        "dados_bancarios": result[10],
        "observacoes": result[11],
        "ativo": result[12],
        "criado_em": result[13].isoformat() if result[13] else None,
        "atualizado_em": result[14].isoformat() if result[14] else None,
        "clientes": [
            {
                "vinculo_id": c[0],
                "cliente_id": c[1],
                "cliente_nome": c[2],
                "data_vinculo": c[3].isoformat() if c[3] else None,
                "percentual_comissao_override": float(c[4]) if c[4] else None,
                "ativo": c[5]
            }
            for c in clientes
        ]
    }


@router.post("")
async def criar_parceiro(
    dados: ParceiroCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Cria um novo parceiro comercial"""
    # Validar tipo_pessoa
    if dados.tipo_pessoa not in ['PF', 'PJ']:
        raise HTTPException(status_code=400, detail="Tipo de pessoa deve ser PF ou PJ")

    # Validar tipo_comissao
    if dados.tipo_comissao not in ['percentual', 'fixo']:
        raise HTTPException(status_code=400, detail="Tipo de comissão deve ser 'percentual' ou 'fixo'")

    # Verificar CPF/CNPJ duplicado
    if dados.cpf_cnpj:
        existe = db.execute(text("""
            SELECT id FROM parceiros_comerciais WHERE cpf_cnpj = :cpf_cnpj
        """), {"cpf_cnpj": dados.cpf_cnpj}).fetchone()
        if existe:
            raise HTTPException(status_code=400, detail="CPF/CNPJ já cadastrado")

    # Criar parceiro
    dados_bancarios_json = json.dumps(dados.dados_bancarios.dict()) if dados.dados_bancarios else None

    result = db.execute(text("""
        INSERT INTO parceiros_comerciais (
            nome, tipo_pessoa, cpf_cnpj, email, telefone, endereco,
            percentual_comissao, valor_fixo_comissao, tipo_comissao,
            dados_bancarios, observacoes, ativo
        ) VALUES (
            :nome, :tipo_pessoa, :cpf_cnpj, :email, :telefone, :endereco,
            :percentual_comissao, :valor_fixo_comissao, :tipo_comissao,
            CAST(:dados_bancarios AS jsonb), :observacoes, true
        ) RETURNING id
    """), {
        "nome": dados.nome,
        "tipo_pessoa": dados.tipo_pessoa,
        "cpf_cnpj": dados.cpf_cnpj,
        "email": dados.email,
        "telefone": dados.telefone,
        "endereco": dados.endereco,
        "percentual_comissao": dados.percentual_comissao,
        "valor_fixo_comissao": dados.valor_fixo_comissao,
        "tipo_comissao": dados.tipo_comissao,
        "dados_bancarios": dados_bancarios_json,
        "observacoes": dados.observacoes
    })

    parceiro_id = result.fetchone()[0]
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='criar',
        recurso='parceiro_comercial',
        recurso_id=parceiro_id,
        usuario_tipo='sistema',
        dados_novos={"nome": dados.nome, "cpf_cnpj": dados.cpf_cnpj},
        ip_address=request.client.host if request.client else None,
        descricao=f"Parceiro comercial criado: {dados.nome}"
    )

    logger.info(f"Parceiro comercial criado: {dados.nome}")

    return {
        "sucesso": True,
        "mensagem": "Parceiro criado com sucesso",
        "id": parceiro_id
    }


@router.put("/{parceiro_id}")
async def atualizar_parceiro(
    parceiro_id: int,
    dados: ParceiroUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Atualiza um parceiro comercial"""
    # Verificar se existe
    parceiro_atual = db.execute(text("""
        SELECT id, nome, cpf_cnpj FROM parceiros_comerciais WHERE id = :id
    """), {"id": parceiro_id}).fetchone()

    if not parceiro_atual:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")

    # Verificar CPF/CNPJ duplicado
    if dados.cpf_cnpj:
        existe = db.execute(text("""
            SELECT id FROM parceiros_comerciais WHERE cpf_cnpj = :cpf_cnpj AND id != :id
        """), {"cpf_cnpj": dados.cpf_cnpj, "id": parceiro_id}).fetchone()
        if existe:
            raise HTTPException(status_code=400, detail="CPF/CNPJ já cadastrado por outro parceiro")

    # Montar update dinâmico
    updates = []
    params = {"id": parceiro_id}

    campos_simples = ['nome', 'tipo_pessoa', 'cpf_cnpj', 'email', 'telefone',
                      'endereco', 'percentual_comissao', 'valor_fixo_comissao',
                      'tipo_comissao', 'observacoes', 'ativo']

    for campo in campos_simples:
        valor = getattr(dados, campo, None)
        if valor is not None:
            updates.append(f"{campo} = :{campo}")
            params[campo] = valor

    if dados.dados_bancarios:
        updates.append("dados_bancarios = CAST(:dados_bancarios AS jsonb)")
        params["dados_bancarios"] = json.dumps(dados.dados_bancarios.dict())

    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    updates.append("atualizado_em = NOW()")

    query = f"UPDATE parceiros_comerciais SET {', '.join(updates)} WHERE id = :id"
    db.execute(text(query), params)
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='atualizar',
        recurso='parceiro_comercial',
        recurso_id=parceiro_id,
        usuario_tipo='sistema',
        dados_anteriores={"nome": parceiro_atual[1]},
        dados_novos=dados.dict(exclude_none=True),
        ip_address=request.client.host if request.client else None,
        descricao=f"Parceiro comercial atualizado: ID={parceiro_id}"
    )

    logger.info(f"Parceiro comercial atualizado: ID={parceiro_id}")

    return {"sucesso": True, "mensagem": "Parceiro atualizado com sucesso"}


@router.delete("/{parceiro_id}")
async def desativar_parceiro(
    parceiro_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Desativa um parceiro comercial"""
    parceiro = db.execute(text("""
        SELECT id, nome FROM parceiros_comerciais WHERE id = :id
    """), {"id": parceiro_id}).fetchone()

    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")

    db.execute(text("""
        UPDATE parceiros_comerciais SET ativo = false, atualizado_em = NOW() WHERE id = :id
    """), {"id": parceiro_id})
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='deletar',
        recurso='parceiro_comercial',
        recurso_id=parceiro_id,
        usuario_tipo='sistema',
        ip_address=request.client.host if request.client else None,
        descricao=f"Parceiro comercial desativado: {parceiro[1]}"
    )

    logger.info(f"Parceiro comercial desativado: {parceiro[1]}")

    return {"sucesso": True, "mensagem": "Parceiro desativado com sucesso"}


# ==================== VÍNCULOS COM CLIENTES ====================

@router.post("/{parceiro_id}/vincular-cliente")
async def vincular_cliente(
    parceiro_id: int,
    dados: VincularCliente,
    request: Request,
    db: Session = Depends(get_db)
):
    """Vincula um cliente a um parceiro comercial"""
    # Verificar parceiro
    parceiro = db.execute(text("""
        SELECT id, nome FROM parceiros_comerciais WHERE id = :id AND ativo = true
    """), {"id": parceiro_id}).fetchone()

    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado ou inativo")

    # Verificar cliente
    cliente = db.execute(text("""
        SELECT id, nome FROM clientes WHERE id = :id
    """), {"id": dados.cliente_id}).fetchone()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Verificar se já existe vínculo ativo
    vinculo_existente = db.execute(text("""
        SELECT id FROM clientes_parceiros
        WHERE cliente_id = :cliente_id AND parceiro_id = :parceiro_id AND ativo = true
    """), {"cliente_id": dados.cliente_id, "parceiro_id": parceiro_id}).fetchone()

    if vinculo_existente:
        raise HTTPException(status_code=400, detail="Cliente já vinculado a este parceiro")

    # Criar vínculo
    result = db.execute(text("""
        INSERT INTO clientes_parceiros (
            cliente_id, parceiro_id, data_vinculo, percentual_comissao_override, observacoes, ativo
        ) VALUES (
            :cliente_id, :parceiro_id, :data_vinculo, :percentual_override, :observacoes, true
        ) RETURNING id
    """), {
        "cliente_id": dados.cliente_id,
        "parceiro_id": parceiro_id,
        "data_vinculo": dados.data_vinculo,
        "percentual_override": dados.percentual_comissao_override,
        "observacoes": dados.observacoes
    })

    vinculo_id = result.fetchone()[0]
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='criar',
        recurso='cliente_parceiro',
        recurso_id=vinculo_id,
        usuario_tipo='sistema',
        cliente_id=dados.cliente_id,
        dados_novos={"parceiro": parceiro[1], "cliente": cliente[1]},
        ip_address=request.client.host if request.client else None,
        descricao=f"Cliente {cliente[1]} vinculado ao parceiro {parceiro[1]}"
    )

    logger.info(f"Cliente {cliente[1]} vinculado ao parceiro {parceiro[1]}")

    return {
        "sucesso": True,
        "mensagem": "Cliente vinculado com sucesso",
        "vinculo_id": vinculo_id
    }


@router.delete("/{parceiro_id}/desvincular-cliente/{cliente_id}")
async def desvincular_cliente(
    parceiro_id: int,
    cliente_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Desvincula um cliente de um parceiro comercial"""
    vinculo = db.execute(text("""
        SELECT cp.id, p.nome as parceiro_nome, c.nome as cliente_nome
        FROM clientes_parceiros cp
        JOIN parceiros_comerciais p ON p.id = cp.parceiro_id
        JOIN clientes c ON c.id = cp.cliente_id
        WHERE cp.parceiro_id = :parceiro_id AND cp.cliente_id = :cliente_id AND cp.ativo = true
    """), {"parceiro_id": parceiro_id, "cliente_id": cliente_id}).fetchone()

    if not vinculo:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")

    db.execute(text("""
        UPDATE clientes_parceiros
        SET ativo = false, data_desvinculo = CURRENT_DATE, atualizado_em = NOW()
        WHERE id = :id
    """), {"id": vinculo[0]})
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='deletar',
        recurso='cliente_parceiro',
        recurso_id=vinculo[0],
        usuario_tipo='sistema',
        cliente_id=cliente_id,
        ip_address=request.client.host if request.client else None,
        descricao=f"Cliente {vinculo[2]} desvinculado do parceiro {vinculo[1]}"
    )

    logger.info(f"Cliente {vinculo[2]} desvinculado do parceiro {vinculo[1]}")

    return {"sucesso": True, "mensagem": "Cliente desvinculado com sucesso"}


# ==================== RELATÓRIOS DE COMISSÃO ====================

@router.get("/{parceiro_id}/comissoes")
async def calcular_comissoes(
    parceiro_id: int,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Calcula comissões devidas a um parceiro em um período"""
    from datetime import datetime

    # Usar mês/ano atual se não informado
    if not mes:
        mes = datetime.now().month
    if not ano:
        ano = datetime.now().year

    # Buscar parceiro
    parceiro = db.execute(text("""
        SELECT id, nome, percentual_comissao, tipo_comissao, valor_fixo_comissao
        FROM parceiros_comerciais WHERE id = :id
    """), {"id": parceiro_id}).fetchone()

    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")

    # Buscar clientes vinculados e seus pagamentos no período
    # TODO: Implementar lógica quando tivermos tabela de pagamentos
    clientes = db.execute(text("""
        SELECT
            cp.cliente_id, c.nome, c.valor_mensalidade,
            COALESCE(cp.percentual_comissao_override, :percentual_padrao) as percentual
        FROM clientes_parceiros cp
        JOIN clientes c ON c.id = cp.cliente_id
        WHERE cp.parceiro_id = :parceiro_id AND cp.ativo = true
    """), {"parceiro_id": parceiro_id, "percentual_padrao": parceiro[2]}).fetchall()

    total_comissao = 0
    detalhes = []

    for cliente in clientes:
        valor_mensalidade = float(cliente[2]) if cliente[2] else 0
        percentual = float(cliente[3]) if cliente[3] else 0
        comissao = valor_mensalidade * (percentual / 100)
        total_comissao += comissao

        detalhes.append({
            "cliente_id": cliente[0],
            "cliente_nome": cliente[1],
            "valor_mensalidade": valor_mensalidade,
            "percentual_comissao": percentual,
            "valor_comissao": round(comissao, 2)
        })

    return {
        "parceiro_id": parceiro_id,
        "parceiro_nome": parceiro[1],
        "periodo": f"{mes:02d}/{ano}",
        "total_comissao": round(total_comissao, 2),
        "detalhes": detalhes
    }


# ==================== PARCERIA ESTRATÉGICA DE LANÇAMENTO ====================

# Constantes de custos variáveis (do Plano de Negócios v1.1)
CUSTOS_VARIAVEIS_CLIENTE = Decimal('19.49')


def calcular_comissao_parceiro(
    tipo_comissao: str,
    percentual: Decimal,
    valor_fixo: Decimal,
    receita_cliente: Decimal,
    comissao_sobre: str = 'receita'
) -> dict:
    """
    Calcula comissão de um parceiro para um cliente específico.

    Regras de Parceria Estratégica de Lançamento:
    - 80% dos primeiros 50 clientes (40 clientes)
    - 40% da margem de contribuição
    - Recorrente enquanto cliente ativo
    """
    margem = receita_cliente - CUSTOS_VARIAVEIS_CLIENTE

    # Determinar base de cálculo
    if comissao_sobre == 'margem':
        base_calculo = margem
    else:
        base_calculo = receita_cliente

    # Calcular comissão
    if tipo_comissao == 'fixo':
        comissao = valor_fixo or Decimal('0')
    else:
        comissao = base_calculo * (percentual / 100)

    return {
        "receita_cliente": float(receita_cliente),
        "custos_variaveis": float(CUSTOS_VARIAVEIS_CLIENTE),
        "margem": float(margem),
        "base_calculo": float(base_calculo),
        "tipo_comissao": tipo_comissao,
        "percentual": float(percentual),
        "comissao": float(comissao),
        "margem_apos_comissao": float(margem - comissao)
    }


@router.post("/lancamento/configurar")
async def configurar_parceria_lancamento(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Configura o parceiro de lançamento estratégico.
    Cria ou atualiza o parceiro especial com 40% sobre margem.
    """
    dados = await request.json()

    nome = dados.get('nome', 'Parceria Estratégica de Lançamento')
    email = dados.get('email')
    pix = dados.get('pix')

    # Verificar se já existe parceiro de lançamento
    existente = db.execute(text("""
        SELECT id FROM parceiros_comerciais WHERE parceria_lancamento = true
    """)).fetchone()

    if existente:
        # Atualizar existente
        db.execute(text("""
            UPDATE parceiros_comerciais SET
                nome = :nome,
                email = :email,
                percentual_comissao = 40,
                tipo_comissao = 'percentual_margem',
                dados_bancarios = CAST(:dados_bancarios AS jsonb),
                atualizado_em = NOW()
            WHERE id = :id
        """), {
            "id": existente[0],
            "nome": nome,
            "email": email,
            "dados_bancarios": json.dumps({"pix": pix}) if pix else None
        })
        db.commit()

        return {
            "sucesso": True,
            "mensagem": "Parceiro de lançamento atualizado",
            "id": existente[0]
        }
    else:
        # Criar novo
        result = db.execute(text("""
            INSERT INTO parceiros_comerciais (
                nome, tipo_pessoa, email,
                percentual_comissao, tipo_comissao,
                parceria_lancamento, limite_clientes_lancamento,
                dados_bancarios, observacoes, ativo
            ) VALUES (
                :nome, 'PF', :email,
                40, 'percentual_margem',
                true, 40,
                CAST(:dados_bancarios AS jsonb),
                'Parceria de lançamento: 40% da margem para 80% dos primeiros 50 clientes (40 clientes). Comissão recorrente enquanto cliente ativo.',
                true
            ) RETURNING id
        """), {
            "nome": nome,
            "email": email,
            "dados_bancarios": json.dumps({"pix": pix}) if pix else None
        })

        parceiro_id = result.fetchone()[0]
        db.commit()

        logger.info(f"Parceiro de lançamento criado: ID={parceiro_id}")

        return {
            "sucesso": True,
            "mensagem": "Parceiro de lançamento configurado",
            "id": parceiro_id
        }


@router.get("/lancamento/status")
async def status_parceria_lancamento(db: Session = Depends(get_db)):
    """Retorna status atual da parceria de lançamento"""
    # Buscar parceiro de lançamento
    parceiro = db.execute(text("""
        SELECT id, nome, percentual_comissao, limite_clientes_lancamento
        FROM parceiros_comerciais
        WHERE parceria_lancamento = true AND ativo = true
    """)).fetchone()

    if not parceiro:
        return {
            "configurado": False,
            "mensagem": "Parceria de lançamento não configurada"
        }

    # Contar clientes vinculados à parceria de lançamento
    clientes_lancamento = db.execute(text("""
        SELECT COUNT(*) FROM clientes_parceiros
        WHERE parceiro_id = :parceiro_id
        AND tipo_parceria = 'lancamento'
        AND ativo = true
    """), {"parceiro_id": parceiro[0]}).scalar()

    # Total de clientes no sistema
    total_clientes = db.execute(text("""
        SELECT COUNT(*) FROM clientes WHERE ativo = true
    """)).scalar()

    limite = parceiro[3] or 40
    vagas_disponiveis = max(0, limite - clientes_lancamento)

    return {
        "configurado": True,
        "parceiro_id": parceiro[0],
        "parceiro_nome": parceiro[1],
        "percentual_comissao": float(parceiro[2]),
        "limite_clientes": limite,
        "clientes_vinculados": clientes_lancamento,
        "vagas_disponiveis": vagas_disponiveis,
        "total_clientes_sistema": total_clientes,
        "em_periodo_lancamento": total_clientes <= 50,
        "probabilidade_vinculo": "80%" if total_clientes <= 50 else "0%"
    }


@router.get("/relatorio/comissoes-mensais")
async def relatorio_comissoes_mensais(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Gera relatório de comissões a pagar no mês.
    Separa parceria estratégica de outras parcerias.
    """
    from datetime import datetime

    if not mes:
        mes = datetime.now().month
    if not ano:
        ano = datetime.now().year

    # Buscar clientes ativos com parceiros vinculados e suas assinaturas
    clientes_parceiros = db.execute(text("""
        SELECT
            cp.id, cp.cliente_id, cp.parceiro_id,
            cp.percentual_comissao_override, cp.tipo_parceria,
            cp.ordem_cliente, cp.comissao_sobre,
            p.nome as parceiro_nome, p.percentual_comissao as parceiro_percentual,
            p.tipo_comissao, p.valor_fixo_comissao, p.parceria_lancamento,
            c.nome as cliente_nome,
            a.valor_mensal, a.profissionais_contratados,
            pl.profissionais_inclusos, a.valor_profissional_adicional,
            a.numero_virtual_salvy, a.valor_numero_virtual
        FROM clientes_parceiros cp
        JOIN parceiros_comerciais p ON p.id = cp.parceiro_id
        JOIN clientes c ON c.id = cp.cliente_id
        LEFT JOIN assinaturas a ON a.cliente_id = cp.cliente_id AND a.status = 'ativa'
        LEFT JOIN planos pl ON pl.id = a.plano_id
        WHERE cp.ativo = true AND p.ativo = true
    """)).fetchall()

    comissoes_parceria_lancamento = []
    comissoes_outros = []

    for cp in clientes_parceiros:
        # Calcular receita do cliente
        if cp[13]:  # tem assinatura
            valor_base = Decimal(str(cp[13]))
            profissionais = cp[14] or 1
            profissionais_inclusos = cp[15] or 1
            valor_adicional = Decimal(str(cp[16] or 50))
            adicionais = max(0, profissionais - profissionais_inclusos)
            receita = valor_base + (adicionais * valor_adicional)
            if cp[17]:  # número virtual
                receita += Decimal(str(cp[18] or 40))
        else:
            receita = Decimal('0')

        if receita == 0:
            continue

        # Determinar percentual e tipo
        percentual = Decimal(str(cp[3])) if cp[3] else Decimal(str(cp[8]))
        tipo_comissao = cp[9] or 'percentual'
        valor_fixo = Decimal(str(cp[10])) if cp[10] else Decimal('0')
        comissao_sobre = cp[6] or 'receita'

        # Calcular comissão
        calculo = calcular_comissao_parceiro(
            tipo_comissao, percentual, valor_fixo, receita, comissao_sobre
        )

        dados = {
            "vinculo_id": cp[0],
            "parceiro_id": cp[2],
            "parceiro_nome": cp[7],
            "cliente_id": cp[1],
            "cliente_nome": cp[12],
            "tipo_parceria": cp[4] or 'padrao',
            "ordem_cliente": cp[5],
            **calculo
        }

        if cp[4] == 'lancamento' or cp[11]:  # tipo_parceria ou parceria_lancamento
            comissoes_parceria_lancamento.append(dados)
        else:
            comissoes_outros.append(dados)

    total_lancamento = sum(c['comissao'] for c in comissoes_parceria_lancamento)
    total_outros = sum(c['comissao'] for c in comissoes_outros)

    # Projeção para 40 clientes
    if comissoes_parceria_lancamento:
        media_comissao = total_lancamento / len(comissoes_parceria_lancamento)
        projecao_40_clientes = media_comissao * 40
    else:
        projecao_40_clientes = 40 * 52.20  # Estimativa: R$ 130,51 margem × 40% = R$ 52,20

    return {
        "periodo": {"mes": mes, "ano": ano},
        "parceria_lancamento": {
            "total_clientes": len(comissoes_parceria_lancamento),
            "limite_clientes": 40,
            "vagas_disponiveis": 40 - len(comissoes_parceria_lancamento),
            "comissao_total": round(total_lancamento, 2),
            "detalhes": comissoes_parceria_lancamento
        },
        "outras_parcerias": {
            "total_clientes": len(comissoes_outros),
            "comissao_total": round(total_outros, 2),
            "detalhes": comissoes_outros
        },
        "resumo": {
            "total_comissoes": round(total_lancamento + total_outros, 2),
            "projecao_40_clientes_lancamento": round(projecao_40_clientes, 2)
        }
    }


@router.post("/{parceiro_id}/vincular-cliente-lancamento")
async def vincular_cliente_parceria_lancamento(
    parceiro_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Vincula um cliente à parceria de lançamento.
    Regra: 80% dos primeiros 50 clientes (40 clientes máximo).
    """
    import random

    dados = await request.json()
    cliente_id = dados.get('cliente_id')
    forcar_vinculo = dados.get('forcar', False)  # Para testes ou casos especiais

    if not cliente_id:
        raise HTTPException(status_code=400, detail="cliente_id é obrigatório")

    # Buscar parceiro de lançamento
    parceiro = db.execute(text("""
        SELECT id, nome, limite_clientes_lancamento
        FROM parceiros_comerciais
        WHERE id = :id AND parceria_lancamento = true AND ativo = true
    """), {"id": parceiro_id}).fetchone()

    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro de lançamento não encontrado")

    # Verificar cliente
    cliente = db.execute(text("""
        SELECT id, nome FROM clientes WHERE id = :id
    """), {"id": cliente_id}).fetchone()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Verificar se já está vinculado
    vinculo_existente = db.execute(text("""
        SELECT id FROM clientes_parceiros
        WHERE cliente_id = :cliente_id AND parceiro_id = :parceiro_id AND ativo = true
    """), {"cliente_id": cliente_id, "parceiro_id": parceiro_id}).fetchone()

    if vinculo_existente:
        raise HTTPException(status_code=400, detail="Cliente já vinculado a este parceiro")

    # Contar clientes já vinculados à parceria de lançamento
    clientes_lancamento = db.execute(text("""
        SELECT COUNT(*) FROM clientes_parceiros
        WHERE parceiro_id = :parceiro_id
        AND tipo_parceria = 'lancamento'
        AND ativo = true
    """), {"parceiro_id": parceiro_id}).scalar()

    limite = parceiro[2] or 40

    # Verificar limite
    if clientes_lancamento >= limite:
        raise HTTPException(status_code=400, detail=f"Limite de {limite} clientes atingido")

    # Total de clientes do sistema
    total_clientes = db.execute(text("""
        SELECT COUNT(*) FROM clientes
    """)).scalar()

    # Se ainda nos primeiros 50 clientes, aplicar regra de 80%
    if total_clientes <= 50 and not forcar_vinculo:
        if random.random() > 0.80:  # 20% de chance de NÃO ser vinculado
            return {
                "sucesso": False,
                "mensagem": "Cliente não selecionado para parceria de lançamento (sorteio 80%)",
                "pode_vincular_manualmente": True
            }

    # Criar vínculo
    from datetime import date
    ordem = clientes_lancamento + 1

    result = db.execute(text("""
        INSERT INTO clientes_parceiros (
            cliente_id, parceiro_id, data_vinculo,
            percentual_comissao_override, tipo_parceria,
            ordem_cliente, comissao_sobre, ativo
        ) VALUES (
            :cliente_id, :parceiro_id, :data_vinculo,
            40, 'lancamento',
            :ordem, 'margem', true
        ) RETURNING id
    """), {
        "cliente_id": cliente_id,
        "parceiro_id": parceiro_id,
        "data_vinculo": date.today(),
        "ordem": ordem
    })

    vinculo_id = result.fetchone()[0]
    db.commit()

    logger.info(f"Cliente {cliente[1]} vinculado à parceria de lançamento (ordem: {ordem})")

    return {
        "sucesso": True,
        "mensagem": f"Cliente vinculado à parceria de lançamento",
        "vinculo_id": vinculo_id,
        "ordem_cliente": ordem,
        "clientes_restantes": limite - ordem
    }


@router.get("/lancamento/simulacao")
async def simular_parceria_lancamento(
    receita_cliente: float = 150.0,
    db: Session = Depends(get_db)
):
    """
    Simula valores da parceria de lançamento.

    Com receita padrão de R$ 150:
    - Margem: R$ 150 - R$ 19,49 = R$ 130,51
    - Comissão (40%): R$ 52,20
    - Margem após comissão: R$ 78,31
    """
    receita = Decimal(str(receita_cliente))
    margem = receita - CUSTOS_VARIAVEIS_CLIENTE
    comissao = margem * Decimal('0.40')
    margem_apos = margem - comissao

    return {
        "receita_cliente": float(receita),
        "custos_variaveis": float(CUSTOS_VARIAVEIS_CLIENTE),
        "margem_bruta": float(margem),
        "percentual_comissao": 40,
        "comissao_parceiro": round(float(comissao), 2),
        "margem_apos_comissao": round(float(margem_apos), 2),
        "projecao": {
            "1_cliente": round(float(comissao), 2),
            "10_clientes": round(float(comissao * 10), 2),
            "40_clientes": round(float(comissao * 40), 2),
            "40_clientes_12_meses": round(float(comissao * 40 * 12), 2)
        }
    }
