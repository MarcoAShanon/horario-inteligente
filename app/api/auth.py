from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
import logging
from typing import Optional

from app.database import get_db

# Rate Limiting - importar do main
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

# Rate Limiter para endpoints de autenticação
# 5 tentativas por minuto por IP (proteção contra brute force)
limiter = Limiter(key_func=get_remote_address)

# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("ERRO CRÍTICO: SECRET_KEY não configurada. Defina a variável de ambiente SECRET_KEY no arquivo .env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hora
REFRESH_TOKEN_EXPIRE_MINUTES = 480  # 8 horas para refresh

class UnifiedLoginRequest(BaseModel):
    email: str
    senha: str


def create_access_token(data: dict):
    """Cria um token JWT - aceita cliente_id None para admin/parceiro"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # cliente_id é opcional (None para admin/parceiro)
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_unified_token(user_data: dict, token_type: str = "access") -> str:
    """
    Cria token JWT unificado para qualquer tipo de usuário.

    Campos padrão: sub, email, nome, user_type, source_table, token_type, exp
    Campos condicionais:
      - medico/secretaria: cliente_id, is_secretaria, medico_vinculado_id
      - admin/financeiro/suporte: perfil, is_super_admin
      - parceiro: parceiro_id
    """
    payload = {
        "sub": user_data["id"],
        "email": user_data["email"],
        "nome": user_data["nome"],
        "user_type": user_data["user_type"],
        "source_table": user_data["source_table"],
        "token_type": token_type,
        # Campos para compatibilidade retroativa
        "user_id": user_data["id"],
    }

    # Campos condicionais por tipo
    if user_data["user_type"] in ("medico", "secretaria"):
        payload["cliente_id"] = user_data.get("cliente_id")
        payload["is_secretaria"] = user_data.get("is_secretaria", False)
        payload["medico_vinculado_id"] = user_data.get("medico_vinculado_id")
    elif user_data["user_type"] in ("admin", "financeiro", "suporte"):
        payload["perfil"] = user_data.get("perfil")
        payload["is_super_admin"] = user_data.get("is_super_admin", False)
        payload["cliente_id"] = user_data.get("cliente_id")
    elif user_data["user_type"] == "parceiro":
        payload["parceiro_id"] = user_data["id"]

    # Expiração
    if token_type == "refresh":
        expire = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload["exp"] = expire

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    """Verifica e decodifica o token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Dependency para obter o usuário atual do token"""
    token = credentials.credentials
    payload = verify_token(token)

    # Detectar token unificado (tem source_table)
    source_table = payload.get("source_table")

    if source_table:
        user_type = payload.get("user_type")
        user_id = payload.get("sub") or payload.get("user_id")

        # Parceiro não pode acessar endpoints de cliente
        if source_table == "parceiros_comerciais":
            raise HTTPException(status_code=403, detail="Acesso não permitido para parceiros neste endpoint")

        if user_type in ("medico", "secretaria"):
            if user_type == "secretaria":
                result = db.execute(text("""
                    SELECT id, nome, email, 'Secretária' as especialidade, '' as crm, telefone, medico_vinculado_id
                    FROM medicos
                    WHERE id = :user_id AND ativo = true AND is_secretaria = true
                """), {"user_id": user_id})
            else:
                result = db.execute(text("""
                    SELECT id, nome, email, especialidade, crm, telefone, medico_vinculado_id
                    FROM medicos
                    WHERE id = :user_id AND ativo = true AND is_secretaria = false
                """), {"user_id": user_id})
        elif user_type in ("admin", "financeiro", "suporte"):
            if source_table == "usuarios_internos":
                result = db.execute(text("""
                    SELECT id, nome, email, 'Admin' as especialidade, '' as crm, telefone, NULL as medico_vinculado_id
                    FROM usuarios_internos
                    WHERE id = :user_id AND ativo = true
                """), {"user_id": user_id})
            else:
                result = db.execute(text("""
                    SELECT id, nome, email, 'Admin' as especialidade, '' as crm, telefone, NULL as medico_vinculado_id
                    FROM super_admins
                    WHERE id = :user_id AND ativo = true
                """), {"user_id": user_id})
        else:
            raise HTTPException(status_code=401, detail="Tipo de usuário inválido")

        user = result.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")

        return {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "tipo": user_type,
            "especialidade": user.especialidade if hasattr(user, 'especialidade') else None,
            "crm": user.crm if hasattr(user, 'crm') else None,
            "telefone": user.telefone if hasattr(user, 'telefone') else None,
            "cliente_id": payload.get("cliente_id"),
            "is_secretaria": payload.get("is_secretaria", False),
            "medico_vinculado_id": user.medico_vinculado_id if hasattr(user, 'medico_vinculado_id') else None
        }

    # Caminho legado (tokens antigos sem source_table)
    user_id = payload.get("user_id")
    user_type = payload.get("user_type")

    if not user_id or not user_type:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Buscar usuário no banco
    if user_type == "medico":
        result = db.execute(text("""
            SELECT id, nome, email, especialidade, crm, telefone, medico_vinculado_id
            FROM medicos
            WHERE id = :user_id AND ativo = true AND is_secretaria = false
        """), {"user_id": user_id})
    elif user_type == "secretaria":
        # Secretárias também estão na tabela medicos com is_secretaria=true
        result = db.execute(text("""
            SELECT id, nome, email, 'Secretária' as especialidade, '' as crm, telefone, medico_vinculado_id
            FROM medicos
            WHERE id = :user_id AND ativo = true AND is_secretaria = true
        """), {"user_id": user_id})
    elif user_type == "admin":
        result = db.execute(text("""
            SELECT id, nome, email, 'Admin' as especialidade, '' as crm, telefone, NULL as medico_vinculado_id
            FROM usuarios_internos
            WHERE id = :user_id AND ativo = true
        """), {"user_id": user_id})
    else:
        raise HTTPException(status_code=401, detail="Tipo de usuário inválido")

    user = result.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    return {
        "id": user.id,
        "nome": user.nome,
        "email": user.email,
        "tipo": user_type,
        "especialidade": user.especialidade if hasattr(user, 'especialidade') else None,
        "crm": user.crm if hasattr(user, 'crm') else None,
        "telefone": user.telefone if hasattr(user, 'telefone') else None,
        "cliente_id": payload.get("cliente_id"),  # IMPORTANTE: Adicionar cliente_id do token
        "is_secretaria": payload.get("is_secretaria", False),
        "medico_vinculado_id": user.medico_vinculado_id if hasattr(user, 'medico_vinculado_id') else None
    }

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica senha usando bcrypt.

    SEGURANÇA: Apenas senhas com hash bcrypt são aceitas.
    Senhas em texto plano são rejeitadas.
    """
    if not hashed_password:
        return False

    # Rejeitar senhas que não são hash bcrypt
    if not hashed_password.startswith('$2'):
        return False

    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


