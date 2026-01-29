"""
API do Portal do Parceiro - Autenticação e Gestão
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import logging
import bcrypt
import secrets
import jwt
import os
import re
import unicodedata

from app.database import get_db
from app.services.email_service import get_email_service

router = APIRouter(prefix="/api/parceiro", tags=["Portal do Parceiro"])
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "parceiro-secret-key-change-in-production")
ALGORITHM = "HS256"


# ==================== SCHEMAS ====================

class ParceiroLogin(BaseModel):
    email: str
    senha: str


class ClienteParceiroCreate(BaseModel):
    nome_fantasia: str
    documento: str  # CPF ou CNPJ
    email: EmailStr
    telefone: str
    endereco: Optional[str] = None
    plano_id: int = 1
    medico_nome: str
    medico_especialidade: str
    medico_registro: str
    medico_email: EmailStr
    medico_telefone: Optional[str] = None


# ==================== HELPERS ====================

def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))


def criar_token_parceiro(parceiro_id: int, nome: str) -> str:
    payload = {
        "parceiro_id": parceiro_id,
        "nome": nome,
        "tipo": "parceiro",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_parceiro(request: Request):
    """Dependency para obter parceiro autenticado do JWT"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")

    token = auth_header.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("tipo") != "parceiro":
            raise HTTPException(status_code=401, detail="Token inválido")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


def gerar_subdomain(nome: str) -> str:
    nome_normalizado = unicodedata.normalize('NFKD', nome)
    nome_ascii = nome_normalizado.encode('ASCII', 'ignore').decode('ASCII')
    subdomain = nome_ascii.lower()
    subdomain = re.sub(r'[^a-z0-9]+', '-', subdomain)
    subdomain = subdomain.strip('-')
    if len(subdomain) > 30:
        subdomain = subdomain[:30].rstrip('-')
    return subdomain


def gerar_senha_temporaria() -> str:
    digitos = ''.join([str(secrets.randbelow(10)) for _ in range(4)])
    return f"HI@2025{digitos}"


# ==================== ENDPOINTS ====================

