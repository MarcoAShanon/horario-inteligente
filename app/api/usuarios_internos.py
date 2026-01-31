"""
API para Gestão de Usuários Internos (Admin, Financeiro, Suporte)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
import re
from datetime import datetime, timezone
import bcrypt
import logging

from app.database import get_db
from app.api.admin import get_current_admin
from app.services.auditoria_service import get_auditoria_service
from app.api.auth import _unified_login_logic

from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/interno/usuarios", tags=["Usuarios Internos"])
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

class UsuarioInternoCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    perfil: str  # 'admin', 'financeiro', 'suporte'
    telefone: Optional[str] = None

    @validator('senha')
    def senha_forte(cls, v):
        if len(v) < 8:
            raise ValueError('Senha deve ter no mínimo 8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Senha deve conter pelo menos uma letra maiúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('Senha deve conter pelo menos uma letra minúscula')
        if not re.search(r'\d', v):
            raise ValueError('Senha deve conter pelo menos um número')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Senha deve conter pelo menos um caractere especial (!@#$%^&*)')
        return v


class UsuarioInternoUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    perfil: Optional[str] = None
    telefone: Optional[str] = None
    ativo: Optional[bool] = None


class UsuarioInternoSenha(BaseModel):
    senha_atual: str
    nova_senha: str

    @validator('nova_senha')
    def senha_forte(cls, v):
        if len(v) < 8:
            raise ValueError('Senha deve ter no mínimo 8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Senha deve conter pelo menos uma letra maiúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('Senha deve conter pelo menos uma letra minúscula')
        if not re.search(r'\d', v):
            raise ValueError('Senha deve conter pelo menos um número')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Senha deve conter pelo menos um caractere especial (!@#$%^&*)')
        return v


class UsuarioInternoLogin(BaseModel):
    email: EmailStr
    senha: str


# ==================== HELPERS ====================

PERFIS_VALIDOS = ['admin', 'financeiro', 'suporte']


def hash_senha(senha: str) -> str:
    """Gera hash bcrypt da senha"""
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha confere com o hash"""
    return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))


# ==================== ENDPOINTS ====================

