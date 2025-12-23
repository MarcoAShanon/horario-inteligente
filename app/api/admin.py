"""
API Administrativa - Painel Admin
Endpoints exclusivos para super administradores
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional, List
import logging
import bcrypt
import jwt
import os

from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/admin", tags=["Admin"])
logger = logging.getLogger(__name__)

# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas


# ==================== AUTENTICAÇÃO ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha está correta"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_admin_token(admin_id: int, email: str) -> str:
    """Cria token JWT para admin"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "admin_id": admin_id,
        "email": email,
        "is_super_admin": True,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_admin(request: Request, db: Session = Depends(get_db)):
    """Dependency para obter admin autenticado"""
    # Verificar se está no subdomínio admin
    is_admin = getattr(request.state, 'is_admin', False)
    logger.debug(f"DEBUG get_current_admin: is_admin={is_admin}")

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso permitido apenas via admin.horariointeligente.com.br (is_admin={is_admin})"
        )

    # Extrair token do header
    auth_header = request.headers.get('Authorization') or request.headers.get('authorization')
    logger.debug(f"DEBUG get_current_admin: auth_header={auth_header[:50] if auth_header else None}")

    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token não fornecido (auth_header present: {bool(auth_header)})"
        )

    token = auth_header.split(' ')[1]

    # Verificar se é token do novo sistema (usuarios_internos)
    if token.startswith('interno_'):
        try:
            user_id = int(token.replace('interno_', ''))
            result = db.execute(
                text("""
                    SELECT id, nome, email, perfil, ativo
                    FROM usuarios_internos
                    WHERE id = :id AND perfil IN ('admin', 'financeiro', 'suporte')
                """),
                {"id": user_id}
            ).fetchone()

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário interno não encontrado"
                )

            if not result[4]:  # ativo
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Conta administrativa desativada"
                )

            return {
                "id": result[0],
                "nome": result[1],
                "email": result[2],
                "perfil": result[3],
                "ativo": result[4]
            }
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

    # Token JWT legado (super_admins)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id = payload.get('admin_id')
        is_super_admin = payload.get('is_super_admin', False)

        if not admin_id or not is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

        # Buscar admin no banco
        result = db.execute(
            text("SELECT id, nome, email, ativo FROM super_admins WHERE id = :id"),
            {"id": admin_id}
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin não encontrado"
            )

        if not result[3]:  # ativo
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conta administrativa desativada"
            )

        return {
            "id": result[0],
            "nome": result[1],
            "email": result[2],
            "ativo": result[3]
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
async def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login de super administrador"""
    try:
        # Buscar admin por email
        result = db.execute(
            text("SELECT id, nome, email, senha, ativo FROM super_admins WHERE email = :email"),
            {"email": form_data.username}
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )

        admin_id, nome, email, senha_hash, ativo = result

        # Verificar se está ativo
        if not ativo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conta administrativa desativada"
            )

        # Verificar senha
        if not verify_password(form_data.password, senha_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )

        # Criar token
        token = create_admin_token(admin_id, email)

        logger.info(f"✅ Admin login bem-sucedido: {email}")

        return {
            "access_token": token,
            "token_type": "bearer",
            "admin": {
                "id": admin_id,
                "nome": nome,
                "email": email
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no login admin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao fazer login"
        )


@router.get("/auth/me")
async def get_admin_info(admin = Depends(get_current_admin)):
    """Retorna informações do admin autenticado"""
    return admin


@router.get("/test")
async def test_admin_access(request: Request):
    """Endpoint de teste para debug"""
    return {
        "subdomain": getattr(request.state, 'subdomain', 'not_set'),
        "is_admin": getattr(request.state, 'is_admin', False),
        "cliente_id": getattr(request.state, 'cliente_id', 'not_set'),
        "headers": dict(request.headers)
    }


# ==================== DASHBOARD ====================

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Estatísticas globais do sistema"""
    try:
        # Total de clientes
        total_clientes = db.execute(
            text("SELECT COUNT(*) FROM clientes WHERE ativo = true")
        ).scalar()

        # Total de médicos
        total_medicos = db.execute(
            text("SELECT COUNT(*) FROM medicos WHERE ativo = true")
        ).scalar()

        # Total de pacientes
        total_pacientes = db.execute(
            text("SELECT COUNT(*) FROM pacientes")
        ).scalar()

        # Total de agendamentos (último mês)
        agendamentos_mes = db.execute(
            text("""
                SELECT COUNT(*) FROM agendamentos
                WHERE data_hora >= NOW() - INTERVAL '30 days'
            """)
        ).scalar()

        # Clientes criados recentemente (últimos 7 dias)
        novos_clientes = db.execute(
            text("""
                SELECT COUNT(*) FROM clientes
                WHERE criado_em >= NOW() - INTERVAL '7 days'
            """)
        ).scalar()

        return {
            "total_clientes": total_clientes or 0,
            "total_medicos": total_medicos or 0,
            "total_pacientes": total_pacientes or 0,
            "agendamentos_mes": agendamentos_mes or 0,
            "novos_clientes_semana": novos_clientes or 0
        }

    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar estatísticas"
        )


