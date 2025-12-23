from fastapi import APIRouter, HTTPException, Form, Depends, Header
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

router = APIRouter()
security = HTTPBearer()

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
    """Verifica senha com bcrypt ou texto simples (legado)"""
    if not hashed_password:
        return False
    # Tentar verificar com bcrypt primeiro
    if hashed_password.startswith('$2'):
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    # Fallback: comparação direta (senhas legadas)
    return plain_password == hashed_password


@router.post("/login", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Login de médico ou secretária"""
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
            # Fallback para credenciais padrão (desenvolvimento)
            if username == "admin@prosaude.com" and password == "admin123":
                # Buscar médico padrão
                result = db.execute(text("""
                    SELECT m.id, m.nome, m.email, m.especialidade, m.crm, m.telefone, m.cliente_id
                    FROM medicos m
                    WHERE m.ativo = true
                    LIMIT 1
                """))
                user = result.fetchone()
                user_type = "secretaria"  # Admin tem permissões de secretária
                cliente_id = user.cliente_id if user else 1
                email_verificado = True  # Admin bypass
            else:
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
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna dados do usuário logado"""
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