@router.get("")
async def listar_usuarios(
    perfil: Optional[str] = None,
    ativo: Optional[bool] = None,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lista todos os usuários internos"""
    query = """
        SELECT id, nome, email, perfil, telefone, ativo, ultimo_acesso, criado_em
        FROM usuarios_internos
        WHERE 1=1
    """
    params = {}

    if perfil:
        query += " AND perfil = :perfil"
        params["perfil"] = perfil

    if ativo is not None:
        query += " AND ativo = :ativo"
        params["ativo"] = ativo

    query += " ORDER BY nome"

    result = db.execute(text(query), params).fetchall()

    return [
        {
            "id": row[0],
            "nome": row[1],
            "email": row[2],
            "perfil": row[3],
            "telefone": row[4],
            "ativo": row[5],
            "ultimo_acesso": row[6].isoformat() if row[6] else None,
            "criado_em": row[7].isoformat() if row[7] else None
        }
        for row in result
    ]


@router.get("/{usuario_id}")
async def obter_usuario(
    usuario_id: int,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtém um usuário interno pelo ID"""
    result = db.execute(text("""
        SELECT id, nome, email, perfil, telefone, ativo, ultimo_acesso, criado_em, atualizado_em
        FROM usuarios_internos
        WHERE id = :id
    """), {"id": usuario_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return {
        "id": result[0],
        "nome": result[1],
        "email": result[2],
        "perfil": result[3],
        "telefone": result[4],
        "ativo": result[5],
        "ultimo_acesso": result[6].isoformat() if result[6] else None,
        "criado_em": result[7].isoformat() if result[7] else None,
        "atualizado_em": result[8].isoformat() if result[8] else None
    }


@router.post("")
async def criar_usuario(
    dados: UsuarioInternoCreate,
    request: Request,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cria um novo usuário interno"""
    # Validar perfil
    if dados.perfil not in PERFIS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Perfil inválido. Valores aceitos: {', '.join(PERFIS_VALIDOS)}"
        )

    # Verificar se email já existe
    existe = db.execute(text("""
        SELECT id FROM usuarios_internos WHERE email = :email
    """), {"email": dados.email}).fetchone()

    if existe:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Criar usuário
    senha_hash = hash_senha(dados.senha)

    result = db.execute(text("""
        INSERT INTO usuarios_internos (nome, email, senha_hash, perfil, telefone, ativo)
        VALUES (:nome, :email, :senha_hash, :perfil, :telefone, true)
        RETURNING id
    """), {
        "nome": dados.nome,
        "email": dados.email,
        "senha_hash": senha_hash,
        "perfil": dados.perfil,
        "telefone": dados.telefone
    })

    usuario_id = result.fetchone()[0]
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='criar',
        recurso='usuario_interno',
        recurso_id=usuario_id,
        usuario_tipo='sistema',
        dados_novos={"nome": dados.nome, "email": dados.email, "perfil": dados.perfil},
        ip_address=request.client.host if request.client else None,
        descricao=f"Usuário interno criado: {dados.email} ({dados.perfil})"
    )

    logger.info(f"Usuário interno criado: {dados.email} ({dados.perfil})")

    return {
        "sucesso": True,
        "mensagem": "Usuário criado com sucesso",
        "id": usuario_id
    }


@router.put("/{usuario_id}")
async def atualizar_usuario(
    usuario_id: int,
    dados: UsuarioInternoUpdate,
    request: Request,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Atualiza um usuário interno"""
    # Verificar se existe
    usuario_atual = db.execute(text("""
        SELECT id, nome, email, perfil, telefone, ativo
        FROM usuarios_internos WHERE id = :id
    """), {"id": usuario_id}).fetchone()

    if not usuario_atual:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Validar perfil se fornecido
    if dados.perfil and dados.perfil not in PERFIS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Perfil inválido. Valores aceitos: {', '.join(PERFIS_VALIDOS)}"
        )

    # Verificar email duplicado
    if dados.email and dados.email != usuario_atual[2]:
        existe = db.execute(text("""
            SELECT id FROM usuarios_internos WHERE email = :email AND id != :id
        """), {"email": dados.email, "id": usuario_id}).fetchone()
        if existe:
            raise HTTPException(status_code=400, detail="Email já cadastrado por outro usuário")

    # Montar update dinâmico
    updates = []
    params = {"id": usuario_id}

    if dados.nome:
        updates.append("nome = :nome")
        params["nome"] = dados.nome
    if dados.email:
        updates.append("email = :email")
        params["email"] = dados.email
    if dados.perfil:
        updates.append("perfil = :perfil")
        params["perfil"] = dados.perfil
    if dados.telefone is not None:
        updates.append("telefone = :telefone")
        params["telefone"] = dados.telefone
    if dados.ativo is not None:
        updates.append("ativo = :ativo")
        params["ativo"] = dados.ativo

    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    updates.append("atualizado_em = NOW()")

    query = f"UPDATE usuarios_internos SET {', '.join(updates)} WHERE id = :id"
    db.execute(text(query), params)
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='atualizar',
        recurso='usuario_interno',
        recurso_id=usuario_id,
        usuario_tipo='sistema',
        dados_anteriores={
            "nome": usuario_atual[1],
            "email": usuario_atual[2],
            "perfil": usuario_atual[3],
            "ativo": usuario_atual[5]
        },
        dados_novos=dados.dict(exclude_none=True),
        ip_address=request.client.host if request.client else None,
        descricao=f"Usuário interno atualizado: ID={usuario_id}"
    )

    logger.info(f"Usuário interno atualizado: ID={usuario_id}")

    return {"sucesso": True, "mensagem": "Usuário atualizado com sucesso"}


@router.delete("/{usuario_id}")
async def desativar_usuario(
    usuario_id: int,
    request: Request,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Desativa um usuário interno (soft delete)"""
    # Verificar se existe
    usuario = db.execute(text("""
        SELECT id, nome, email FROM usuarios_internos WHERE id = :id
    """), {"id": usuario_id}).fetchone()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Desativar
    db.execute(text("""
        UPDATE usuarios_internos
        SET ativo = false, atualizado_em = NOW()
        WHERE id = :id
    """), {"id": usuario_id})
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='deletar',
        recurso='usuario_interno',
        recurso_id=usuario_id,
        usuario_tipo='sistema',
        dados_anteriores={"nome": usuario[1], "email": usuario[2]},
        ip_address=request.client.host if request.client else None,
        descricao=f"Usuário interno desativado: {usuario[2]}"
    )

    logger.info(f"Usuário interno desativado: {usuario[2]}")

    return {"sucesso": True, "mensagem": "Usuário desativado com sucesso"}


@router.post("/{usuario_id}/alterar-senha")
async def alterar_senha(
    usuario_id: int,
    dados: UsuarioInternoSenha,
    request: Request,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Altera a senha de um usuário interno"""
    # Buscar usuário
    usuario = db.execute(text("""
        SELECT id, email, senha_hash FROM usuarios_internos WHERE id = :id
    """), {"id": usuario_id}).fetchone()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Verificar senha atual
    if not verificar_senha(dados.senha_atual, usuario[2]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    # Atualizar senha
    nova_senha_hash = hash_senha(dados.nova_senha)

    db.execute(text("""
        UPDATE usuarios_internos
        SET senha_hash = :senha_hash, atualizado_em = NOW()
        WHERE id = :id
    """), {"senha_hash": nova_senha_hash, "id": usuario_id})
    db.commit()

    # Registrar auditoria
    auditoria = get_auditoria_service(db)
    auditoria.registrar(
        acao='atualizar',
        recurso='usuario_interno',
        recurso_id=usuario_id,
        usuario_tipo='sistema',
        ip_address=request.client.host if request.client else None,
        descricao=f"Senha alterada: {usuario[1]}"
    )

    logger.info(f"Senha alterada para usuário: {usuario[1]}")

    return {"sucesso": True, "mensagem": "Senha alterada com sucesso"}


@router.post("/login")
@limiter.limit("5/minute")
async def login_interno(
    dados: UsuarioInternoLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login de usuário interno - wrapper que usa lógica unificada + auditoria"""
    auditoria = get_auditoria_service(db)
    ip = request.client.host if request.client else None

    try:
        # Chamar lógica unificada
        result = await _unified_login_logic(dados.email, dados.senha, db, request)

        user_info = result.get("user", {})
        user_type = user_info.get("user_type") or user_info.get("tipo", "")

        # Registrar login bem-sucedido
        auditoria.registrar_login(
            usuario_id=user_info.get("id"),
            usuario_tipo=user_type,
            usuario_nome=user_info.get("nome", ""),
            usuario_email=user_info.get("email", ""),
            ip_address=ip,
            user_agent=request.headers.get('user-agent'),
            sucesso=True
        )

        logger.info(f"Login interno bem-sucedido: {user_info.get('email')} ({user_type})")

        # Retornar no formato legado esperado pelo frontend antigo
        return {
            "sucesso": True,
            "usuario": {
                "id": user_info.get("id"),
                "nome": user_info.get("nome"),
                "email": user_info.get("email"),
                "perfil": user_info.get("perfil") or user_type
            }
        }

    except HTTPException as e:
        # Registrar falha de login na auditoria
        auditoria.registrar(
            acao='login',
            usuario_tipo='desconhecido',
            usuario_email=dados.email,
            ip_address=ip,
            sucesso=False,
            erro_mensagem=e.detail
        )
        raise