# ==================== CLIENTES ====================

@router.get("/clientes")
async def listar_clientes(
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """Lista todos os clientes"""
    try:
        result = db.execute(
            text("""
                SELECT
                    id, nome, subdomain, email, telefone,
                    plano, ativo, whatsapp_numero,
                    criado_em, atualizado_em
                FROM clientes
                ORDER BY criado_em DESC
                LIMIT :limit OFFSET :skip
            """),
            {"limit": limit, "skip": skip}
        ).fetchall()

        clientes = []
        for row in result:
            clientes.append({
                "id": row[0],
                "nome": row[1],
                "subdomain": row[2],
                "email": row[3],
                "telefone": row[4],
                "plano": row[5],
                "ativo": row[6],
                "whatsapp_numero": row[7],
                "criado_em": row[8].isoformat() if row[8] else None,
                "atualizado_em": row[9].isoformat() if row[9] else None,
                "url": f"https://{row[2]}.horariointeligente.com.br"
            })

        return clientes

    except Exception as e:
        logger.error(f"Erro ao listar clientes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar clientes"
        )


@router.get("/clientes/{cliente_id}")
async def obter_cliente(
    cliente_id: int,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtém detalhes de um cliente específico"""
    try:
        result = db.execute(
            text("""
                SELECT
                    c.id, c.nome, c.subdomain, c.email, c.telefone,
                    c.plano, c.ativo, c.whatsapp_numero, c.whatsapp_instance,
                    c.criado_em, c.atualizado_em,
                    COUNT(DISTINCT m.id) as total_medicos,
                    COUNT(DISTINCT p.id) as total_pacientes,
                    COUNT(DISTINCT a.id) as total_agendamentos
                FROM clientes c
                LEFT JOIN medicos m ON m.cliente_id = c.id
                LEFT JOIN pacientes p ON p.cliente_id = c.id
                LEFT JOIN agendamentos a ON a.paciente_id = p.id
                WHERE c.id = :id
                GROUP BY c.id
            """),
            {"id": cliente_id}
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        return {
            "id": result[0],
            "nome": result[1],
            "subdomain": result[2],
            "email": result[3],
            "telefone": result[4],
            "plano": result[5],
            "ativo": result[6],
            "whatsapp_numero": result[7],
            "whatsapp_instance": result[8],
            "criado_em": result[9].isoformat() if result[9] else None,
            "atualizado_em": result[10].isoformat() if result[10] else None,
            "total_medicos": result[11],
            "total_pacientes": result[12],
            "total_agendamentos": result[13],
            "url": f"https://{result[2]}.horariointeligente.com.br"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter cliente: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter cliente"
        )
