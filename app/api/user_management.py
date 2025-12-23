"""
APIs de Gestão de Usuários
Cadastro, Recuperação de Senha, Perfil
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import bcrypt
import secrets
import logging
import base64
import re
import json

from app.database import get_db
from app.api.auth import get_current_user
from app.services.email_service import get_email_service

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

class ProcedimentoItem(BaseModel):
    nome: str
    duracao_minutos: int
    valor: float

class RegisterRequest(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    tipo: str  # "medico" ou "secretaria"
    telefone: Optional[str] = None
    telefone_particular: Optional[str] = None

    # Campos específicos para médicos
    crm: Optional[str] = None
    especialidade: Optional[str] = None
    convenios_aceitos: Optional[List[str]] = []
    valor_consulta_particular: Optional[float] = None
    procedimentos: Optional[List[ProcedimentoItem]] = []
    biografia: Optional[str] = None

    # Será preenchido automaticamente baseado no subdomínio
    cliente_id: Optional[int] = None

    @validator('senha')
    def senha_forte(cls, v):
        if len(v) < 6:
            raise ValueError('Senha deve ter no mínimo 6 caracteres')
        return v

    @validator('tipo')
    def tipo_valido(cls, v):
        if v not in ['medico', 'secretaria']:
            raise ValueError('Tipo deve ser "medico" ou "secretaria"')
        return v

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    nova_senha: str

    @validator('nova_senha')
    def senha_forte(cls, v):
        if len(v) < 6:
            raise ValueError('Senha deve ter no mínimo 6 caracteres')
        return v

class UpdateProfileRequest(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    telefone_particular: Optional[str] = None
    especialidade: Optional[str] = None
    convenios_aceitos: Optional[List[str]] = None
    valor_consulta_particular: Optional[float] = None
    procedimentos: Optional[List[ProcedimentoItem]] = None
    biografia: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    senha_atual: str
    nova_senha: str

    @validator('nova_senha')
    def senha_forte(cls, v):
        if len(v) < 6:
            raise ValueError('Senha deve ter no mínimo 6 caracteres')
        return v


# ==================== REGISTRO ====================

@router.post("/auth/register")
async def register_user(
    dados: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Cadastro de novo usuário (médico ou secretária)

    - Valida se email já existe
    - Cria hash da senha
    - Envia email de boas-vindas
    """
    try:
        # Verificar se email já existe
        if dados.tipo == "medico":
            existe = db.execute(text("""
                SELECT id FROM medicos WHERE email = :email
            """), {"email": dados.email}).fetchone()
        else:
            existe = db.execute(text("""
                SELECT id FROM usuarios WHERE email = :email
            """), {"email": dados.email}).fetchone()

        if existe:
            raise HTTPException(
                status_code=400,
                detail="Este email já está cadastrado no sistema"
            )

        # Hash da senha
        senha_hash = bcrypt.hashpw(
            dados.senha.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Cliente padrão (TODO: pegar do subdomínio/contexto)
        cliente_id = dados.cliente_id or 1

        if dados.tipo == "medico":
            # Validar campos obrigatórios para médico
            if not dados.crm or not dados.especialidade:
                raise HTTPException(
                    status_code=400,
                    detail="CRM e Especialidade são obrigatórios para médicos"
                )

            # Converter procedimentos para JSON
            procedimentos_json = [
                {
                    "nome": p.nome,
                    "duracao_minutos": p.duracao_minutos,
                    "valor": p.valor
                }
                for p in (dados.procedimentos or [])
            ]

            # Gerar token de verificação
            token_verificacao = secrets.token_urlsafe(32)
            token_expira = datetime.now(timezone.utc) + timedelta(hours=24)

            # Inserir médico (email_verificado = false)
            convenios_json = json.dumps(dados.convenios_aceitos or [])
            procedimentos_str = json.dumps(procedimentos_json)

            result = db.execute(text("""
                INSERT INTO medicos (
                    cliente_id, nome, email, senha, crm, especialidade,
                    telefone, telefone_particular, convenios_aceitos,
                    valor_consulta_particular, procedimentos, biografia,
                    ativo, email_verificado, token_verificacao, token_verificacao_expira,
                    criado_em, atualizado_em
                ) VALUES (
                    :cliente_id, :nome, :email, :senha, :crm, :especialidade,
                    :telefone, :telefone_particular, CAST(:convenios AS jsonb),
                    :valor_consulta, CAST(:procedimentos AS jsonb), :biografia,
                    true, false, :token_verificacao, :token_expira,
                    NOW(), NOW()
                ) RETURNING id
            """), {
                "cliente_id": cliente_id,
                "nome": dados.nome,
                "email": dados.email,
                "senha": senha_hash,
                "crm": dados.crm,
                "especialidade": dados.especialidade,
                "telefone": dados.telefone,
                "telefone_particular": dados.telefone_particular,
                "convenios": convenios_json,
                "valor_consulta": dados.valor_consulta_particular,
                "procedimentos": procedimentos_str,
                "biografia": dados.biografia,
                "token_verificacao": token_verificacao,
                "token_expira": token_expira
            })

            user_id = result.fetchone()[0]
            user_type = "medico"

        else:  # secretaria
            # Gerar token de verificação
            token_verificacao = secrets.token_urlsafe(32)
            token_expira = datetime.now(timezone.utc) + timedelta(hours=24)

            # Inserir secretária (email_verificado = false)
            result = db.execute(text("""
                INSERT INTO usuarios (
                    cliente_id, nome, email, senha, tipo,
                    telefone, telefone_particular, ativo,
                    email_verificado, token_verificacao, token_verificacao_expira,
                    criado_em, atualizado_em
                ) VALUES (
                    :cliente_id, :nome, :email, :senha, 'secretaria',
                    :telefone, :telefone_particular, true,
                    false, :token_verificacao, :token_expira,
                    NOW(), NOW()
                ) RETURNING id
            """), {
                "cliente_id": cliente_id,
                "nome": dados.nome,
                "email": dados.email,
                "senha": senha_hash,
                "telefone": dados.telefone,
                "telefone_particular": dados.telefone_particular,
                "token_verificacao": token_verificacao,
                "token_expira": token_expira
            })

            user_id = result.fetchone()[0]
            user_type = "secretaria"

        db.commit()

        # Enviar email de verificação
        email_service = get_email_service()
        email_service.send_email_verification(
            to_email=dados.email,
            to_name=dados.nome,
            verification_token=token_verificacao
        )

        logger.info(f"✅ Novo usuário cadastrado (aguardando verificação): {dados.email} ({user_type})")

        return {
            "sucesso": True,
            "mensagem": "Cadastro realizado! Enviamos um email de confirmação para ativar sua conta.",
            "user_id": user_id,
            "tipo": user_type,
            "email_verificado": False
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao registrar usuário: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao criar cadastro: {str(e)}")


# ==================== VERIFICAÇÃO DE EMAIL ====================

class VerifyEmailRequest(BaseModel):
    token: str

@router.post("/auth/verify-email")
async def verify_email(
    dados: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Verifica email do usuário através do token

    - Valida se token existe e não expirou
    - Marca email como verificado
    - Limpa token de verificação
    """
    try:
        # Buscar em médicos
        medico = db.execute(text("""
            SELECT id, nome, email, token_verificacao_expira
            FROM medicos
            WHERE token_verificacao = :token
        """), {"token": dados.token}).fetchone()

        if medico:
            # Verificar se token expirou
            if medico.token_verificacao_expira and medico.token_verificacao_expira.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=400,
                    detail="Token expirado. Solicite um novo email de verificação."
                )

            # Marcar como verificado
            db.execute(text("""
                UPDATE medicos
                SET email_verificado = true,
                    token_verificacao = NULL,
                    token_verificacao_expira = NULL,
                    atualizado_em = NOW()
                WHERE id = :id
            """), {"id": medico.id})

            db.commit()

            # Enviar email de boas-vindas agora que foi verificado
            email_service = get_email_service()
            email_service.send_welcome_email(
                to_email=medico.email,
                to_name=medico.nome,
                user_type="medico"
            )

            logger.info(f"✅ Email verificado: {medico.email}")

            return {
                "sucesso": True,
                "mensagem": "Email verificado com sucesso! Você já pode fazer login.",
                "email": medico.email,
                "nome": medico.nome
            }

        # Buscar em usuários (secretárias)
        usuario = db.execute(text("""
            SELECT id, nome, email, token_verificacao_expira
            FROM usuarios
            WHERE token_verificacao = :token
        """), {"token": dados.token}).fetchone()

        if usuario:
            # Verificar se token expirou
            if usuario.token_verificacao_expira and usuario.token_verificacao_expira.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=400,
                    detail="Token expirado. Solicite um novo email de verificação."
                )

            # Marcar como verificado
            db.execute(text("""
                UPDATE usuarios
                SET email_verificado = true,
                    token_verificacao = NULL,
                    token_verificacao_expira = NULL,
                    atualizado_em = NOW()
                WHERE id = :id
            """), {"id": usuario.id})

            db.commit()

            # Enviar email de boas-vindas
            email_service = get_email_service()
            email_service.send_welcome_email(
                to_email=usuario.email,
                to_name=usuario.nome,
                user_type="secretaria"
            )

            logger.info(f"✅ Email verificado: {usuario.email}")

            return {
                "sucesso": True,
                "mensagem": "Email verificado com sucesso! Você já pode fazer login.",
                "email": usuario.email,
                "nome": usuario.nome
            }

        # Token não encontrado
        raise HTTPException(
            status_code=404,
            detail="Token de verificação inválido ou já utilizado."
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao verificar email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao verificar email: {str(e)}")


@router.post("/auth/resend-verification")
async def resend_verification_email(
    dados: ForgotPasswordRequest,  # Reutiliza o schema que tem apenas email
    db: Session = Depends(get_db)
):
    """
    Reenvia email de verificação

    - Gera novo token
    - Atualiza expiração (24 horas)
    - Envia novo email
    """
    try:
        # Buscar em médicos
        medico = db.execute(text("""
            SELECT id, nome, email, email_verificado
            FROM medicos
            WHERE email = :email
        """), {"email": dados.email}).fetchone()

        if medico:
            if medico.email_verificado:
                return {
                    "sucesso": True,
                    "mensagem": "Este email já foi verificado. Você pode fazer login."
                }

            # Gerar novo token
            novo_token = secrets.token_urlsafe(32)
            token_expira = datetime.now(timezone.utc) + timedelta(hours=24)

            db.execute(text("""
                UPDATE medicos
                SET token_verificacao = :token,
                    token_verificacao_expira = :expira,
                    atualizado_em = NOW()
                WHERE id = :id
            """), {"token": novo_token, "expira": token_expira, "id": medico.id})

            db.commit()

            # Enviar email
            email_service = get_email_service()
            email_service.send_email_verification(
                to_email=medico.email,
                to_name=medico.nome,
                verification_token=novo_token
            )

            logger.info(f"📧 Email de verificação reenviado: {medico.email}")

            return {
                "sucesso": True,
                "mensagem": "Email de verificação reenviado! Verifique sua caixa de entrada."
            }

        # Buscar em usuários
        usuario = db.execute(text("""
            SELECT id, nome, email, email_verificado
            FROM usuarios
            WHERE email = :email
        """), {"email": dados.email}).fetchone()

        if usuario:
            if usuario.email_verificado:
                return {
                    "sucesso": True,
                    "mensagem": "Este email já foi verificado. Você pode fazer login."
                }

            # Gerar novo token
            novo_token = secrets.token_urlsafe(32)
            token_expira = datetime.now(timezone.utc) + timedelta(hours=24)

            db.execute(text("""
                UPDATE usuarios
                SET token_verificacao = :token,
                    token_verificacao_expira = :expira,
                    atualizado_em = NOW()
                WHERE id = :id
            """), {"token": novo_token, "expira": token_expira, "id": usuario.id})

            db.commit()

            # Enviar email
            email_service = get_email_service()
            email_service.send_email_verification(
                to_email=usuario.email,
                to_name=usuario.nome,
                verification_token=novo_token
            )

            logger.info(f"📧 Email de verificação reenviado: {usuario.email}")

            return {
                "sucesso": True,
                "mensagem": "Email de verificação reenviado! Verifique sua caixa de entrada."
            }

        # Email não encontrado - mas não revelamos isso por segurança
        return {
            "sucesso": True,
            "mensagem": "Se este email estiver cadastrado, você receberá um email de verificação."
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao reenviar verificação: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao reenviar email: {str(e)}")


# ==================== RECUPERAÇÃO DE SENHA ====================

@router.post("/auth/forgot-password")
async def forgot_password(
    dados: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Solicita recuperação de senha

    - Gera token único
    - Define expiração (1 hora)
    - Envia email com link
    """
    try:
        # Buscar usuário (médico ou secretária)
        medico = db.execute(text("""
            SELECT id, nome, email FROM medicos WHERE email = :email AND ativo = true
        """), {"email": dados.email}).fetchone()

        secretaria = db.execute(text("""
            SELECT id, nome, email FROM usuarios WHERE email = :email AND ativo = true
        """), {"email": dados.email}).fetchone()

        if not medico and not secretaria:
            # Por segurança, sempre retorna sucesso (não revelar se email existe)
            return {
                "sucesso": True,
                "mensagem": "Se o email existir, você receberá instruções de recuperação"
            }

        # Determinar tabela e dados
        if medico:
            user_id, user_name, user_email = medico
            table = "medicos"
        else:
            user_id, user_name, user_email = secretaria
            table = "usuarios"

        # Gerar token único
        recovery_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)

        # Atualizar no banco
        db.execute(text(f"""
            UPDATE {table}
            SET recovery_token = :token,
                recovery_token_expires = :expires
            WHERE id = :user_id
        """), {
            "token": recovery_token,
            "expires": expires_at,
            "user_id": user_id
        })

        db.commit()

        # Enviar email
        email_service = get_email_service()
        email_service.send_password_recovery(
            to_email=user_email,
            to_name=user_name,
            recovery_token=recovery_token
        )

        logger.info(f"✅ Token de recuperação gerado para: {user_email}")

        return {
            "sucesso": True,
            "mensagem": "Se o email existir, você receberá instruções de recuperação"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao processar recuperação de senha: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao processar solicitação")


@router.post("/auth/reset-password")
async def reset_password(
    dados: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Redefine senha com token válido

    - Valida token
    - Verifica expiração
    - Atualiza senha
    - Invalida token
    """
    try:
        # Buscar token em ambas as tabelas
        medico = db.execute(text("""
            SELECT id, email, recovery_token_expires
            FROM medicos
            WHERE recovery_token = :token AND ativo = true
        """), {"token": dados.token}).fetchone()

        secretaria = db.execute(text("""
            SELECT id, email, recovery_token_expires
            FROM usuarios
            WHERE recovery_token = :token AND ativo = true
        """), {"token": dados.token}).fetchone()

        if not medico and not secretaria:
            raise HTTPException(
                status_code=400,
                detail="Token inválido ou expirado"
            )

        # Determinar tabela e dados
        if medico:
            user_id, user_email, expires_at = medico
            table = "medicos"
        else:
            user_id, user_email, expires_at = secretaria
            table = "usuarios"

        # Verificar expiração
        if expires_at < datetime.now():
            raise HTTPException(
                status_code=400,
                detail="Token expirado. Solicite uma nova recuperação de senha"
            )

        # Hash da nova senha
        nova_senha_hash = bcrypt.hashpw(
            dados.nova_senha.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Atualizar senha e invalidar token
        db.execute(text(f"""
            UPDATE {table}
            SET senha = :senha,
                recovery_token = NULL,
                recovery_token_expires = NULL,
                atualizado_em = NOW()
            WHERE id = :user_id
        """), {
            "senha": nova_senha_hash,
            "user_id": user_id
        })

        db.commit()

        logger.info(f"✅ Senha redefinida para: {user_email}")

        return {
            "sucesso": True,
            "mensagem": "Senha redefinida com sucesso! Você já pode fazer login."
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao redefinir senha: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao redefinir senha")


# ==================== PERFIL ====================

@router.get("/perfil")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna dados do perfil do usuário logado"""
    try:
        user_type = current_user.get("tipo")
        user_id = current_user.get("id")

        if user_type == "medico":
            result = db.execute(text("""
                SELECT
                    id, nome, email, crm, especialidade,
                    telefone, telefone_particular, convenios_aceitos,
                    valor_consulta_particular, procedimentos, biografia,
                    foto_perfil, ativo
                FROM medicos
                WHERE id = :user_id
            """), {"user_id": user_id}).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Usuário não encontrado")

            return {
                "id": result[0],
                "nome": result[1],
                "email": result[2],
                "tipo": "medico",
                "crm": result[3],
                "especialidade": result[4],
                "telefone": result[5],
                "telefone_particular": result[6],
                "convenios_aceitos": result[7],
                "valor_consulta_particular": float(result[8]) if result[8] else None,
                "procedimentos": result[9],
                "biografia": result[10],
                "foto_perfil": result[11],
                "ativo": result[12]
            }

        else:  # secretaria
            result = db.execute(text("""
                SELECT
                    id, nome, email, telefone, telefone_particular,
                    foto_perfil, ativo, tipo
                FROM usuarios
                WHERE id = :user_id
            """), {"user_id": user_id}).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Usuário não encontrado")

            return {
                "id": result[0],
                "nome": result[1],
                "email": result[2],
                "telefone": result[3],
                "telefone_particular": result[4],
                "foto_perfil": result[5],
                "ativo": result[6],
                "tipo": result[7]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar perfil: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar perfil")


@router.put("/perfil")
async def update_profile(
    dados: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza dados do perfil do usuário logado"""
    try:
        user_type = current_user.get("tipo")
        user_id = current_user.get("id")

        if user_type == "medico":
            # Montar query dinamicamente baseado nos campos fornecidos
            updates = []
            params = {"user_id": user_id}

            if dados.nome:
                updates.append("nome = :nome")
                params["nome"] = dados.nome

            if dados.telefone is not None:
                updates.append("telefone = :telefone")
                params["telefone"] = dados.telefone

            if dados.telefone_particular is not None:
                updates.append("telefone_particular = :telefone_particular")
                params["telefone_particular"] = dados.telefone_particular

            if dados.especialidade:
                updates.append("especialidade = :especialidade")
                params["especialidade"] = dados.especialidade

            if dados.convenios_aceitos is not None:
                updates.append("convenios_aceitos = :convenios::jsonb")
                params["convenios"] = str(dados.convenios_aceitos)

            if dados.valor_consulta_particular is not None:
                updates.append("valor_consulta_particular = :valor")
                params["valor"] = dados.valor_consulta_particular

            if dados.procedimentos is not None:
                procedimentos_json = [
                    {
                        "nome": p.nome,
                        "duracao_minutos": p.duracao_minutos,
                        "valor": p.valor
                    }
                    for p in dados.procedimentos
                ]
                updates.append("procedimentos = :procedimentos::jsonb")
                params["procedimentos"] = str(procedimentos_json)

            if dados.biografia is not None:
                updates.append("biografia = :biografia")
                params["biografia"] = dados.biografia

            if updates:
                updates.append("atualizado_em = NOW()")
                query = f"UPDATE medicos SET {', '.join(updates)} WHERE id = :user_id"
                db.execute(text(query), params)
                db.commit()

        else:  # secretaria
            updates = []
            params = {"user_id": user_id}

            if dados.nome:
                updates.append("nome = :nome")
                params["nome"] = dados.nome

            if dados.telefone is not None:
                updates.append("telefone = :telefone")
                params["telefone"] = dados.telefone

            if dados.telefone_particular is not None:
                updates.append("telefone_particular = :telefone_particular")
                params["telefone_particular"] = dados.telefone_particular

            if updates:
                updates.append("atualizado_em = NOW()")
                query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = :user_id"
                db.execute(text(query), params)
                db.commit()

        logger.info(f"✅ Perfil atualizado para user_id={user_id}")

        return {
            "sucesso": True,
            "mensagem": "Perfil atualizado com sucesso!"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar perfil: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao atualizar perfil")


@router.post("/perfil/foto")
async def upload_profile_photo(
    foto_base64: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload de foto de perfil (base64)
    Aceita string base64 da imagem
    """
    try:
        user_type = current_user.get("tipo")
        user_id = current_user.get("id")

        # Validar tamanho (max 2MB)
        if len(foto_base64) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Imagem muito grande. Máximo 2MB"
            )

        # Atualizar no banco
        if user_type == "medico":
            db.execute(text("""
                UPDATE medicos
                SET foto_perfil = :foto, atualizado_em = NOW()
                WHERE id = :user_id
            """), {"foto": foto_base64, "user_id": user_id})
        else:
            db.execute(text("""
                UPDATE usuarios
                SET foto_perfil = :foto, atualizado_em = NOW()
                WHERE id = :user_id
            """), {"foto": foto_base64, "user_id": user_id})

        db.commit()

        logger.info(f"✅ Foto de perfil atualizada para user_id={user_id}")

        return {
            "sucesso": True,
            "mensagem": "Foto atualizada com sucesso!"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao fazer upload de foto: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao fazer upload")


@router.post("/perfil/alterar-senha")
async def change_password(
    dados: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Altera senha do usuário logado

    - Valida senha atual
    - Atualiza para nova senha
    """
    try:
        user_type = current_user.get("tipo")
        user_id = current_user.get("id")

        # Buscar senha atual do banco
        if user_type == "medico":
            result = db.execute(text("""
                SELECT senha FROM medicos WHERE id = :user_id
            """), {"user_id": user_id}).fetchone()
            table = "medicos"
        else:
            result = db.execute(text("""
                SELECT senha FROM usuarios WHERE id = :user_id
            """), {"user_id": user_id}).fetchone()
            table = "usuarios"

        if not result:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        senha_atual_hash = result[0]

        # Verificar se senha atual está correta
        if not bcrypt.checkpw(dados.senha_atual.encode('utf-8'), senha_atual_hash.encode('utf-8')):
            raise HTTPException(
                status_code=400,
                detail="Senha atual incorreta"
            )

        # Hash da nova senha
        nova_senha_hash = bcrypt.hashpw(
            dados.nova_senha.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Atualizar senha
        db.execute(text(f"""
            UPDATE {table}
            SET senha = :senha, atualizado_em = NOW()
            WHERE id = :user_id
        """), {
            "senha": nova_senha_hash,
            "user_id": user_id
        })

        db.commit()

        logger.info(f"✅ Senha alterada para user_id={user_id}")

        return {
            "sucesso": True,
            "mensagem": "Senha alterada com sucesso!"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao alterar senha: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao alterar senha")
