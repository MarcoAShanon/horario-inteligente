"""
Endpoints CRUD: editar cliente, adicionar médico/secretária/usuário, status, plano.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import asyncio

from app.database import get_db
from app.api.admin import get_current_admin
from app.services.telegram_service import alerta_cliente_inativo
from app.services.onboarding_service import (
    gerar_senha_temporaria, hash_senha, verificar_email_disponivel
)
from app.api.admin_clientes.schemas import (
    ClienteUpdate, MedicoAdicionalCreate, SecretariaOnboarding,
    UsuarioCreate, StatusUpdate, PlanoUpdate
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.put("/clientes/{cliente_id}")
async def editar_cliente(
    cliente_id: int,
    dados: ClienteUpdate,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Edita dados de uma clínica existente"""
    try:
        # Verificar se cliente existe
        cliente = db.execute(
            text("SELECT id, nome FROM clientes WHERE id = :id"),
            {"id": cliente_id}
        ).fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        # Montar campos para atualização
        campos = []
        params = {"id": cliente_id, "atualizado_em": datetime.now()}

        if dados.nome_fantasia:
            campos.append("nome = :nome")
            params["nome"] = dados.nome_fantasia

        if dados.razao_social:
            campos.append("cnpj = :cnpj")  # Usando campo cnpj para razao social
            params["cnpj"] = dados.razao_social

        if dados.email:
            campos.append("email = :email")
            params["email"] = dados.email

        if dados.telefone:
            campos.append("telefone = :telefone")
            params["telefone"] = dados.telefone

        if dados.endereco:
            campos.append("endereco = :endereco")
            params["endereco"] = dados.endereco

        if not campos:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

        campos.append("atualizado_em = :atualizado_em")

        query = text(f"UPDATE clientes SET {', '.join(campos)} WHERE id = :id")
        db.execute(query, params)
        db.commit()

        logger.info(f"[Admin] Cliente {cliente_id} atualizado")

        return {"success": True, "message": "Cliente atualizado com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Admin] Erro ao editar cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clientes/{cliente_id}/medicos")
