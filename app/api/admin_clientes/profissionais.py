"""
Endpoints de profissionais: listar, credenciais, convite.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging
import secrets

from app.database import get_db
from app.api.admin import get_current_admin
from app.services.email_service import get_email_service
from app.services.onboarding_service import gerar_senha_temporaria, hash_senha
from app.api.admin_clientes.schemas import EnviarCredenciaisRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/clientes/{cliente_id}/medicos")
async def listar_medicos_cliente(
    cliente_id: int,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lista médicos e secretárias de um cliente específico"""
    try:
        result = db.execute(
            text("""
                SELECT
                    id, nome, crm, especialidade, email, telefone,
                    ativo, pode_fazer_login, is_admin, criado_em,
                    is_secretaria, pode_ver_financeiro
                FROM medicos
                WHERE cliente_id = :cliente_id
                ORDER BY is_secretaria ASC, is_admin DESC, nome
            """),
            {"cliente_id": cliente_id}
        ).fetchall()

        medicos = []
        secretarias = []
        for row in result:
            item = {
                "id": row[0],
                "nome": row[1],
                "crm": row[2],
                "especialidade": row[3],
                "email": row[4],
                "telefone": row[5],
                "ativo": row[6],
                "pode_fazer_login": row[7],
                "is_admin": row[8],
                "criado_em": row[9].isoformat() if row[9] else None,
                "is_secretaria": row[10],
                "pode_ver_financeiro": row[11]
            }
            if row[10]:  # is_secretaria
                secretarias.append(item)
            else:
                medicos.append(item)

        return {
            "medicos": medicos,
            "secretarias": secretarias,
            "total_medicos": len(medicos),
            "total_secretarias": len(secretarias)
        }

    except Exception as e:
        logger.error(f"[Admin] Erro ao listar médicos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clientes/{cliente_id}/usuarios")
