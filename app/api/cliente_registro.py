"""
API de Registro de Cliente via Convite Personalizado (Self-Service)
Endpoints publicos (sem auth) para prospect preencher dados basicos.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from typing import Optional
import logging
import re
from html import escape as html_escape

from app.database import get_db
from app.services.onboarding_service import gerar_subdomain_unico
from app.services.email_service import get_email_service

# Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/registro-cliente", tags=["Registro Cliente"])
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

class RegistroClienteCreate(BaseModel):
    """Schema para registro de cliente via convite"""
    # Dados da clinica
    nome_fantasia: str = Field(..., min_length=3, max_length=255, description="Nome fantasia da clinica")
    razao_social: Optional[str] = Field(None, max_length=255, description="Razao social")
    documento: str = Field(..., min_length=11, max_length=18, description="CPF ou CNPJ")
    email: EmailStr = Field(..., description="Email da clinica")
    telefone: str = Field(..., min_length=10, max_length=16, description="Telefone com DDD")
    endereco: Optional[str] = Field(None, max_length=500, description="Endereco completo")

    # Tipo de consultorio
    tipo_consultorio: str = Field('individual', description="individual ou multi_consultorio")
    qtd_medicos_adicionais: int = Field(0, ge=0, le=20, description="Quantidade de medicos adicionais")
    necessita_secretaria: bool = Field(False, description="Se necessita secretaria")

    # Plano selecionado
    plano: str = Field('individual', description="Plano: individual ou clinica")

    # Medico principal
    medico_nome: str = Field(..., min_length=3, max_length=255, description="Nome do medico principal")
    medico_especialidade: str = Field(..., min_length=2, max_length=100, description="Especialidade")
    medico_registro_profissional: str = Field(..., min_length=4, max_length=20, description="CRM/CRO")
    medico_email: EmailStr = Field(..., description="Email do medico")
    medico_telefone: Optional[str] = Field(None, max_length=16, description="Telefone do medico")

    @validator('documento')
    def validar_documento(cls, v):
        numeros = re.sub(r'\D', '', v)
        if len(numeros) not in (11, 14):
            raise ValueError('Documento deve ser CPF (11 digitos) ou CNPJ (14 digitos)')
        return v

    @validator('telefone', 'medico_telefone')
    def validar_telefone(cls, v):
        if v is None:
            return v
        numeros = re.sub(r'\D', '', v)
        if len(numeros) < 10 or len(numeros) > 11:
            raise ValueError('Telefone deve ter 10 ou 11 digitos')
        return v

    @validator('tipo_consultorio')
    def validar_tipo_consultorio(cls, v):
        if v not in ('individual', 'multi_consultorio'):
            raise ValueError('Tipo deve ser individual ou multi_consultorio')
        return v

    @validator('medico_registro_profissional')
    def validar_registro(cls, v):
        if len(v.strip()) < 4:
            raise ValueError('Registro profissional invalido')
        return v.strip().upper()

    @validator('plano')
    def validar_plano(cls, v):
        if v not in ('individual', 'clinica'):
            raise ValueError('Plano deve ser individual ou clinica')
        return v


# ==================== ENDPOINTS ====================

@router.get("/{token}")
async def validar_convite(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Valida convite e retorna dados pre-preenchidos (se houver).
    Endpoint publico, sem autenticacao.
    """
    try:
        convite = db.execute(
            text("""
                SELECT c.id, c.token, c.email_destino, c.nome_destino, c.telefone_destino,
                       c.usado, c.expira_em, c.observacoes, c.parceiro_id,
                       p.nome as parceiro_nome
                FROM convites_clientes c
                LEFT JOIN parceiros_comerciais p ON p.id = c.parceiro_id
                WHERE c.token = :token
            """),
            {"token": token}
        ).fetchone()

        if not convite:
            raise HTTPException(status_code=404, detail="Convite nao encontrado")

        # Verificar se ja foi usado
        if convite[5]:  # usado
            raise HTTPException(status_code=409, detail="Este convite ja foi utilizado")

        # Verificar se expirou
        agora = datetime.now(timezone.utc)
        expira_em = convite[6]
        if expira_em.tzinfo is None:
            from datetime import timezone as tz
            expira_em = expira_em.replace(tzinfo=tz.utc)
        if expira_em < agora:
            raise HTTPException(status_code=410, detail="Este convite expirou")

        response = {
            "valido": True,
            "dados_preenchidos": {
                "email": convite[2],
                "nome": convite[3],
                "telefone": convite[4],
            }
        }

        # Adicionar nome do parceiro se houver
        if convite[9]:  # parceiro_nome
            response["partner_name"] = convite[9]

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RegistroCliente] Erro ao validar convite: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao validar convite")