async def adicionar_medico(
    cliente_id: int,
    dados: MedicoAdicionalCreate,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Adiciona médico a uma clínica existente.
    Usado para plano Consultório (múltiplos profissionais).
    """
    try:
        # Verificar cliente
        cliente = db.execute(
            text("SELECT id, nome, plano FROM clientes WHERE id = :id AND ativo = true"),
            {"id": cliente_id}
        ).fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado ou inativo")

        # Verificar email disponível
        if not verificar_email_disponivel(db, dados.email, "medicos"):
            raise HTTPException(
                status_code=400,
                detail=f"Email {dados.email} já está em uso"
            )

        # Contar médicos existentes
        count = db.execute(
            text("SELECT COUNT(*) FROM medicos WHERE cliente_id = :id AND ativo = true"),
            {"id": cliente_id}
        ).scalar()

        # Verificar limite do plano (alertar se passar)
        if cliente[2] == "individual" and count >= 1:
            logger.warning(f"[Admin] Cliente {cliente_id} (Individual) já tem {count} médico(s)")

        # Gerar senha se pode fazer login
        senha_temporaria = None
        senha_hash = None
        if dados.pode_fazer_login:
            senha_temporaria = gerar_senha_temporaria()
            senha_hash = hash_senha(senha_temporaria)

        # Criar médico
        agora = datetime.now()
        result = db.execute(
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
                    :pode_login, :is_admin, true,
                    false, true,
                    :criado_em, :atualizado_em
                )
                RETURNING id
            """),
            {
                "cliente_id": cliente_id,
                "nome": dados.nome,
                "crm": dados.registro_profissional,
                "especialidade": dados.especialidade,
                "email": dados.email,
                "telefone": dados.telefone,
                "senha": senha_hash,
                "pode_login": dados.pode_fazer_login,
                "is_admin": dados.is_admin,
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        medico_id = result.fetchone()[0]
        db.commit()

        logger.info(f"[Admin] Médico {dados.nome} adicionado ao cliente {cliente_id}")

        response = {
            "success": True,
            "medico": {
                "id": medico_id,
                "nome": dados.nome,
                "email": dados.email,
                "especialidade": dados.especialidade
            }
        }

        if senha_temporaria:
            response["credenciais"] = {
                "email": dados.email,
                "senha_temporaria": senha_temporaria
            }

        return response

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Admin] Erro ao adicionar médico: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clientes/{cliente_id}/secretarias")
async def adicionar_secretaria(
    cliente_id: int,
    dados: SecretariaOnboarding,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Adiciona secretária a uma clínica existente.
    Secretárias são criadas na tabela medicos com is_secretaria=true.
    """
    try:
        # Verificar cliente
        cliente = db.execute(
            text("SELECT id, nome FROM clientes WHERE id = :id AND ativo = true"),
            {"id": cliente_id}
        ).fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado ou inativo")

        # Verificar email disponível
        if not verificar_email_disponivel(db, dados.email, "medicos"):
            raise HTTPException(
                status_code=400,
                detail=f"Email {dados.email} já está em uso"
            )

        # Gerar senha
        senha_temporaria = gerar_senha_temporaria()
        senha_hash = hash_senha(senha_temporaria)

        # Criar secretária na tabela medicos
        agora = datetime.now()
        result = db.execute(
            text("""
                INSERT INTO medicos (
                    cliente_id, nome, crm, especialidade,
                    email, telefone, senha, ativo,
                    pode_fazer_login, is_admin, email_verificado,
                    is_secretaria, pode_ver_financeiro,
                    criado_em, atualizado_em
                ) VALUES (
                    :cliente_id, :nome, 'N/A', 'Secretária',
                    :email, :telefone, :senha, true,
                    true, false, true,
                    true, false,
                    :criado_em, :atualizado_em
                )
                RETURNING id
            """),
            {
                "cliente_id": cliente_id,
                "nome": dados.nome,
                "email": dados.email,
                "telefone": dados.telefone,
                "senha": senha_hash,
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        secretaria_id = result.fetchone()[0]
        db.commit()

        logger.info(f"[Admin] Secretária {dados.nome} adicionada ao cliente {cliente_id}")

        return {
            "success": True,
            "secretaria": {
                "id": secretaria_id,
                "nome": dados.nome,
                "email": dados.email,
                "tipo": "secretaria"
            },
            "credenciais": {
                "email": dados.email,
                "senha_temporaria": senha_temporaria
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Admin] Erro ao adicionar secretária: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clientes/{cliente_id}/usuarios")
async def criar_usuario(
    cliente_id: int,
    dados: UsuarioCreate,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Cria usuário (secretária/admin) para uma clínica.
    """
    try:
        # Verificar cliente
        cliente = db.execute(
            text("SELECT id, nome FROM clientes WHERE id = :id AND ativo = true"),
            {"id": cliente_id}
        ).fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado ou inativo")

        # Verificar email disponível
        if not verificar_email_disponivel(db, dados.email, "usuarios"):
            raise HTTPException(
                status_code=400,
                detail=f"Email {dados.email} já está em uso"
            )

        # Gerar senha temporária
        senha_temporaria = gerar_senha_temporaria()
        senha_hash = hash_senha(senha_temporaria)

        # Criar usuário
        agora = datetime.now()
        result = db.execute(
            text("""
                INSERT INTO usuarios (
                    cliente_id, nome, email, senha, tipo,
                    telefone, ativo, criado_em, atualizado_em
                ) VALUES (
                    :cliente_id, :nome, :email, :senha, :tipo,
                    :telefone, true, :criado_em, :atualizado_em
                )
                RETURNING id
            """),
            {
                "cliente_id": cliente_id,
                "nome": dados.nome,
                "email": dados.email,
                "senha": senha_hash,
                "tipo": dados.tipo,
                "telefone": dados.telefone,
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        usuario_id = result.fetchone()[0]
        db.commit()

        logger.info(f"[Admin] Usuário {dados.nome} ({dados.tipo}) criado para cliente {cliente_id}")

        return {
            "success": True,
            "usuario": {
                "id": usuario_id,
                "nome": dados.nome,
                "email": dados.email,
                "tipo": dados.tipo
            },
            "credenciais": {
                "email": dados.email,
                "senha_temporaria": senha_temporaria
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Admin] Erro ao criar usuário: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clientes/{cliente_id}/status")
async def alterar_status_cliente(
    cliente_id: int,
    dados: StatusUpdate,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Ativa ou desativa um cliente"""
    try:
        # Verificar cliente
        cliente = db.execute(
            text("SELECT id, nome, ativo FROM clientes WHERE id = :id"),
            {"id": cliente_id}
        ).fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        if cliente[2] == dados.ativo:
            status_texto = "ativo" if dados.ativo else "inativo"
            return {"success": True, "message": f"Cliente já está {status_texto}"}

        # Atualizar status e campo ativo
        novo_status = 'ativo' if dados.ativo else 'suspenso'
        db.execute(
            text("UPDATE clientes SET ativo = :ativo, status = :status, atualizado_em = :atualizado_em WHERE id = :id"),
            {"id": cliente_id, "ativo": dados.ativo, "status": novo_status, "atualizado_em": datetime.now()}
        )

        # Se desativando, também desativar assinatura
        if not dados.ativo:
            db.execute(
                text("""
                    UPDATE assinaturas
                    SET status = 'cancelada', motivo_cancelamento = :motivo, atualizado_em = :atualizado_em
                    WHERE cliente_id = :id AND status IN ('ativa', 'pendente')
                """),
                {
                    "id": cliente_id,
                    "motivo": dados.motivo or "Desativado pelo admin",
                    "atualizado_em": datetime.now()
                }
            )

        db.commit()

        acao = "ativado" if dados.ativo else "desativado"
        logger.info(f"[Admin] Cliente {cliente_id} {acao}. Motivo: {dados.motivo}")

        # Notificar via Telegram quando desativado
        if not dados.ativo:
            try:
                asyncio.create_task(alerta_cliente_inativo(
                    nome_cliente=cliente[1],
                    motivo=dados.motivo or ""
                ))
            except Exception as e:
                logger.warning(f"[Telegram] Erro ao enviar notificação: {e}")

        return {
            "success": True,
            "message": f"Cliente {acao} com sucesso",
            "ativo": dados.ativo
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Admin] Erro ao alterar status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clientes/{cliente_id}/medicos/{medico_id}")
async def desativar_medico(
    cliente_id: int,
    medico_id: int,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Desativa um médico (não exclui para manter histórico)"""
    try:
        result = db.execute(
            text("""
                UPDATE medicos
                SET ativo = false, atualizado_em = :atualizado_em
                WHERE id = :medico_id AND cliente_id = :cliente_id
                RETURNING nome
            """),
            {
                "medico_id": medico_id,
                "cliente_id": cliente_id,
                "atualizado_em": datetime.now()
            }
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Médico não encontrado")

        db.commit()
        logger.info(f"[Admin] Médico {medico_id} desativado do cliente {cliente_id}")

        return {"success": True, "message": f"Médico {row[0]} desativado"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Admin] Erro ao desativar médico: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clientes/{cliente_id}/plano")
async def atualizar_plano_cliente(
    cliente_id: int,
    dados: PlanoUpdate,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Atualiza o plano e valor de mensalidade de um cliente.
    Tambem atualiza o valor_mensal na tabela assinaturas (se houver ativa).
    """
    try:
        # 1. Verificar se cliente existe
        cliente = db.execute(
            text("SELECT id, nome, plano, valor_mensalidade FROM clientes WHERE id = :id"),
            {"id": cliente_id}
        ).fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")

        plano_anterior = cliente[2]
        valor_anterior = cliente[3]

        # 2. Atualizar cliente
        agora = datetime.now()
        db.execute(
            text("""
                UPDATE clientes
                SET plano = :plano, valor_mensalidade = :valor_mensalidade, atualizado_em = :atualizado_em
                WHERE id = :id
            """),
            {
                "plano": dados.plano,
                "valor_mensalidade": dados.valor_mensalidade,
                "atualizado_em": agora,
                "id": cliente_id
            }
        )

        # 3. Atualizar assinatura ativa (se houver)
        assinatura_atualizada = False
        result_assinatura = db.execute(
            text("""
                UPDATE assinaturas
                SET valor_mensal = :valor_mensal, valor_com_desconto = :valor_mensal,
                    linha_dedicada = :linha_dedicada, atualizado_em = :atualizado_em
                WHERE cliente_id = :cliente_id AND status IN ('ativa', 'pendente')
                RETURNING id
            """),
            {
                "valor_mensal": float(dados.valor_mensalidade),
                "linha_dedicada": dados.linha_dedicada,
                "atualizado_em": agora,
                "cliente_id": cliente_id
            }
        )
        if result_assinatura.fetchone():
            assinatura_atualizada = True

        db.commit()

        linha_str = " (c/ linha dedicada)" if dados.linha_dedicada else ""
        logger.info(f"[Admin] Plano do cliente {cliente_id} atualizado: {plano_anterior} -> {dados.plano}, R${valor_anterior} -> R${dados.valor_mensalidade}{linha_str}")

        return {
            "success": True,
            "message": "Plano atualizado com sucesso",
            "cliente_id": cliente_id,
            "plano_anterior": plano_anterior,
            "plano_novo": dados.plano,
            "valor_anterior": valor_anterior,
            "valor_novo": dados.valor_mensalidade,
            "linha_dedicada": dados.linha_dedicada,
            "assinatura_atualizada": assinatura_atualizada
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Admin] Erro ao atualizar plano: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar plano: {str(e)}")
