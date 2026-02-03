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

# Rate Limiting - proteção contra brute force
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/admin", tags=["Admin"])
logger = logging.getLogger(__name__)

# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("ERRO CRITICO: SECRET_KEY nao configurada. Defina a variavel de ambiente SECRET_KEY no arquivo .env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hora


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

    # Caminho 1: Token do sistema usuarios_internos (string "interno_X")
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

    # Caminho 2 e 3: Decodificar JWT
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Caminho 2: Token unificado (tem source_table)
        source_table = payload.get('source_table')
        if source_table:
            user_type = payload.get('user_type')
            raw_sub = payload.get('sub') or payload.get('user_id')
            user_id = int(raw_sub) if raw_sub is not None else None

            # Validar que é um tipo admin
            if user_type not in ('admin', 'financeiro', 'suporte'):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso restrito a administradores"
                )

            # Buscar na tabela correta
            if source_table == 'usuarios_internos':
                result = db.execute(
                    text("""
                        SELECT id, nome, email, perfil, ativo
                        FROM usuarios_internos
                        WHERE id = :id AND perfil IN ('admin', 'financeiro', 'suporte')
                    """),
                    {"id": user_id}
                ).fetchone()
            elif source_table == 'super_admins':
                result = db.execute(
                    text("SELECT id, nome, email, 'admin' as perfil, ativo FROM super_admins WHERE id = :id"),
                    {"id": user_id}
                ).fetchone()
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tipo de usuário sem permissão admin"
                )

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Admin não encontrado"
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

        # Caminho 3: Token JWT legado (super_admins - tem admin_id)
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
@limiter.limit("5/minute")  # Máximo 5 tentativas por minuto por IP
async def admin_login(
    request: Request,  # Necessário para rate limiting
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login de super administrador (protegido contra brute force)"""
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
        # Total de clientes (excluir demo)
        total_clientes = db.execute(
            text("SELECT COUNT(*) FROM clientes WHERE ativo = true AND is_demo = false")
        ).scalar()

        # Total de médicos (excluir demo)
        total_medicos = db.execute(
            text("""
                SELECT COUNT(*) FROM medicos m
                JOIN clientes c ON m.cliente_id = c.id
                WHERE m.ativo = true AND c.is_demo = false
            """)
        ).scalar()

        # Total de pacientes (excluir demo)
        total_pacientes = db.execute(
            text("""
                SELECT COUNT(*) FROM pacientes p
                JOIN clientes c ON p.cliente_id = c.id
                WHERE c.is_demo = false
            """)
        ).scalar()

        # Total de agendamentos (último mês) - excluir cancelado, remarcado, faltou e demo
        agendamentos_mes = db.execute(
            text("""
                SELECT COUNT(*) FROM agendamentos a
                WHERE a.data_hora >= NOW() - INTERVAL '30 days'
                AND a.status NOT IN ('cancelado', 'remarcado', 'faltou')
                AND a.medico_id NOT IN (
                    SELECT m.id FROM medicos m
                    JOIN clientes c ON m.cliente_id = c.id
                    WHERE c.is_demo = true
                )
            """)
        ).scalar()

        # Clientes criados recentemente (últimos 7 dias, excluir demo)
        novos_clientes = db.execute(
            text("""
                SELECT COUNT(*) FROM clientes
                WHERE criado_em >= NOW() - INTERVAL '7 days'
                AND is_demo = false
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
    limit: int = 50,
    status_filter: Optional[str] = None
):
    """Lista todos os clientes, com filtro opcional por status"""
    try:
        query = """
            SELECT
                id, nome, subdomain, email, telefone,
                plano, ativo, whatsapp_numero,
                criado_em, atualizado_em, status
            FROM clientes
            WHERE is_demo = false
        """
        params = {"limit": limit, "skip": skip}

        if status_filter:
            query += " AND status = :status_filter"
            params["status_filter"] = status_filter

        query += " ORDER BY criado_em DESC LIMIT :limit OFFSET :skip"

        result = db.execute(text(query), params).fetchall()

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
                "url": f"https://{row[2]}.horariointeligente.com.br",
                "status": row[10]
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
                    COUNT(DISTINCT CASE WHEN a.status NOT IN ('cancelado', 'remarcado', 'faltou') THEN a.id END) as total_agendamentos,
                    c.credenciais_enviadas_em,
                    c.status,
                    c.endereco,
                    c.cnpj,
                    c.tipo_consultorio,
                    c.qtd_medicos_adicionais,
                    c.necessita_secretaria
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
            "credenciais_enviadas_em": result[14].isoformat() if result[14] else None,
            "status": result[15],
            "endereco": result[16],
            "cnpj": result[17],
            "tipo_consultorio": result[18],
            "qtd_medicos_adicionais": result[19],
            "necessita_secretaria": result[20],
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