@router.post("/login")
async def login_parceiro(
    dados: ParceiroLogin,
    db: Session = Depends(get_db)
):
    """Login do parceiro comercial"""
    try:
        result = db.execute(
            text("""
                SELECT id, nome, email, senha_hash, ativo, status, token_ativacao
                FROM parceiros_comerciais
                WHERE email = :email
            """),
            {"email": dados.email}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=401, detail="Email ou senha incorretos")

        parceiro_id, nome, email, senha_hash, ativo, status, token_ativacao = result

        if not ativo:
            raise HTTPException(status_code=403, detail="Conta do parceiro desativada")

        if not senha_hash:
            raise HTTPException(status_code=401, detail="Conta sem senha definida. Contate o administrador.")

        if not verificar_senha(dados.senha, senha_hash):
            raise HTTPException(status_code=401, detail="Email ou senha incorretos")

        # Verificar status do parceiro
        if status == 'pendente_aprovacao':
            raise HTTPException(
                status_code=403,
                detail="pendente_aprovacao"
            )
        elif status == 'pendente_aceite':
            raise HTTPException(
                status_code=403,
                detail="pendente_ativacao"
            )
        elif status == 'suspenso':
            raise HTTPException(status_code=403, detail="conta_suspensa")
        elif status == 'inativo':
            raise HTTPException(status_code=403, detail="conta_inativa")
        elif status != 'ativo':
            raise HTTPException(status_code=403, detail="Conta do parceiro nao esta ativa")

        # Gerar JWT
        token = criar_token_parceiro(parceiro_id, nome)

        # Atualizar último login
        db.execute(
            text("UPDATE parceiros_comerciais SET ultimo_login = :agora WHERE id = :id"),
            {"id": parceiro_id, "agora": datetime.now()}
        )
        db.commit()

        logger.info(f"[Parceiro] Login: {nome} (ID={parceiro_id})")

        return {
            "sucesso": True,
            "token": token,
            "parceiro": {
                "id": parceiro_id,
                "nome": nome,
                "email": email
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Parceiro] Erro no login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao processar login")


@router.get("/me")
async def dados_parceiro(
    parceiro = Depends(get_current_parceiro),
    db: Session = Depends(get_db)
):
    """Retorna dados do parceiro logado"""
    result = db.execute(
        text("""
            SELECT id, nome, tipo_pessoa, cpf_cnpj, email, telefone,
                   percentual_comissao, tipo_comissao, parceria_lancamento,
                   criado_em, ultimo_login
            FROM parceiros_comerciais
            WHERE id = :id
        """),
        {"id": parceiro["parceiro_id"]}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")

    return {
        "id": result[0],
        "nome": result[1],
        "tipo_pessoa": result[2],
        "cpf_cnpj": result[3],
        "email": result[4],
        "telefone": result[5],
        "percentual_comissao": float(result[6]) if result[6] else 0,
        "tipo_comissao": result[7],
        "parceria_lancamento": result[8],
        "criado_em": result[9].isoformat() if result[9] else None,
        "ultimo_login": result[10].isoformat() if result[10] else None
    }


@router.get("/dashboard")
async def dashboard_parceiro(
    parceiro = Depends(get_current_parceiro),
    db: Session = Depends(get_db)
):
    """Retorna dados do dashboard do parceiro"""
    parceiro_id = parceiro["parceiro_id"]

    # Total de clientes
    total = db.execute(
        text("""
            SELECT COUNT(*) FROM clientes
            WHERE cadastrado_por_id = :parceiro_id AND cadastrado_por_tipo = 'parceiro'
        """),
        {"parceiro_id": parceiro_id}
    ).scalar() or 0

    # Por status
    stats = db.execute(
        text("""
            SELECT status, COUNT(*) FROM clientes
            WHERE cadastrado_por_id = :parceiro_id AND cadastrado_por_tipo = 'parceiro'
            GROUP BY status
        """),
        {"parceiro_id": parceiro_id}
    ).fetchall()

    status_map = {row[0]: row[1] for row in stats}

    # Comissões do mês
    comissoes = db.execute(
        text("""
            SELECT COALESCE(SUM(valor_comissao), 0)
            FROM comissoes
            WHERE parceiro_id = :parceiro_id
            AND EXTRACT(MONTH FROM data_referencia) = :mes
            AND EXTRACT(YEAR FROM data_referencia) = :ano
        """),
        {
            "parceiro_id": parceiro_id,
            "mes": datetime.now().month,
            "ano": datetime.now().year
        }
    ).scalar() or 0

    return {
        "total_clientes": total,
        "ativos": status_map.get('ativo', 0),
        "pendentes": status_map.get('pendente_aceite', 0),
        "suspensos": status_map.get('suspenso', 0),
        "comissao_mes": float(comissoes)
    }


@router.get("/clientes")
async def listar_clientes_parceiro(
    parceiro = Depends(get_current_parceiro),
    db: Session = Depends(get_db)
):
    """Lista clientes cadastrados pelo parceiro"""
    parceiro_id = parceiro["parceiro_id"]

    result = db.execute(
        text("""
            SELECT c.id, c.nome, c.email, c.plano, c.status, c.ativo,
                   c.subdomain, c.criado_em, c.valor_mensalidade
            FROM clientes c
            WHERE c.cadastrado_por_id = :parceiro_id AND c.cadastrado_por_tipo = 'parceiro'
            ORDER BY c.criado_em DESC
        """),
        {"parceiro_id": parceiro_id}
    ).fetchall()

    return [
        {
            "id": row[0],
            "nome": row[1],
            "email": row[2],
            "plano": row[3],
            "status": row[4],
            "ativo": row[5],
            "subdomain": row[6],
            "criado_em": row[7].isoformat() if row[7] else None,
            "valor_mensalidade": row[8]
        }
        for row in result
    ]


@router.post("/clientes")
async def criar_cliente_parceiro(
    dados: ClienteParceiroCreate,
    request: Request,
    parceiro = Depends(get_current_parceiro),
    db: Session = Depends(get_db)
):
    """
    Cria novo cliente pelo portal do parceiro.
    Fluxo simplificado: cria cliente com status pendente_aceite.
    """
    try:
        parceiro_id = parceiro["parceiro_id"]
        logger.info(f"[Parceiro] Criando cliente: {dados.nome_fantasia} (por parceiro {parceiro_id})")

        # Gerar subdomain
        subdomain_base = gerar_subdomain(dados.nome_fantasia)
        subdomain = subdomain_base
        contador = 1
        while True:
            exists = db.execute(
                text("SELECT id FROM clientes WHERE subdomain = :sub"),
                {"sub": subdomain}
            ).fetchone()
            if not exists:
                break
            subdomain = f"{subdomain_base}-{contador}"
            contador += 1
            if contador > 10:
                raise HTTPException(status_code=400, detail="Não foi possível gerar subdomain único")

        # Verificar email do médico
        med_exists = db.execute(
            text("SELECT id FROM medicos WHERE email = :email"),
            {"email": dados.medico_email}
        ).fetchone()
        if med_exists:
            raise HTTPException(status_code=400, detail=f"Email {dados.medico_email} já está em uso")

        # Buscar plano
        plano = db.execute(
            text("SELECT id, codigo, nome, valor_mensal, profissionais_inclusos, taxa_ativacao FROM planos WHERE id = :id AND ativo = true"),
            {"id": dados.plano_id}
        ).fetchone()
        if not plano:
            raise HTTPException(status_code=400, detail="Plano não encontrado")

        # Gerar token de ativação
        token_ativacao = secrets.token_urlsafe(64)
        token_expira = datetime.now() + timedelta(days=7)

        agora = datetime.now()

        # Criar cliente com status pendente
        result_cliente = db.execute(
            text("""
                INSERT INTO clientes (
                    nome, cnpj, email, telefone, endereco,
                    subdomain, plano, ativo, valor_mensalidade,
                    logo_icon, cor_primaria, cor_secundaria,
                    status, token_ativacao, token_expira_em,
                    cadastrado_por_id, cadastrado_por_tipo,
                    criado_em, atualizado_em
                ) VALUES (
                    :nome, :cnpj, :email, :telefone, :endereco,
                    :subdomain, :plano, false, :valor_mensalidade,
                    'fa-heartbeat', '#3b82f6', '#1e40af',
                    'pendente_aceite', :token_ativacao, :token_expira,
                    :cadastrado_por_id, 'parceiro',
                    :criado_em, :atualizado_em
                )
                RETURNING id
            """),
            {
                "nome": dados.nome_fantasia,
                "cnpj": dados.documento,
                "email": dados.email,
                "telefone": dados.telefone,
                "endereco": dados.endereco,
                "subdomain": subdomain,
                "plano": plano[1],
                "valor_mensalidade": str(plano[3]),
                "token_ativacao": token_ativacao,
                "token_expira": token_expira,
                "cadastrado_por_id": parceiro_id,
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        cliente_id = result_cliente.fetchone()[0]

        # Criar configurações
        db.execute(
            text("""
                INSERT INTO configuracoes (cliente_id, sistema_ativo, timezone, criado_em, atualizado_em)
                VALUES (:cliente_id, true, 'America/Sao_Paulo', :criado_em, :atualizado_em)
            """),
            {"cliente_id": cliente_id, "criado_em": agora, "atualizado_em": agora}
        )

        # Criar médico principal
        senha_temp = gerar_senha_temporaria()
        senha_hash = hash_senha(senha_temp)

        db.execute(
            text("""
                INSERT INTO medicos (
                    cliente_id, nome, crm, especialidade,
                    email, telefone, senha, ativo,
                    pode_fazer_login, is_admin, email_verificado,
                    is_secretaria, pode_ver_financeiro,
                    criado_em, atualizado_em
                ) VALUES (
                    :cliente_id, :nome, :crm, :especialidade,
                    :email, :telefone, :senha, true,
                    true, true, true,
                    false, true,
                    :criado_em, :atualizado_em
                )
            """),
            {
                "cliente_id": cliente_id,
                "nome": dados.medico_nome,
                "crm": dados.medico_registro,
                "especialidade": dados.medico_especialidade,
                "email": dados.medico_email,
                "telefone": dados.medico_telefone,
                "senha": senha_hash,
                "criado_em": agora,
                "atualizado_em": agora
            }
        )

        # Criar assinatura
        db.execute(
            text("""
                INSERT INTO assinaturas (
                    cliente_id, plano_id, valor_mensal,
                    profissionais_contratados, taxa_ativacao,
                    data_inicio, status, dia_vencimento,
                    periodo_cobranca, valor_original, valor_com_desconto,
                    criado_em
                ) VALUES (
                    :cliente_id, :plano_id, :valor_mensal,
                    1, :taxa_ativacao,
                    :data_inicio, 'pendente', 10,
                    'mensal', :valor_mensal, :valor_mensal,
                    :criado_em
                )
            """),
            {
                "cliente_id": cliente_id,
                "plano_id": plano[0],
                "valor_mensal": float(plano[3]),
                "taxa_ativacao": plano[5],
                "data_inicio": date.today(),
                "criado_em": agora
            }
        )

        # Criar vínculo parceiro-cliente
        parceiro_info = db.execute(
            text("SELECT percentual_comissao, parceria_lancamento, limite_clientes_lancamento FROM parceiros_comerciais WHERE id = :id"),
            {"id": parceiro_id}
        ).fetchone()

        if parceiro_info:
            clientes_count = db.execute(
                text("SELECT COUNT(*) FROM clientes_parceiros WHERE parceiro_id = :pid AND ativo = true"),
                {"pid": parceiro_id}
            ).scalar() or 0

            ordem = clientes_count + 1
            tipo_parceria = 'lancamento' if parceiro_info[1] and ordem <= (parceiro_info[2] or 40) else 'padrao'

            db.execute(
                text("""
                    INSERT INTO clientes_parceiros (
                        cliente_id, parceiro_id, data_vinculo, tipo_parceria,
                        ordem_cliente, ativo, criado_em
                    ) VALUES (
                        :cliente_id, :parceiro_id, :data_vinculo, :tipo_parceria,
                        :ordem_cliente, true, :criado_em
                    )
                """),
                {
                    "cliente_id": cliente_id,
                    "parceiro_id": parceiro_id,
                    "data_vinculo": date.today(),
                    "tipo_parceria": tipo_parceria,
                    "ordem_cliente": ordem,
                    "criado_em": agora
                }
            )

        db.commit()

        # Enviar email de ativação
        try:
            email_service = get_email_service()
            email_service.send_ativacao_conta(dados.email, dados.nome_fantasia, token_ativacao)
        except Exception as e:
            logger.warning(f"[Parceiro] Erro ao enviar email de ativação: {e}")

        logger.info(f"[Parceiro] Cliente {dados.nome_fantasia} criado (ID={cliente_id})")

        return {
            "sucesso": True,
            "cliente": {
                "id": cliente_id,
                "nome": dados.nome_fantasia,
                "subdomain": subdomain,
                "status": "pendente_aceite"
            },
            "link_ativacao": f"https://horariointeligente.com.br/static/ativar-conta.html?token={token_ativacao}",
            "mensagem": "Cliente criado. Email de ativação enviado."
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Parceiro] Erro ao criar cliente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao criar cliente: {str(e)}")


@router.post("/reenviar-ativacao/{cliente_id}")
async def reenviar_ativacao_parceiro(
    cliente_id: int,
    parceiro = Depends(get_current_parceiro),
    db: Session = Depends(get_db)
):
    """Reenvia email de ativação para um cliente do parceiro"""
    parceiro_id = parceiro["parceiro_id"]

    # Verificar se cliente pertence ao parceiro
    result = db.execute(
        text("""
            SELECT id, nome, email, status
            FROM clientes
            WHERE id = :id AND cadastrado_por_id = :parceiro_id AND cadastrado_por_tipo = 'parceiro'
        """),
        {"id": cliente_id, "parceiro_id": parceiro_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    if result[3] != 'pendente_aceite':
        raise HTTPException(status_code=400, detail="Cliente já ativou a conta")

    # Gerar novo token
    novo_token = secrets.token_urlsafe(64)
    expira_em = datetime.now() + timedelta(days=7)

    db.execute(
        text("""
            UPDATE clientes SET
                token_ativacao = :token,
                token_expira_em = :expira_em,
                atualizado_em = :atualizado_em
            WHERE id = :id
        """),
        {
            "id": cliente_id,
            "token": novo_token,
            "expira_em": expira_em,
            "atualizado_em": datetime.now()
        }
    )
    db.commit()

    # Enviar email
    try:
        email_service = get_email_service()
        email_service.send_ativacao_conta(result[2], result[1], novo_token)
    except Exception as e:
        logger.warning(f"[Parceiro] Erro ao reenviar email: {e}")

    return {
        "sucesso": True,
        "mensagem": "Email de ativação reenviado"
    }