async def listar_usuarios_cliente(
    cliente_id: int,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lista usuários (secretárias) de um cliente específico"""
    try:
        result = db.execute(
            text("""
                SELECT
                    id, nome, email, tipo, telefone, ativo, criado_em
                FROM usuarios
                WHERE cliente_id = :cliente_id
                ORDER BY tipo, nome
            """),
            {"cliente_id": cliente_id}
        ).fetchall()

        usuarios = []
        for row in result:
            usuarios.append({
                "id": row[0],
                "nome": row[1],
                "email": row[2],
                "tipo": row[3],
                "telefone": row[4],
                "ativo": row[5],
                "criado_em": row[6].isoformat() if row[6] else None
            })

        return {"usuarios": usuarios, "total": len(usuarios)}

    except Exception as e:
        logger.error(f"[Admin] Erro ao listar usuários: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clientes/{cliente_id}/profissionais-credenciais")
async def listar_profissionais_para_credenciais(
    cliente_id: int,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lista profissionais elegíveis para receber credenciais"""
    try:
        profissionais = db.execute(
            text("""
                SELECT id, nome, email, is_secretaria, especialidade, is_admin
                FROM medicos
                WHERE cliente_id = :cliente_id
                  AND ativo = true
                  AND email IS NOT NULL
                  AND pode_fazer_login = true
                ORDER BY is_admin DESC, is_secretaria ASC, nome
            """),
            {"cliente_id": cliente_id}
        ).fetchall()

        return {
            "profissionais": [
                {
                    "id": p[0],
                    "nome": p[1],
                    "email": p[2],
                    "is_secretaria": p[3],
                    "especialidade": p[4],
                    "is_admin": p[5],
                    "tipo": "Secretária" if p[3] else ("Admin" if p[5] else "Médico(a)")
                }
                for p in profissionais
            ]
        }
    except Exception as e:
        logger.error(f"[Admin] Erro ao listar profissionais: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clientes/{cliente_id}/enviar-credenciais")
async def enviar_credenciais(
    cliente_id: int,
    dados: Optional[EnviarCredenciaisRequest] = None,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Gera novas senhas temporárias e envia credenciais de acesso.
    Se profissional_ids for fornecido, envia apenas para os selecionados.
    Se não for fornecido, envia para todos os profissionais ativos.
    """
    try:
        # 1. Validar cliente existe, status ativo e ativo=true
        cliente = db.execute(
            text("SELECT id, nome, subdomain, status, ativo FROM clientes WHERE id = :id"),
            {"id": cliente_id}
        ).fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        if cliente[3] != 'ativo' or not cliente[4]:
            raise HTTPException(
                status_code=400,
                detail="Cliente precisa estar ativo para enviar credenciais"
            )

        nome_clinica = cliente[1]
        subdomain = cliente[2]
        login_url = f"https://{subdomain}.horariointeligente.com.br/static/login.html"

        # 2. Buscar profissionais ativos com email
        if dados and dados.profissional_ids:
            # Buscar apenas os selecionados
            placeholders = ','.join([f':id_{i}' for i in range(len(dados.profissional_ids))])
            params = {"cliente_id": cliente_id}
            params.update({f"id_{i}": pid for i, pid in enumerate(dados.profissional_ids)})

            profissionais = db.execute(
                text(f"""
                    SELECT id, nome, email, is_secretaria
                    FROM medicos
                    WHERE cliente_id = :cliente_id
                      AND id IN ({placeholders})
                      AND ativo = true
                      AND email IS NOT NULL
                      AND pode_fazer_login = true
                """),
                params
            ).fetchall()
        else:
            # Buscar todos
            profissionais = db.execute(
                text("""
                    SELECT id, nome, email, is_secretaria
                    FROM medicos
                    WHERE cliente_id = :cliente_id
                      AND ativo = true
                      AND email IS NOT NULL
                      AND pode_fazer_login = true
                """),
                {"cliente_id": cliente_id}
            ).fetchall()

        if not profissionais:
            raise HTTPException(
                status_code=400,
                detail="Nenhum profissional selecionado ou elegível encontrado"
            )

        # 3. Gerar novas senhas e atualizar no banco
        credenciais_lista = []
        for prof in profissionais:
            senha_temp = gerar_senha_temporaria()
            senha_hash_val = hash_senha(senha_temp)

            db.execute(
                text("""
                    UPDATE medicos
                    SET senha = :senha, email_verificado = true, atualizado_em = :atualizado_em
                    WHERE id = :id
                """),
                {
                    "senha": senha_hash_val,
                    "id": prof[0],
                    "atualizado_em": datetime.now()
                }
            )

            credenciais_lista.append({
                "id": prof[0],
                "nome": prof[1],
                "email": prof[2],
                "is_secretaria": prof[3],
                "senha_temporaria": senha_temp
            })

        # 4. Commit das senhas antes de enviar emails
        db.commit()

        # 5. Enviar emails
        email_service = get_email_service()
        detalhes = []
        total_enviados = 0
        total_falhas = 0

        for cred in credenciais_lista:
            tipo = "secretaria" if cred["is_secretaria"] else "medico"
            email_enviado = email_service.send_credenciais_acesso(
                to_email=cred["email"],
                to_name=cred["nome"],
                login_url=login_url,
                email_login=cred["email"],
                senha_temporaria=cred["senha_temporaria"],
                nome_clinica=nome_clinica
            )

            if email_enviado:
                total_enviados += 1
            else:
                total_falhas += 1

            detalhes.append({
                "nome": cred["nome"],
                "email": cred["email"],
                "tipo": tipo,
                "email_enviado": email_enviado
            })

        # 6. Atualizar credenciais_enviadas_em no cliente
        agora = datetime.now()
        db.execute(
            text("UPDATE clientes SET credenciais_enviadas_em = :agora, atualizado_em = :agora WHERE id = :id"),
            {"agora": agora, "id": cliente_id}
        )
        db.commit()

        logger.info(f"[Admin] Credenciais enviadas para cliente {cliente_id}: {total_enviados} OK, {total_falhas} falhas")

        return {
            "success": True,
            "total_enviados": total_enviados,
            "total_falhas": total_falhas,
            "credenciais_enviadas_em": agora.isoformat(),
            "detalhes": detalhes
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Admin] Erro ao enviar credenciais: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao enviar credenciais: {str(e)}")


@router.post("/medicos/{medico_id}/enviar-convite")
async def enviar_convite_profissional(
    medico_id: int,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Envia convite por email para profissional completar cadastro e criar senha"""
    try:
        # Buscar dados do medico
        medico = db.execute(
            text("""
                SELECT m.id, m.nome, m.email, m.cliente_id, m.pode_fazer_login,
                       c.nome as cliente_nome, c.subdomain
                FROM medicos m
                JOIN clientes c ON c.id = m.cliente_id
                WHERE m.id = :id
            """),
            {"id": medico_id}
        ).fetchone()

        if not medico:
            raise HTTPException(status_code=404, detail="Profissional nao encontrado")

        if medico[4]:  # pode_fazer_login
            raise HTTPException(status_code=400, detail="Este profissional ja possui acesso ao sistema")

        # Gerar token de ativacao
        token = secrets.token_urlsafe(48)
        expira_em = datetime.now() + timedelta(days=7)

        # Salvar token no medico (reusar campo de verificacao de email)
        db.execute(
            text("""
                UPDATE medicos SET
                    token_verificacao = :token,
                    token_verificacao_expira = :expira_em,
                    atualizado_em = :atualizado_em
                WHERE id = :id
            """),
            {
                "token": token,
                "expira_em": expira_em,
                "atualizado_em": datetime.now(),
                "id": medico_id
            }
        )
        db.commit()

        # Montar link de ativacao
        base_url = f"https://{medico[6]}.horariointeligente.com.br"
        link_ativacao = f"{base_url}/static/ativar-profissional.html?token={token}"

        # Enviar email
        email_service = get_email_service()
        enviado = email_service.send_convite_profissional(
            to_email=medico[2],
            to_name=medico[1],
            clinica_nome=medico[5],
            activation_link=link_ativacao
        )

        if not enviado:
            logger.warning(f"[Setup] Falha ao enviar email de convite para {medico[2]}")

        logger.info(f"[Setup] Convite enviado para profissional {medico_id} ({medico[2]})")

        return {
            "success": True,
            "message": f"Convite enviado para {medico[2]}",
            "expira_em": expira_em.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Setup] Erro ao enviar convite: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao enviar convite")
