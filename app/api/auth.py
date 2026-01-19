from fastapi import APIRouter, HTTPException, Form, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
from typing import Optional

from app.database import get_db

# Rate Limiting - importar do main
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
security = HTTPBearer()

# Rate Limiter para endpoints de autenticação
# 5 tentativas por minuto por IP (proteção contra brute force)
limiter = Limiter(key_func=get_remote_address)

# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY", "sua-chave-secreta-super-segura-aqui-123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class LoginRequest(BaseModel):
    username: str
    password: str

def create_access_token(data: dict):
    """Cria um token JWT"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # IMPORTANTE: cliente_id deve estar em data
    if "cliente_id" not in to_encode:
        raise ValueError("cliente_id é obrigatório no JWT")
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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

    user_id = payload.get("user_id")
    user_type = payload.get("user_type")

    if not user_id or not user_type:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Buscar usuário no banco
    if user_type == "medico":
        result = db.execute(text("""
            SELECT id, nome, email, especialidade, crm, telefone
            FROM medicos
            WHERE id = :user_id AND ativo = true
        """), {"user_id": user_id})
    elif user_type == "secretaria":
        result = db.execute(text("""
            SELECT id, nome, email, telefone, 'Secretária' as especialidade, '' as crm
            FROM usuarios
            WHERE id = :user_id AND ativo = true AND tipo = 'secretaria'
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
        "cliente_id": payload.get("cliente_id")  # IMPORTANTE: Adicionar cliente_id do token
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


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")  # Máximo 5 tentativas por minuto por IP
async def login(
    request: Request,  # Necessário para rate limiting
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Login de médico ou secretária (protegido contra brute force)"""
    try:
        # Tentar login como médico
        result = db.execute(text("""
            SELECT m.id, m.nome, m.email, m.especialidade, m.crm, m.telefone, m.senha,
                   m.cliente_id, m.email_verificado
            FROM medicos m
            WHERE m.email = :email AND m.ativo = true
        """), {"email": username})

        user = result.fetchone()
        user_type = "medico"
        cliente_id = None
        email_verificado = True  # Default para usuários existentes

        # Se não for médico, tentar como secretária
        if not user:
            result = db.execute(text("""
                SELECT u.id, u.nome, u.email, u.telefone, u.senha, 'secretaria' as tipo,
                       u.cliente_id, u.email_verificado
                FROM usuarios u
                WHERE u.email = :email AND u.ativo = true AND u.tipo = 'secretaria'
            """), {"email": username})
            user = result.fetchone()
            user_type = "secretaria"

        # Verificar se usuário existe e senha está correta
        if not user or not verify_password(password, user.senha if hasattr(user, 'senha') else None):
            # SEGURANÇA: Credenciais hardcoded removidas - usar apenas banco de dados
            raise HTTPException(status_code=401, detail="Email ou senha incorretos")
        else:
            # Verificar se email foi verificado
            email_verificado = getattr(user, 'email_verificado', True)
            if email_verificado is None:
                email_verificado = True  # Usuários antigos são considerados verificados

        # Bloquear login se email não verificado
        if not email_verificado:
            raise HTTPException(
                status_code=403,
                detail="Email não verificado. Verifique sua caixa de entrada ou solicite um novo email de verificação."
            )

        # Pegar cliente_id do usuário
        if not cliente_id:
            cliente_id = user.cliente_id if hasattr(user, 'cliente_id') else 1

        # Criar token com cliente_id (MULTI-TENANT)
        token_data = {
            "user_id": user.id,
            "user_type": user_type,
            "email": user.email,
            "cliente_id": cliente_id  # NOVO - essencial para multi-tenant
        }
        access_token = create_access_token(token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "nome": user.nome,
                "email": user.email,
                "tipo": user_type,
                "especialidade": user.especialidade if hasattr(user, 'especialidade') else "Administração",
                "crm": user.crm if hasattr(user, 'crm') else None,
                "telefone": user.telefone if hasattr(user, 'telefone') else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no login: {str(e)}")

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
        "user_id": payload.get("user_id"),
        "user_type": payload.get("user_type"),
        "email": payload.get("email")
    }