async def _unified_login_logic(email: str, password: str, db: Session, request: Request) -> dict:
    """
    Lógica unificada de login. Busca em todas as tabelas de usuários.

    Ordem de busca:
    1. medicos (ativo=true) → tipo medico/secretaria
    2. usuarios_internos (ativo=true) → tipo admin/financeiro/suporte
    3. super_admins (ativo=true) → tipo admin (legado)
    4. parceiros_comerciais (ativo=true) → tipo parceiro

    Retorna dict com access_token, refresh_token, user info, etc.
    """
    try:
        user = None
        user_data = None

        # === 1. Buscar em medicos ===
        result = db.execute(text("""
            SELECT m.id, m.nome, m.email, m.especialidade, m.crm, m.telefone, m.senha,
                   m.cliente_id, m.email_verificado, m.is_secretaria, m.medico_vinculado_id
            FROM medicos m
            WHERE m.email = :email AND m.ativo = true
        """), {"email": email})
        user = result.fetchone()

        if user and verify_password(password, user.senha if hasattr(user, 'senha') else None):
            # Verificar email verificado
            email_verificado = getattr(user, 'email_verificado', True)
            if email_verificado is None:
                email_verificado = True

            if not email_verificado:
                raise HTTPException(
                    status_code=403,
                    detail="Email não verificado. Verifique sua caixa de entrada ou solicite um novo email de verificação."
                )

            is_secretaria = getattr(user, 'is_secretaria', False)
            user_type = "secretaria" if is_secretaria else "medico"
            medico_vinculado_id = user.medico_vinculado_id if hasattr(user, 'medico_vinculado_id') else None
            cliente_id = user.cliente_id if hasattr(user, 'cliente_id') else 1

            user_data = {
                "id": user.id,
                "nome": user.nome,
                "email": user.email,
                "user_type": user_type,
                "source_table": "medicos",
                "cliente_id": cliente_id,
                "is_secretaria": is_secretaria,
                "medico_vinculado_id": medico_vinculado_id,
                "especialidade": user.especialidade if hasattr(user, 'especialidade') else None,
                "crm": user.crm if hasattr(user, 'crm') else None,
                "telefone": user.telefone if hasattr(user, 'telefone') else None,
            }
        else:
            user = None  # Reset para continuar buscando

        # === 2. Buscar em usuarios_internos ===
        if not user_data:
            result = db.execute(text("""
                SELECT u.id, u.nome, u.email, u.telefone, u.senha_hash as senha,
                       u.perfil, u.ativo, u.cliente_id, u.email_verificado
                FROM usuarios_internos u
                WHERE u.email = :email AND u.ativo = true
            """), {"email": email})
            user = result.fetchone()

            if user and verify_password(password, user.senha if hasattr(user, 'senha') else None):
                perfil = user.perfil if hasattr(user, 'perfil') else 'admin'
                user_data = {
                    "id": user.id,
                    "nome": user.nome,
                    "email": user.email,
                    "user_type": perfil,  # admin, financeiro, suporte
                    "source_table": "usuarios_internos",
                    "perfil": perfil,
                    "is_super_admin": False,
                    "cliente_id": user.cliente_id if hasattr(user, 'cliente_id') else None,
                    "telefone": user.telefone if hasattr(user, 'telefone') else None,
                }
            else:
                user = None

        # === 3. Buscar em super_admins ===
        if not user_data:
            result = db.execute(text("""
                SELECT id, nome, email, senha, ativo
                FROM super_admins
                WHERE email = :email AND ativo = true
            """), {"email": email})
            user = result.fetchone()

            if user and verify_password(password, user.senha if hasattr(user, 'senha') else None):
                user_data = {
                    "id": user.id,
                    "nome": user.nome,
                    "email": user.email,
                    "user_type": "admin",
                    "source_table": "super_admins",
                    "perfil": "admin",
                    "is_super_admin": True,
                    "cliente_id": None,
                }
            else:
                user = None

        # === 4. Buscar em parceiros_comerciais ===
        if not user_data:
            result = db.execute(text("""
                SELECT id, nome, email, senha_hash, ativo, status
                FROM parceiros_comerciais
                WHERE email = :email
            """), {"email": email})
            user = result.fetchone()

            if user:
                # Verificar ativação
                if not user.ativo:
                    raise HTTPException(status_code=403, detail="Conta do parceiro desativada")

                if not user.senha_hash:
                    raise HTTPException(status_code=401, detail="Email ou senha incorretos")

                if verify_password(password, user.senha_hash if hasattr(user, 'senha_hash') else None):
                    # Verificar status do parceiro
                    parceiro_status = user.status if hasattr(user, 'status') else 'ativo'
                    if parceiro_status == 'pendente_aprovacao':
                        raise HTTPException(status_code=403, detail="pendente_aprovacao")
                    elif parceiro_status == 'pendente_aceite':
                        raise HTTPException(status_code=403, detail="pendente_ativacao")
                    elif parceiro_status == 'suspenso':
                        raise HTTPException(status_code=403, detail="conta_suspensa")
                    elif parceiro_status == 'inativo':
                        raise HTTPException(status_code=403, detail="conta_inativa")
                    elif parceiro_status != 'ativo':
                        raise HTTPException(status_code=403, detail="Conta do parceiro não está ativa")

                    # Atualizar último login
                    db.execute(
                        text("UPDATE parceiros_comerciais SET ultimo_login = :agora WHERE id = :id"),
                        {"id": user.id, "agora": datetime.now()}
                    )
                    db.commit()

                    user_data = {
                        "id": user.id,
                        "nome": user.nome,
                        "email": user.email,
                        "user_type": "parceiro",
                        "source_table": "parceiros_comerciais",
                        "parceiro_id": user.id,
                    }
                else:
                    user = None

        # === Nenhum usuário encontrado ===
        if not user_data:
            # SEGURANÇA: mensagem genérica sem revelar se email existe
            raise HTTPException(status_code=401, detail="Email ou senha incorretos")

        # === Gerar tokens unificados ===
        access_token = create_unified_token(user_data, "access")
        refresh_token = create_unified_token(user_data, "refresh")

        # Construir resposta do user
        user_response = {
            "id": user_data["id"],
            "nome": user_data["nome"],
            "email": user_data["email"],
            "tipo": user_data["user_type"],
            "user_type": user_data["user_type"],
        }

        # Campos condicionais na resposta
        if user_data["user_type"] in ("medico", "secretaria"):
            user_response["is_secretaria"] = user_data.get("is_secretaria", False)
            user_response["medico_vinculado_id"] = user_data.get("medico_vinculado_id")
            user_response["especialidade"] = user_data.get("especialidade", "")
            user_response["crm"] = user_data.get("crm")
            user_response["telefone"] = user_data.get("telefone")
            user_response["cliente_id"] = user_data.get("cliente_id")
        elif user_data["user_type"] in ("admin", "financeiro", "suporte"):
            user_response["perfil"] = user_data.get("perfil", "admin")
            user_response["is_super_admin"] = user_data.get("is_super_admin", False)
        elif user_data["user_type"] == "parceiro":
            user_response["parceiro_id"] = user_data["id"]

        logger.info(f"Login unificado bem-sucedido: {user_data['email']} (tipo={user_data['user_type']}, tabela={user_data['source_table']})")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user_response,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no login unificado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro no login: {str(e)}")