@router.post("/{token}", status_code=201)
@limiter.limit("5/minute")
async def registrar_cliente(
    token: str,
    request: Request,
    dados: RegistroClienteCreate,
    db: Session = Depends(get_db)
):
    """
    Registra cliente via convite personalizado.

    - Rate limit: 5 requisicoes por minuto por IP
    - Valida token, inputs, unicidade
    - Cria cliente com status='pendente_aprovacao', ativo=false, plano=NULL
    - Cria medico principal sem senha e sem login
    - Marca convite como usado
    - Notifica admin via Telegram
    """
    try:
        # 1. Validar convite
        convite = db.execute(
            text("""
                SELECT id, token, email_destino, nome_destino, usado, expira_em,
                       criado_por_id, criado_por_tipo, parceiro_id
                FROM convites_clientes
                WHERE token = :token
            """),
            {"token": token}
        ).fetchone()

        if not convite:
            raise HTTPException(status_code=404, detail="Convite nao encontrado")

        if convite[4]:  # usado
            raise HTTPException(status_code=410, detail="Este convite ja foi utilizado")

        agora_utc = datetime.now(timezone.utc)
        expira_em = convite[5]
        if expira_em.tzinfo is None:
            from datetime import timezone as tz
            expira_em = expira_em.replace(tzinfo=tz.utc)
        if expira_em < agora_utc:
            raise HTTPException(status_code=410, detail="Este convite expirou")

        convite_id = convite[0]
        parceiro_id = convite[8]

        # 2. Sanitizar inputs
        nome_sanitizado = html_escape(dados.nome_fantasia.strip())
        razao_social_sanitizada = html_escape(dados.razao_social.strip()) if dados.razao_social else None
        endereco_sanitizado = html_escape(dados.endereco.strip()) if dados.endereco else None
        email_lower = dados.email.lower().strip()
        medico_email_lower = dados.medico_email.lower().strip()
        doc_numeros = re.sub(r'\D', '', dados.documento)

        # 3. Verificar unicidade de documento
        doc_existente = db.execute(
            text("SELECT id, nome FROM clientes WHERE cnpj = :cnpj"),
            {"cnpj": doc_numeros}
        ).fetchone()
        if doc_existente:
            raise HTTPException(
                status_code=409,
                detail="Este CPF/CNPJ ja esta cadastrado no sistema."
            )

        # 4. Verificar unicidade de email da clinica
        email_existente = db.execute(
            text("SELECT id FROM clientes WHERE email = :email"),
            {"email": email_lower}
        ).fetchone()
        if email_existente:
            raise HTTPException(
                status_code=409,
                detail="Este email ja esta cadastrado no sistema."
            )

        # 5. Verificar email do medico
        medico_existente = db.execute(
            text("SELECT id FROM medicos WHERE email = :email"),
            {"email": medico_email_lower}
        ).fetchone()
        if medico_existente:
            raise HTTPException(
                status_code=409,
                detail="O email do medico ja esta em uso por outro profissional."
            )

        # 6. Gerar subdomain unico
        subdomain = gerar_subdomain_unico(db, nome_sanitizado)

        # 7. Calcular valor estimado da mensalidade
        # Individual: R$150/mes (1 profissional incluso)
        # Clinica: R$200/mes (2 profissionais inclusos) + R$50 por profissional extra
        if dados.plano == 'individual':
            valor_base = 150.0
            profissionais_inclusos = 1
        else:  # clinica
            valor_base = 200.0
            profissionais_inclusos = 2

        # Total de profissionais: medico principal + adicionais
        total_profissionais = 1 + dados.qtd_medicos_adicionais
        profissionais_extras = max(0, total_profissionais - profissionais_inclusos)
        valor_mensalidade_estimado = valor_base + (profissionais_extras * 50.0)

        # 8. Criar cliente com status pendente_aprovacao
        agora = datetime.now()
        result_cliente = db.execute(
            text("""
                INSERT INTO clientes (
                    nome, cnpj, email, telefone, endereco,
                    subdomain, plano, ativo, valor_mensalidade,
                    logo_icon, cor_primaria, cor_secundaria,
                    status, tipo_consultorio, qtd_medicos_adicionais,
                    necessita_secretaria, convite_id,
                    cadastrado_por_id, cadastrado_por_tipo,
                    criado_em, atualizado_em
                ) VALUES (
                    :nome, :cnpj, :email, :telefone, :endereco,
                    :subdomain, :plano, false, :valor_mensalidade,
                    'fa-heartbeat', '#3b82f6', '#1e40af',
                    'pendente_aprovacao', :tipo_consultorio, :qtd_medicos_adicionais,
                    :necessita_secretaria, :convite_id,
                    :cadastrado_por_id, :cadastrado_por_tipo,
                    :criado_em, :atualizado_em
                )
                RETURNING id
            """),
            {
                "nome": nome_sanitizado,
                "cnpj": doc_numeros,
                "email": email_lower,
                "telefone": dados.telefone.strip(),
                "endereco": endereco_sanitizado,
                "subdomain": subdomain,
                "plano": dados.plano,
                "valor_mensalidade": f"{valor_mensalidade_estimado:.2f}",
                "tipo_consultorio": dados.tipo_consultorio,
                "qtd_medicos_adicionais": dados.qtd_medicos_adicionais,
                "necessita_secretaria": dados.necessita_secretaria,
                "convite_id": convite_id,
                "cadastrado_por_id": convite[6],  # criado_por_id do convite
                "cadastrado_por_tipo": convite[7],  # criado_por_tipo do convite
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        cliente_id = result_cliente.fetchone()[0]
        logger.info(f"[RegistroCliente] Cliente criado: ID={cliente_id} (pendente_aprovacao), plano={dados.plano}, valor_estimado=R${valor_mensalidade_estimado:.2f}")

        # 9. Criar medico principal (sem senha, sem login)
        result_medico = db.execute(
            text("""
                INSERT INTO medicos (
                    cliente_id, nome, crm, especialidade,
                    email, telefone, senha, ativo,
                    pode_fazer_login, is_admin, email_verificado,
                    is_secretaria, pode_ver_financeiro,
                    criado_em, atualizado_em
                ) VALUES (
                    :cliente_id, :nome, :crm, :especialidade,
                    :email, :telefone, NULL, true,
                    false, false, false,
                    false, false,
                    :criado_em, :atualizado_em
                )
                RETURNING id
            """),
            {
                "cliente_id": cliente_id,
                "nome": html_escape(dados.medico_nome.strip()),
                "crm": dados.medico_registro_profissional,
                "especialidade": html_escape(dados.medico_especialidade.strip()),
                "email": medico_email_lower,
                "telefone": dados.medico_telefone,
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        medico_id = result_medico.fetchone()[0]
        logger.info(f"[RegistroCliente] Medico principal criado: ID={medico_id}")

        # 10. Marcar convite como usado
        db.execute(
            text("""
                UPDATE convites_clientes
                SET usado = true, usado_em = :usado_em, cliente_id = :cliente_id
                WHERE id = :convite_id
            """),
            {
                "usado_em": agora,
                "cliente_id": cliente_id,
                "convite_id": convite_id
            }
        )

        # 11. Vincular parceiro se houver
        if parceiro_id:
            from datetime import date as date_type
            db.execute(
                text("""
                    INSERT INTO clientes_parceiros (
                        cliente_id, parceiro_id, data_vinculo, tipo_parceria,
                        ordem_cliente, ativo, criado_em
                    ) VALUES (
                        :cliente_id, :parceiro_id, :data_vinculo, 'padrao',
                        1, true, :criado_em
                    )
                """),
                {
                    "cliente_id": cliente_id,
                    "parceiro_id": parceiro_id,
                    "data_vinculo": date_type.today(),
                    "criado_em": agora
                }
            )

        db.commit()

        # 12. Notificar admin via Telegram (nao-bloqueante)
        try:
            email_service = get_email_service()

            tipo_label = "Individual" if dados.tipo_consultorio == 'individual' else f"Multi-consultorio ({dados.qtd_medicos_adicionais + 1} medicos)"
            mensagem_telegram = (
                f"<b>Novo Registro de Cliente (Self-Service)</b>\n\n"
                f"<b>Clinica:</b> {nome_sanitizado}\n"
                f"<b>Email:</b> {email_lower}\n"
                f"<b>Telefone:</b> {dados.telefone}\n"
                f"<b>Tipo:</b> {tipo_label}\n"
                f"<b>Medico:</b> {dados.medico_nome}\n"
                f"<b>Especialidade:</b> {dados.medico_especialidade}\n\n"
                f"Acesse o painel para revisar e aprovar."
            )
            email_service.send_telegram_notification(mensagem_telegram)
        except Exception as e:
            logger.warning(f"[RegistroCliente] Erro ao notificar admin: {e}")

        return {
            "sucesso": True,
            "mensagem": "Cadastro enviado com sucesso! Aguarde a aprovacao do administrador.",
            "cliente_id": cliente_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RegistroCliente] Erro ao registrar cliente: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar cadastro. Tente novamente."
        )