@router.post("/login")
@limiter.limit("5/minute")  # Máximo 5 tentativas por minuto por IP
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Login unificado - aceita JSON ou form-data.

    JSON: {"email": "...", "senha": "..."}
    Form-data: username=...&password=... (compatibilidade legada)

    Busca em: medicos → usuarios_internos → super_admins → parceiros_comerciais
    """
    content_type = request.headers.get("content-type", "")
    email = ""
    senha = ""

    if "application/json" in content_type:
        # JSON request
        body = await request.json()
        email = body.get("email", "")
        senha = body.get("senha", "")
    else:
        # Form-data (compatibilidade legada)
        try:
            form = await request.form()
            email = form.get("username", "") or form.get("email", "")
            senha = form.get("password", "") or form.get("senha", "")
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de requisição inválido. Envie JSON ou form-data.")

    if not email or not senha:
        raise HTTPException(status_code=400, detail="Email e senha são obrigatórios")

    return await _unified_login_logic(email, senha, db, request)


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_access_token(body: RefreshRequest):
    """Renova o access_token usando um refresh_token válido (unificado)"""
    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=401, detail="Token invalido: nao e um refresh token")

        # Token unificado (tem source_table)
        if payload.get("source_table"):
            user_data = {
                "id": payload.get("sub") or payload.get("user_id"),
                "email": payload.get("email"),
                "nome": payload.get("nome", ""),
                "user_type": payload.get("user_type"),
                "source_table": payload.get("source_table"),
                "cliente_id": payload.get("cliente_id"),
                "is_secretaria": payload.get("is_secretaria", False),
                "medico_vinculado_id": payload.get("medico_vinculado_id"),
                "perfil": payload.get("perfil"),
                "is_super_admin": payload.get("is_super_admin", False),
                "parceiro_id": payload.get("parceiro_id"),
            }
            new_access_token = create_unified_token(user_data, "access")
        else:
            # Token legado (sem source_table)
            token_data = {
                "user_id": payload["user_id"],
                "user_type": payload["user_type"],
                "email": payload["email"],
                "cliente_id": payload.get("cliente_id"),
                "is_secretaria": payload.get("is_secretaria", False),
                "medico_vinculado_id": payload.get("medico_vinculado_id")
            }
            new_access_token = create_access_token(token_data)

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expirado. Faca login novamente.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Refresh token invalido")

@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna dados completos do usuário logado"""
    user_type = current_user.get("tipo")
    user_id = current_user.get("id")

    if user_type == "medico":
        result = db.execute(text("""
            SELECT
                id, nome, email, crm, especialidade,
                telefone, convenios_aceitos, valor_consulta_particular,
                procedimentos, biografia, foto_perfil, ativo
            FROM medicos
            WHERE id = :user_id
        """), {"user_id": user_id}).fetchone()

        if result:
            return {
                **current_user,
                "id": result[0],
                "nome": result[1],
                "email": result[2],
                "crm": result[3],
                "especialidade": result[4],
                "telefone": result[5],
                "convenios_aceitos": result[6],
                "valor_consulta_particular": float(result[7]) if result[7] else None,
                "procedimentos": result[8],
                "biografia": result[9],
                "foto_perfil": result[10],
                "ativo": result[11]
            }

    return current_user

@router.post("/logout")
async def logout():
    """Logout"""
    return {"message": "Logout realizado com sucesso"}

@router.post("/verify-token")
async def verify_user_token(
    authorization: Optional[str] = Header(None)
):
    """Verifica se o token é válido"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")

    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)

    return {
        "valid": True,
        "user_id": payload.get("sub") or payload.get("user_id"),
        "user_type": payload.get("user_type"),
        "email": payload.get("email")
    }
