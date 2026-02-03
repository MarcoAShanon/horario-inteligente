"""
API de Gestão de Clientes - Painel Admin
Endpoints para onboarding e gestão de clínicas
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, validator
import logging
import bcrypt
import secrets
import re
import unicodedata

from datetime import timedelta

from app.database import get_db
from app.api.admin import get_current_admin
from app.services.telegram_service import alerta_novo_cliente, alerta_cliente_inativo
from app.services.email_service import get_email_service
from app.services.onboarding_service import (
    gerar_subdomain, gerar_senha_temporaria, hash_senha,
    verificar_subdomain_disponivel, verificar_email_disponivel,
    TABELAS_EMAIL_VALIDAS, calcular_billing, gerar_subdomain_unico
)
import asyncio

router = APIRouter(prefix="/api/admin", tags=["Admin - Clientes"])
logger = logging.getLogger(__name__)


# ==================== SCHEMAS ====================

class MedicoPrincipalCreate(BaseModel):
    """Dados do médico principal/admin da clínica"""
    nome: str
    especialidade: str
    registro_profissional: str  # CRM, CRO, etc
    email: EmailStr
    telefone: Optional[str] = None

    @validator('nome')
    def nome_valido(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Nome deve ter pelo menos 3 caracteres')
        return v.strip()

    @validator('registro_profissional')
    def registro_valido(cls, v):
        if len(v.strip()) < 4:
            raise ValueError('Registro profissional inválido')
        return v.strip().upper()


class MedicoAdicionalOnboarding(BaseModel):
    """Dados de médico adicional no onboarding"""
    nome: str
    especialidade: str
    registro_profissional: str
    email: EmailStr
    telefone: Optional[str] = None


class SecretariaOnboarding(BaseModel):
    """Dados da secretária no onboarding"""
    nome: str
    email: EmailStr
    telefone: Optional[str] = None


class AssinaturaOnboarding(BaseModel):
    """Dados da assinatura no onboarding"""
    periodo_cobranca: str = "mensal"  # mensal, trimestral, semestral, anual
    percentual_periodo: float = 0  # Desconto pelo período (10%, 15%, 20%)
    linha_dedicada: bool = False  # Se usa linha WhatsApp dedicada (+R$40)
    dia_vencimento: int = 10  # Dia do vencimento: 1, 5 ou 10
    desconto_percentual: Optional[float] = None  # Desconto promocional percentual
    desconto_valor_fixo: Optional[float] = None  # Desconto promocional fixo
    desconto_duracao_meses: Optional[int] = None  # Duração do desconto (null=permanente)
    desconto_motivo: Optional[str] = None  # Motivo do desconto
    ativacao_cortesia: bool = False  # Isentar taxa de ativação (cortesia)


class ClienteCreate(BaseModel):
    """Dados para criar nova clínica"""
    nome_fantasia: str
    razao_social: Optional[str] = None
    documento: str  # CPF ou CNPJ
    email: EmailStr
    telefone: str
    endereco: Optional[str] = None
    plano_id: int = 1  # 1=Individual, 2=Consultório

    # Médico principal (obrigatório)
    medico_principal: MedicoPrincipalCreate

    # Médicos adicionais (opcional, para plano Consultório)
    medicos_adicionais: Optional[List[MedicoAdicionalOnboarding]] = None

    # Secretária (opcional, para plano Consultório)
    secretaria: Optional[SecretariaOnboarding] = None

    # Dados da assinatura (período, descontos, etc)
    assinatura: Optional[AssinaturaOnboarding] = None

    # Parceiro comercial (indicação)
    parceiro_id: Optional[int] = None

    @validator('documento')
    def documento_valido(cls, v):
        # Remove formatação
        doc = re.sub(r'[^0-9]', '', v)
        if len(doc) == 11:  # CPF
            return doc
        elif len(doc) == 14:  # CNPJ
            return doc
        raise ValueError('Documento deve ser CPF (11 dígitos) ou CNPJ (14 dígitos)')

    @validator('telefone')
    def telefone_valido(cls, v):
        tel = re.sub(r'[^0-9]', '', v)
        if len(tel) < 10 or len(tel) > 11:
            raise ValueError('Telefone inválido')
        return tel


class ClienteUpdate(BaseModel):
    """Dados para editar clínica"""
    nome_fantasia: Optional[str] = None
    razao_social: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None


class MedicoAdicionalCreate(BaseModel):
    """Dados para adicionar médico à clínica"""
    nome: str
    especialidade: str
    registro_profissional: str
    email: EmailStr
    telefone: Optional[str] = None
    pode_fazer_login: bool = True
    is_admin: bool = False


class UsuarioCreate(BaseModel):
    """Dados para criar usuário (secretária)"""
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    tipo: str = "secretaria"  # secretaria, admin


class StatusUpdate(BaseModel):
    """Dados para ativar/desativar cliente"""
    ativo: bool
    motivo: Optional[str] = None


# ==================== ENDPOINTS ====================

@router.post("/clientes")
async def criar_cliente(
    dados: ClienteCreate,
    request: Request,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Cria nova clínica completa com médico principal.

    Fluxo:
    1. Validar dados
    2. Gerar subdomain único
    3. Criar cliente
    4. Criar configurações padrão
    5. Criar médico principal (admin)
    6. Criar assinatura
    7. Retornar credenciais
    """
    try:
        logger.info(f"[Onboarding] Iniciando criação de cliente: {dados.nome_fantasia}")

        # 1. Gerar e validar subdomain
        subdomain_base = gerar_subdomain(dados.nome_fantasia)
        subdomain = subdomain_base
        contador = 1

        while not verificar_subdomain_disponivel(db, subdomain):
            subdomain = f"{subdomain_base}-{contador}"
            contador += 1
            if contador > 10:
                raise HTTPException(
                    status_code=400,
                    detail="Não foi possível gerar subdomain único. Tente outro nome."
                )

        logger.info(f"[Onboarding] Subdomain gerado: {subdomain}")

        # 2. Verificar documento (CPF/CNPJ) duplicado
        doc_existente = db.execute(
            text("SELECT id, nome FROM clientes WHERE cnpj = :cnpj"),
            {"cnpj": dados.documento}
        ).fetchone()
        if doc_existente:
            raise HTTPException(
                status_code=400,
                detail=f"CPF/CNPJ {dados.documento} já está cadastrado (Cliente: {doc_existente[1]}, ID: {doc_existente[0]})"
            )

        # 2b. Verificar email do médico
        if not verificar_email_disponivel(db, dados.medico_principal.email, "medicos"):
            raise HTTPException(
                status_code=400,
                detail=f"Email {dados.medico_principal.email} já está em uso por outro profissional"
            )

        # 3. Buscar plano
        plano = db.execute(
            text("SELECT id, codigo, nome, valor_mensal, profissionais_inclusos, taxa_ativacao FROM planos WHERE id = :id AND ativo = true"),
            {"id": dados.plano_id}
        ).fetchone()

        if not plano:
            raise HTTPException(
                status_code=400,
                detail=f"Plano {dados.plano_id} não encontrado ou inativo"
            )

        # 4. Criar cliente com status pendente_aceite
        agora = datetime.now()
        token_ativacao = secrets.token_urlsafe(64)
        token_expira_em = agora + timedelta(days=7)

        result_cliente = db.execute(
            text("""
                INSERT INTO clientes (
                    nome, cnpj, email, telefone, endereco,
                    subdomain, plano, ativo, valor_mensalidade,
                    logo_icon, cor_primaria, cor_secundaria,
                    status, token_ativacao, token_expira_em,
                    cadastrado_por_id, cadastrado_por_tipo,
                    criado_em, atualizado_em
                ) VALUES (
                    :nome, :cnpj, :email, :telefone, :endereco,
                    :subdomain, :plano, false, :valor_mensalidade,
                    'fa-heartbeat', '#3b82f6', '#1e40af',
                    'pendente_aceite', :token_ativacao, :token_expira_em,
                    :cadastrado_por_id, 'admin',
                    :criado_em, :atualizado_em
                )
                RETURNING id
            """),
            {
                "nome": dados.nome_fantasia,
                "cnpj": dados.documento,
                "email": dados.email,
                "telefone": dados.telefone,
                "endereco": dados.endereco,
                "subdomain": subdomain,
                "plano": plano[1],  # codigo do plano
                "valor_mensalidade": str(plano[3]),  # valor_mensal
                "token_ativacao": token_ativacao,
                "token_expira_em": token_expira_em,
                "cadastrado_por_id": admin.get("id"),
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        cliente_id = result_cliente.fetchone()[0]
        logger.info(f"[Onboarding] Cliente criado: ID={cliente_id} (pendente_aceite)")

        # 5. Criar configurações padrão
        db.execute(
            text("""
                INSERT INTO configuracoes (
                    cliente_id, sistema_ativo, timezone,
                    criado_em, atualizado_em
                ) VALUES (
                    :cliente_id, true, 'America/Sao_Paulo',
                    :criado_em, :atualizado_em
                )
            """),
            {
                "cliente_id": cliente_id,
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        logger.info(f"[Onboarding] Configurações criadas para cliente {cliente_id}")

        # 6. Criar médico principal
        senha_temporaria = gerar_senha_temporaria()
        senha_hash = hash_senha(senha_temporaria)

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
                    :email, :telefone, :senha, true,
                    true, true, true,
                    false, true,
                    :criado_em, :atualizado_em
                )
                RETURNING id
            """),
            {
                "cliente_id": cliente_id,
                "nome": dados.medico_principal.nome,
                "crm": dados.medico_principal.registro_profissional,
                "especialidade": dados.medico_principal.especialidade,
                "email": dados.medico_principal.email,
                "telefone": dados.medico_principal.telefone,
                "senha": senha_hash,
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        medico_id = result_medico.fetchone()[0]
        logger.info(f"[Onboarding] Médico principal criado: ID={medico_id}")

        # 7. Criar assinatura com cálculo de valores
        valor_base_plano = float(plano[3])  # valor_mensal do plano
        profissionais_inclusos = plano[4]

        # Calcular profissionais extras (R$50 cada)
        total_profissionais = 1  # Médico principal
        if dados.medicos_adicionais:
            total_profissionais += len(dados.medicos_adicionais)

        profissionais_extras = max(0, total_profissionais - profissionais_inclusos)
        valor_extras_profissionais = profissionais_extras * 50.0

        # Valores da assinatura
        assinatura_dados = dados.assinatura or AssinaturaOnboarding()

        # Adicional linha WhatsApp dedicada (+R$40) — valor fixo, sem desconto de periodicidade
        valor_linha_dedicada = 40.0 if assinatura_dados.linha_dedicada else 0.0

        # Subtotal descontável (sem linha dedicada)
        subtotal_descontavel = valor_base_plano + valor_extras_profissionais

        # Valor original (para registro, antes de descontos)
        valor_original = subtotal_descontavel + valor_linha_dedicada

        # Aplicar desconto do período apenas sobre plano + extras
        percentual_periodo = assinatura_dados.percentual_periodo or 0
        valor_apos_desconto_periodo = subtotal_descontavel * (1 - percentual_periodo / 100)
        valor_apos_desconto_periodo += valor_linha_dedicada  # linha dedicada sem desconto

        # Aplicar desconto promocional
        valor_final = valor_apos_desconto_periodo
        if assinatura_dados.desconto_percentual and assinatura_dados.desconto_percentual > 0:
            valor_final = valor_final * (1 - assinatura_dados.desconto_percentual / 100)
        elif assinatura_dados.desconto_valor_fixo and assinatura_dados.desconto_valor_fixo > 0:
            valor_final = max(0, valor_final - assinatura_dados.desconto_valor_fixo)

        # Calcular data fim do desconto promocional
        data_fim_desconto = None
        if assinatura_dados.desconto_duracao_meses and assinatura_dados.desconto_duracao_meses > 0:
            # Aproximação: 30 dias por mês
            dias = assinatura_dados.desconto_duracao_meses * 30
            data_fim_desconto = date.today() + timedelta(days=dias)

        # Se cortesia, aplicar 100% de desconto na taxa de ativação
        desconto_ativacao_pct = 100 if assinatura_dados.ativacao_cortesia else 0
        motivo_desconto_ativacao = "Cortesia" if assinatura_dados.ativacao_cortesia else None

        db.execute(
            text("""
                INSERT INTO assinaturas (
                    cliente_id, plano_id, valor_mensal,
                    profissionais_contratados, taxa_ativacao,
                    data_inicio, status, dia_vencimento,
                    periodo_cobranca, percentual_periodo,
                    valor_original, valor_com_desconto,
                    desconto_percentual, desconto_valor_fixo,
                    desconto_duracao_meses, desconto_motivo,
                    data_fim_desconto, linha_dedicada,
                    ativacao_cortesia, desconto_ativacao_percentual,
                    motivo_desconto_ativacao,
                    criado_em
                ) VALUES (
                    :cliente_id, :plano_id, :valor_mensal,
                    :profissionais, :taxa_ativacao,
                    :data_inicio, 'pendente', :dia_vencimento,
                    :periodo_cobranca, :percentual_periodo,
                    :valor_original, :valor_com_desconto,
                    :desconto_percentual, :desconto_valor_fixo,
                    :desconto_duracao_meses, :desconto_motivo,
                    :data_fim_desconto, :linha_dedicada,
                    :ativacao_cortesia, :desconto_ativacao_percentual,
                    :motivo_desconto_ativacao,
                    :criado_em
                )
            """),
            {
                "cliente_id": cliente_id,
                "plano_id": plano[0],
                "valor_mensal": valor_final,
                "profissionais": total_profissionais,
                "taxa_ativacao": plano[5],  # taxa_ativacao
                "data_inicio": date.today(),
                "dia_vencimento": assinatura_dados.dia_vencimento,
                "periodo_cobranca": assinatura_dados.periodo_cobranca,
                "percentual_periodo": percentual_periodo,
                "valor_original": valor_original,
                "valor_com_desconto": valor_final,
                "desconto_percentual": assinatura_dados.desconto_percentual,
                "desconto_valor_fixo": assinatura_dados.desconto_valor_fixo,
                "desconto_duracao_meses": assinatura_dados.desconto_duracao_meses,
                "desconto_motivo": assinatura_dados.desconto_motivo,
                "data_fim_desconto": data_fim_desconto,
                "linha_dedicada": assinatura_dados.linha_dedicada,
                "ativacao_cortesia": assinatura_dados.ativacao_cortesia,
                "desconto_ativacao_percentual": desconto_ativacao_pct,
                "motivo_desconto_ativacao": motivo_desconto_ativacao,
                "criado_em": agora
            }
        )
        logger.info(f"[Onboarding] Assinatura criada para cliente {cliente_id}: R${valor_final:.2f}/mês (original: R${valor_original:.2f})")

        # 7.5 Buscar ID da assinatura recém criada
        assinatura_result = db.execute(
            text("SELECT id FROM assinaturas WHERE cliente_id = :cliente_id ORDER BY criado_em DESC LIMIT 1"),
            {"cliente_id": cliente_id}
        ).fetchone()
        assinatura_id = assinatura_result[0] if assinatura_result else None

        # 7.6 Criar vínculo e comissão se tiver parceiro
        comissao_info = None
        if dados.parceiro_id:
            # Verificar se parceiro existe e está ativo
            parceiro = db.execute(
                text("""
                    SELECT id, nome, percentual_comissao, tipo_comissao, parceria_lancamento, limite_clientes_lancamento
                    FROM parceiros_comerciais
                    WHERE id = :parceiro_id AND ativo = true
                """),
                {"parceiro_id": dados.parceiro_id}
            ).fetchone()

            if parceiro:
                # Contar clientes existentes do parceiro (para parceria de lançamento)
                clientes_parceiro = db.execute(
                    text("SELECT COUNT(*) FROM clientes_parceiros WHERE parceiro_id = :parceiro_id AND ativo = true"),
                    {"parceiro_id": dados.parceiro_id}
                ).scalar() or 0

                ordem_cliente = clientes_parceiro + 1
                tipo_parceria = 'lancamento' if parceiro[4] and ordem_cliente <= (parceiro[5] or 40) else 'padrao'

                # Criar vínculo em clientes_parceiros
                db.execute(
                    text("""
                        INSERT INTO clientes_parceiros (
                            cliente_id, parceiro_id, data_vinculo, tipo_parceria,
                            ordem_cliente, ativo, criado_em
                        ) VALUES (
                            :cliente_id, :parceiro_id, :data_vinculo, :tipo_parceria,
                            :ordem_cliente, true, :criado_em
                        )
                    """),
                    {
                        "cliente_id": cliente_id,
                        "parceiro_id": dados.parceiro_id,
                        "data_vinculo": date.today(),
                        "tipo_parceria": tipo_parceria,
                        "ordem_cliente": ordem_cliente,
                        "criado_em": agora
                    }
                )
                logger.info(f"[Onboarding] Vínculo cliente-parceiro criado: cliente {cliente_id} -> parceiro {dados.parceiro_id}")

                # Calcular comissão
                percentual_comissao = float(parceiro[2]) if parceiro[2] else 40.0  # Default 40%

                # Valor comissionável mensal = plano base + extras (SEM linha dedicada)
                valor_comissionavel = valor_base_plano + valor_extras_profissionais
                comissao_mensal = valor_comissionavel * (percentual_comissao / 100)

                # Comissão sobre taxa de ativação
                taxa_ativacao = float(plano[5]) if plano[5] else 150.0
                # Se ativação é cortesia, não há comissão sobre ativação
                comissao_ativacao = 0.0 if assinatura_dados.ativacao_cortesia else taxa_ativacao * (percentual_comissao / 100)

                # Criar registro de comissão mensal (mes_referencia=1)
                db.execute(
                    text("""
                        INSERT INTO comissoes (
                            parceiro_id, cliente_id, assinatura_id,
                            valor_base, percentual_aplicado, valor_comissao,
                            mes_referencia, data_referencia, status,
                            observacoes, created_at
                        ) VALUES (
                            :parceiro_id, :cliente_id, :assinatura_id,
                            :valor_base, :percentual_aplicado, :valor_comissao,
                            1, :data_referencia, 'pendente',
                            'Comissão mensal', :created_at
                        )
                    """),
                    {
                        "parceiro_id": dados.parceiro_id,
                        "cliente_id": cliente_id,
                        "assinatura_id": assinatura_id,
                        "valor_base": valor_comissionavel,
                        "percentual_aplicado": percentual_comissao,
                        "valor_comissao": comissao_mensal,
                        "data_referencia": date.today(),
                        "created_at": agora
                    }
                )
                logger.info(f"[Onboarding] Comissão mensal criada: R${comissao_mensal:.2f} ({percentual_comissao}% de R${valor_comissionavel:.2f})")

                # Criar registro de comissão sobre ativação (mes_referencia=0)
                if comissao_ativacao > 0:
                    db.execute(
                        text("""
                            INSERT INTO comissoes (
                                parceiro_id, cliente_id, assinatura_id,
                                valor_base, percentual_aplicado, valor_comissao,
                                mes_referencia, data_referencia, status,
                                observacoes, created_at
                            ) VALUES (
                                :parceiro_id, :cliente_id, :assinatura_id,
                                :valor_base, :percentual_aplicado, :valor_comissao,
                                0, :data_referencia, 'pendente',
                                'Comissão sobre taxa de ativação', :created_at
                            )
                        """),
                        {
                            "parceiro_id": dados.parceiro_id,
                            "cliente_id": cliente_id,
                            "assinatura_id": assinatura_id,
                            "valor_base": taxa_ativacao,
                            "percentual_aplicado": percentual_comissao,
                            "valor_comissao": comissao_ativacao,
                            "data_referencia": date.today(),
                            "created_at": agora
                        }
                    )
                    logger.info(f"[Onboarding] Comissão ativação criada: R${comissao_ativacao:.2f} ({percentual_comissao}% de R${taxa_ativacao:.2f})")

                comissao_info = {
                    "parceiro_id": dados.parceiro_id,
                    "parceiro_nome": parceiro[1],
                    "valor_base_mensal": valor_comissionavel,
                    "valor_base_ativacao": taxa_ativacao if not assinatura_dados.ativacao_cortesia else 0,
                    "percentual": percentual_comissao,
                    "comissao_mensal": comissao_mensal,
                    "comissao_ativacao": comissao_ativacao,
                    "total_primeira_comissao": comissao_mensal + comissao_ativacao,
                    "tipo_parceria": tipo_parceria,
                    "ordem_cliente": ordem_cliente
                }
            else:
                logger.warning(f"[Onboarding] Parceiro {dados.parceiro_id} não encontrado ou inativo")

        # 8. Commit da transação
        db.commit()

        # 9. Log de auditoria (não-crítico, não deve afetar a transação principal)
        try:
            db.execute(
                text("""
                    INSERT INTO log_auditoria (
                        recurso, recurso_id, acao, dados_novos,
                        usuario_id, usuario_tipo, ip_address, criado_em
                    ) VALUES (
                        'clientes', :recurso_id, 'CREATE', :dados,
                        :usuario_id, 'admin', :ip, :criado_em
                    )
                """),
                {
                    "recurso_id": cliente_id,
                    "dados": f'{{"nome": "{dados.nome_fantasia}", "plano": "{plano[1]}", "medico": "{dados.medico_principal.nome}"}}',
                    "usuario_id": admin.get("id"),
                    "ip": request.client.host if request.client else "unknown",
                    "criado_em": agora
                }
            )
            db.commit()
        except Exception as e:
            db.rollback()  # Limpar estado da transação para não afetar operações seguintes
            logger.warning(f"[Onboarding] Erro ao criar log de auditoria: {e}")

        logger.info(f"[Onboarding] ✅ Cliente {dados.nome_fantasia} criado com sucesso!")

        # 10. Criar médicos adicionais (se houver)
        medicos_adicionais_response = []
        if dados.medicos_adicionais:
            for med in dados.medicos_adicionais:
                med_senha = gerar_senha_temporaria()
                med_senha_hash = hash_senha(med_senha)

                result_med = db.execute(
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
                            true, false, true,
                            false, true,
                            :criado_em, :atualizado_em
                        )
                        RETURNING id
                    """),
                    {
                        "cliente_id": cliente_id,
                        "nome": med.nome,
                        "crm": med.registro_profissional,
                        "especialidade": med.especialidade,
                        "email": med.email,
                        "telefone": med.telefone,
                        "senha": med_senha_hash,
                        "criado_em": agora,
                        "atualizado_em": agora
                    }
                )
                med_id = result_med.fetchone()[0]

                medicos_adicionais_response.append({
                    "id": med_id,
                    "nome": med.nome,
                    "email": med.email,
                    "senha_temporaria": med_senha
                })
                logger.info(f"[Onboarding] Médico adicional criado: {med.nome} (ID={med_id})")

            db.commit()

        # 11. Criar secretária (se houver) - na tabela medicos com is_secretaria=true
        secretaria_response = None
        if dados.secretaria:
            sec_senha = gerar_senha_temporaria()
            sec_senha_hash = hash_senha(sec_senha)

            result_sec = db.execute(
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
                    "nome": dados.secretaria.nome,
                    "email": dados.secretaria.email,
                    "telefone": dados.secretaria.telefone,
                    "senha": sec_senha_hash,
                    "criado_em": agora,
                    "atualizado_em": agora
                }
            )
            sec_id = result_sec.fetchone()[0]
            db.commit()

            secretaria_response = {
                "id": sec_id,
                "nome": dados.secretaria.nome,
                "email": dados.secretaria.email,
                "senha_temporaria": sec_senha,
                "tipo": "secretaria"
            }
            logger.info(f"[Onboarding] Secretária criada na tabela medicos: {dados.secretaria.nome} (ID={sec_id})")

        # Enviar notificação via Telegram (não bloqueante)
        try:
            asyncio.create_task(alerta_novo_cliente(
                nome_cliente=dados.nome_fantasia,
                plano=plano[2],  # nome do plano
                subdomain=subdomain,
                valor_mensal=valor_final,
                periodo=assinatura_dados.periodo_cobranca
            ))
        except Exception as e:
            logger.warning(f"[Telegram] Erro ao enviar notificação: {e}")

        # Enviar email de ativação (não bloqueante)
        link_ativacao = f"https://horariointeligente.com.br/static/ativar-conta.html?token={token_ativacao}"
        try:
            email_service = get_email_service()
            email_service.send_ativacao_conta(dados.email, dados.nome_fantasia, token_ativacao)
            logger.info(f"[Onboarding] Email de ativação enviado para {dados.email}")
        except Exception as e:
            logger.warning(f"[Onboarding] Erro ao enviar email de ativação: {e}")

        # Montar resposta
        response = {
            "success": True,
            "cliente": {
                "id": cliente_id,
                "nome": dados.nome_fantasia,
                "subdomain": subdomain,
                "plano": plano[1],
                "plano_nome": plano[2],
                "status": "pendente_aceite"
            },
            "ativacao": {
                "status": "pendente_aceite",
                "link_ativacao": link_ativacao,
                "expira_em": token_expira_em.isoformat(),
                "email_enviado": True
            },
            "assinatura": {
                "valor_base_plano": valor_base_plano,
                "profissionais_contratados": total_profissionais,
                "profissionais_extras": profissionais_extras,
                "valor_extras_profissionais": valor_extras_profissionais,
                "linha_dedicada": assinatura_dados.linha_dedicada,
                "valor_linha_dedicada": valor_linha_dedicada,
                "periodo_cobranca": assinatura_dados.periodo_cobranca,
                "percentual_periodo": percentual_periodo,
                "valor_original": valor_original,
                "desconto_percentual": assinatura_dados.desconto_percentual,
                "desconto_valor_fixo": assinatura_dados.desconto_valor_fixo,
                "desconto_duracao_meses": assinatura_dados.desconto_duracao_meses,
                "desconto_motivo": assinatura_dados.desconto_motivo,
                "valor_final": valor_final,
                "data_fim_desconto": data_fim_desconto.isoformat() if data_fim_desconto else None
            },
            "medico_principal": {
                "id": medico_id,
                "nome": dados.medico_principal.nome,
                "email": dados.medico_principal.email
            },
            "credenciais": {
                "url_acesso": f"https://{subdomain}.horariointeligente.com.br",
                "email": dados.medico_principal.email,
                "senha_temporaria": senha_temporaria
            },
            "proximos_passos": [
                "Cliente receberá email para aceitar termos e ativar conta",
                "Após ativação, configurar número WhatsApp na WABA (Meta Business)",
                "Agendar chamada de onboarding para configuração inicial",
                "Gerar primeira cobrança no ASAAS"
            ]
        }

        # Adicionar médicos adicionais à resposta
        if medicos_adicionais_response:
            response["medicos_adicionais"] = medicos_adicionais_response

        # Adicionar secretária à resposta
        if secretaria_response:
            response["secretaria"] = secretaria_response

        # Adicionar informações da comissão se houver parceiro
        if comissao_info:
            response["comissao"] = comissao_info

        return response

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Onboarding] Erro ao criar cliente: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar cliente: {str(e)}"
        )


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


@router.post("/clientes/{cliente_id}/enviar-credenciais")
async def enviar_credenciais(
    cliente_id: int,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Gera novas senhas temporárias e envia credenciais de acesso
    por email a todos os profissionais ativos do cliente.
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
                detail="Nenhum profissional ativo com email encontrado"
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


# ==================== STATUS DO SISTEMA ====================

@router.get("/sistema/certificado-ssl")
async def get_certificado_status(admin = Depends(get_current_admin)):
    """Retorna o status do certificado SSL wildcard"""
    import json
    import os

    status_file = "/var/run/ssl-cert-status.json"

    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                status = json.load(f)
            return status
        else:
            # Gerar status em tempo real se o arquivo não existir
            import subprocess
            cert_path = "/etc/letsencrypt/live/horariointeligente.com.br-0001/fullchain.pem"

            if os.path.exists(cert_path):
                result = subprocess.run(
                    ["openssl", "x509", "-enddate", "-noout", "-in", cert_path],
                    capture_output=True, text=True
                )
                expiry_str = result.stdout.strip().split("=")[1]

                from datetime import datetime
                expiry_date = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                days_left = (expiry_date - datetime.now()).days

                return {
                    "domain": "horariointeligente.com.br",
                    "type": "wildcard",
                    "expiry_date": expiry_str,
                    "days_left": days_left,
                    "status": "critical" if days_left <= 7 else ("warning" if days_left <= 30 else "ok"),
                    "last_check": datetime.now().isoformat(),
                    "cert_path": cert_path
                }
            else:
                return {
                    "domain": "horariointeligente.com.br",
                    "status": "error",
                    "message": "Certificado não encontrado"
                }

    except Exception as e:
        logger.error(f"[Admin] Erro ao verificar certificado SSL: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ==================== APROVACAO / REJEICAO DE CLIENTES ====================

class AprovacaoClienteRequest(BaseModel):
    """Dados para aprovar cliente pendente"""
    plano_id: int
    assinatura: Optional[AssinaturaOnboarding] = None
    medicos_adicionais: Optional[List[MedicoAdicionalOnboarding]] = None
    secretaria: Optional[SecretariaOnboarding] = None
    parceiro_id: Optional[int] = None


class RejeicaoClienteRequest(BaseModel):
    """Dados para rejeitar cliente pendente"""
    motivo: Optional[str] = None
    notificar_email: bool = False


class PlanoUpdate(BaseModel):
    """Dados para atualizar plano do cliente"""
    plano: str  # 'individual', 'clinica', 'profissional'
    valor_mensalidade: str  # ex: "150.00"
    linha_dedicada: bool = False  # Linha WhatsApp dedicada (+R$40)

    @validator('plano')
    def plano_valido(cls, v):
        planos_validos = ('individual', 'clinica', 'profissional')
        if v not in planos_validos:
            raise ValueError(f'Plano deve ser um de: {", ".join(planos_validos)}')
        return v

    @validator('valor_mensalidade')
    def valor_valido(cls, v):
        try:
            valor = float(v.replace(',', '.'))
            if valor < 0:
                raise ValueError('Valor nao pode ser negativo')
            return f"{valor:.2f}"
        except (ValueError, AttributeError):
            raise ValueError('Valor de mensalidade invalido')


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


@router.post("/clientes/{cliente_id}/aprovar")
async def aprovar_cliente(
    cliente_id: int,
    dados: AprovacaoClienteRequest,
    request: Request,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Aprova cliente com status 'pendente_aprovacao'.
    Configura billing, gera senhas, cria assinatura e envia email de ativacao.
    """
    try:
        # 1. Validar cliente
        cliente = db.execute(
            text("""
                SELECT id, nome, email, subdomain, status, telefone,
                       tipo_consultorio, qtd_medicos_adicionais, necessita_secretaria
                FROM clientes
                WHERE id = :id
            """),
            {"id": cliente_id}
        ).fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")

        if cliente[4] != 'pendente_aprovacao':
            raise HTTPException(
                status_code=400,
                detail=f"Cliente nao esta pendente de aprovacao (status atual: {cliente[4]})"
            )

        nome_cliente = cliente[1]
        email_cliente = cliente[2]
        subdomain = cliente[3]

        # 2. Buscar plano
        plano = db.execute(
            text("SELECT id, codigo, nome, valor_mensal, profissionais_inclusos, taxa_ativacao FROM planos WHERE id = :id AND ativo = true"),
            {"id": dados.plano_id}
        ).fetchone()

        if not plano:
            raise HTTPException(status_code=400, detail=f"Plano {dados.plano_id} nao encontrado ou inativo")

        # 3. Buscar medico principal
        medico_principal = db.execute(
            text("""
                SELECT id, nome, email FROM medicos
                WHERE cliente_id = :cliente_id AND is_secretaria = false
                ORDER BY criado_em ASC LIMIT 1
            """),
            {"cliente_id": cliente_id}
        ).fetchone()

        if not medico_principal:
            raise HTTPException(status_code=400, detail="Medico principal nao encontrado para este cliente")

        agora = datetime.now()

        # 4. Gerar senha e atualizar medico principal
        senha_temporaria = gerar_senha_temporaria()
        senha_hash_val = hash_senha(senha_temporaria)

        db.execute(
            text("""
                UPDATE medicos
                SET pode_fazer_login = true, is_admin = true, senha = :senha,
                    email_verificado = true, pode_ver_financeiro = true,
                    atualizado_em = :atualizado_em
                WHERE id = :id
            """),
            {
                "senha": senha_hash_val,
                "atualizado_em": agora,
                "id": medico_principal[0]
            }
        )
        logger.info(f"[Aprovacao] Medico principal {medico_principal[0]} atualizado com credenciais")

        # 5. Calcular billing e criar assinatura
        assinatura_dados = dados.assinatura or AssinaturaOnboarding()
        total_profissionais = 1  # medico principal
        if dados.medicos_adicionais:
            total_profissionais += len(dados.medicos_adicionais)

        billing = calcular_billing(
            valor_base_plano=float(plano[3]),
            profissionais_inclusos=plano[4],
            total_profissionais=total_profissionais,
            assinatura_dados=assinatura_dados
        )

        result_assinatura = db.execute(
            text("""
                INSERT INTO assinaturas (
                    cliente_id, plano_id, valor_mensal,
                    profissionais_contratados, taxa_ativacao,
                    data_inicio, status, dia_vencimento,
                    periodo_cobranca, percentual_periodo,
                    valor_original, valor_com_desconto,
                    desconto_percentual, desconto_valor_fixo,
                    desconto_duracao_meses, desconto_motivo,
                    data_fim_desconto, linha_dedicada,
                    ativacao_cortesia, desconto_ativacao_percentual,
                    motivo_desconto_ativacao,
                    criado_em
                ) VALUES (
                    :cliente_id, :plano_id, :valor_mensal,
                    :profissionais, :taxa_ativacao,
                    :data_inicio, 'pendente', :dia_vencimento,
                    :periodo_cobranca, :percentual_periodo,
                    :valor_original, :valor_com_desconto,
                    :desconto_percentual, :desconto_valor_fixo,
                    :desconto_duracao_meses, :desconto_motivo,
                    :data_fim_desconto, :linha_dedicada,
                    :ativacao_cortesia, :desconto_ativacao_percentual,
                    :motivo_desconto_ativacao,
                    :criado_em
                )
                RETURNING id
            """),
            {
                "cliente_id": cliente_id,
                "plano_id": plano[0],
                "valor_mensal": billing["valor_final"],
                "profissionais": total_profissionais,
                "taxa_ativacao": plano[5],
                "data_inicio": date.today(),
                "dia_vencimento": assinatura_dados.dia_vencimento,
                "periodo_cobranca": assinatura_dados.periodo_cobranca,
                "percentual_periodo": billing["percentual_periodo"],
                "valor_original": billing["valor_original"],
                "valor_com_desconto": billing["valor_final"],
                "desconto_percentual": assinatura_dados.desconto_percentual,
                "desconto_valor_fixo": assinatura_dados.desconto_valor_fixo,
                "desconto_duracao_meses": assinatura_dados.desconto_duracao_meses,
                "desconto_motivo": assinatura_dados.desconto_motivo,
                "data_fim_desconto": billing["data_fim_desconto"],
                "linha_dedicada": assinatura_dados.linha_dedicada,
                "ativacao_cortesia": assinatura_dados.ativacao_cortesia,
                "desconto_ativacao_percentual": billing["desconto_ativacao_pct"],
                "motivo_desconto_ativacao": billing["motivo_desconto_ativacao"],
                "criado_em": agora
            }
        )
        assinatura_id = result_assinatura.fetchone()[0]
        logger.info(f"[Aprovacao] Assinatura criada para cliente {cliente_id}: R${billing['valor_final']:.2f}/mes (ID={assinatura_id})")

        # 6. Criar medicos adicionais (se houver)
        medicos_adicionais_response = []
        if dados.medicos_adicionais:
            for med in dados.medicos_adicionais:
                med_senha = gerar_senha_temporaria()
                med_senha_hash = hash_senha(med_senha)

                result_med = db.execute(
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
                            true, false, true,
                            false, true,
                            :criado_em, :atualizado_em
                        )
                        RETURNING id
                    """),
                    {
                        "cliente_id": cliente_id,
                        "nome": med.nome,
                        "crm": med.registro_profissional,
                        "especialidade": med.especialidade,
                        "email": med.email,
                        "telefone": med.telefone,
                        "senha": med_senha_hash,
                        "criado_em": agora,
                        "atualizado_em": agora
                    }
                )
                med_id = result_med.fetchone()[0]
                medicos_adicionais_response.append({
                    "id": med_id,
                    "nome": med.nome,
                    "email": med.email,
                    "senha_temporaria": med_senha
                })

        # 7. Criar secretaria (se houver)
        secretaria_response = None
        if dados.secretaria:
            sec_senha = gerar_senha_temporaria()
            sec_senha_hash = hash_senha(sec_senha)

            result_sec = db.execute(
                text("""
                    INSERT INTO medicos (
                        cliente_id, nome, crm, especialidade,
                        email, telefone, senha, ativo,
                        pode_fazer_login, is_admin, email_verificado,
                        is_secretaria, pode_ver_financeiro,
                        criado_em, atualizado_em
                    ) VALUES (
                        :cliente_id, :nome, 'N/A', 'Secretaria',
                        :email, :telefone, :senha, true,
                        true, false, true,
                        true, false,
                        :criado_em, :atualizado_em
                    )
                    RETURNING id
                """),
                {
                    "cliente_id": cliente_id,
                    "nome": dados.secretaria.nome,
                    "email": dados.secretaria.email,
                    "telefone": dados.secretaria.telefone,
                    "senha": sec_senha_hash,
                    "criado_em": agora,
                    "atualizado_em": agora
                }
            )
            sec_id = result_sec.fetchone()[0]
            secretaria_response = {
                "id": sec_id,
                "nome": dados.secretaria.nome,
                "email": dados.secretaria.email,
                "senha_temporaria": sec_senha
            }

        # 8. Criar configuracao default
        db.execute(
            text("""
                INSERT INTO configuracoes (
                    cliente_id, sistema_ativo, timezone,
                    criado_em, atualizado_em
                ) VALUES (
                    :cliente_id, true, 'America/Sao_Paulo',
                    :criado_em, :atualizado_em
                )
                ON CONFLICT (cliente_id) DO NOTHING
            """),
            {
                "cliente_id": cliente_id,
                "criado_em": agora,
                "atualizado_em": agora
            }
        )

        # 9. Gerar token de ativacao e atualizar status
        token_ativacao = secrets.token_urlsafe(64)
        token_expira_em = agora + timedelta(days=7)

        db.execute(
            text("""
                UPDATE clientes
                SET status = 'pendente_aceite',
                    plano = :plano,
                    valor_mensalidade = :valor_mensalidade,
                    token_ativacao = :token_ativacao,
                    token_expira_em = :token_expira_em,
                    atualizado_em = :atualizado_em
                WHERE id = :id
            """),
            {
                "plano": plano[1],
                "valor_mensalidade": str(billing["valor_final"]),
                "token_ativacao": token_ativacao,
                "token_expira_em": token_expira_em,
                "atualizado_em": agora,
                "id": cliente_id
            }
        )

        # 10. Vincular parceiro e criar comissões (se informado na aprovacao)
        comissao_info = None
        if dados.parceiro_id:
            # Buscar dados do parceiro
            parceiro = db.execute(
                text("""
                    SELECT id, nome, percentual_comissao, tipo_comissao, parceria_lancamento, limite_clientes_lancamento
                    FROM parceiros_comerciais
                    WHERE id = :parceiro_id AND ativo = true
                """),
                {"parceiro_id": dados.parceiro_id}
            ).fetchone()

            if parceiro:
                vinculo_existente = db.execute(
                    text("SELECT id FROM clientes_parceiros WHERE cliente_id = :cid AND parceiro_id = :pid"),
                    {"cid": cliente_id, "pid": dados.parceiro_id}
                ).fetchone()

                if not vinculo_existente:
                    # Contar clientes existentes do parceiro
                    clientes_parceiro = db.execute(
                        text("SELECT COUNT(*) FROM clientes_parceiros WHERE parceiro_id = :parceiro_id AND ativo = true"),
                        {"parceiro_id": dados.parceiro_id}
                    ).scalar() or 0

                    ordem_cliente = clientes_parceiro + 1
                    tipo_parceria = 'lancamento' if parceiro[4] and ordem_cliente <= (parceiro[5] or 40) else 'padrao'

                    db.execute(
                        text("""
                            INSERT INTO clientes_parceiros (
                                cliente_id, parceiro_id, data_vinculo, tipo_parceria,
                                ordem_cliente, ativo, criado_em
                            ) VALUES (
                                :cliente_id, :parceiro_id, :data_vinculo, :tipo_parceria,
                                :ordem_cliente, true, :criado_em
                            )
                        """),
                        {
                            "cliente_id": cliente_id,
                            "parceiro_id": dados.parceiro_id,
                            "data_vinculo": date.today(),
                            "tipo_parceria": tipo_parceria,
                            "ordem_cliente": ordem_cliente,
                            "criado_em": agora
                        }
                    )
                    logger.info(f"[Aprovacao] Vínculo cliente-parceiro criado: cliente {cliente_id} -> parceiro {dados.parceiro_id}")

                # Calcular comissões
                percentual_comissao = float(parceiro[2]) if parceiro[2] else 40.0

                # Valor comissionável mensal = plano base + extras (SEM linha dedicada)
                valor_base_plano = float(plano[3])
                profissionais_inclusos = plano[4]
                profissionais_extras = max(0, total_profissionais - profissionais_inclusos)
                valor_extras_profissionais = profissionais_extras * 50.0
                valor_comissionavel = valor_base_plano + valor_extras_profissionais
                comissao_mensal = valor_comissionavel * (percentual_comissao / 100)

                # Comissão sobre taxa de ativação
                taxa_ativacao = float(plano[5]) if plano[5] else 150.0
                comissao_ativacao = 0.0 if assinatura_dados.ativacao_cortesia else taxa_ativacao * (percentual_comissao / 100)

                # Criar registro de comissão mensal (mes_referencia=1)
                db.execute(
                    text("""
                        INSERT INTO comissoes (
                            parceiro_id, cliente_id, assinatura_id,
                            valor_base, percentual_aplicado, valor_comissao,
                            mes_referencia, data_referencia, status,
                            observacoes, created_at
                        ) VALUES (
                            :parceiro_id, :cliente_id, :assinatura_id,
                            :valor_base, :percentual_aplicado, :valor_comissao,
                            1, :data_referencia, 'pendente',
                            'Comissão mensal', :created_at
                        )
                    """),
                    {
                        "parceiro_id": dados.parceiro_id,
                        "cliente_id": cliente_id,
                        "assinatura_id": assinatura_id,
                        "valor_base": valor_comissionavel,
                        "percentual_aplicado": percentual_comissao,
                        "valor_comissao": comissao_mensal,
                        "data_referencia": date.today(),
                        "created_at": agora
                    }
                )
                logger.info(f"[Aprovacao] Comissão mensal criada: R${comissao_mensal:.2f} ({percentual_comissao}% de R${valor_comissionavel:.2f})")

                # Criar registro de comissão sobre ativação (mes_referencia=0)
                if comissao_ativacao > 0:
                    db.execute(
                        text("""
                            INSERT INTO comissoes (
                                parceiro_id, cliente_id, assinatura_id,
                                valor_base, percentual_aplicado, valor_comissao,
                                mes_referencia, data_referencia, status,
                                observacoes, created_at
                            ) VALUES (
                                :parceiro_id, :cliente_id, :assinatura_id,
                                :valor_base, :percentual_aplicado, :valor_comissao,
                                0, :data_referencia, 'pendente',
                                'Comissão sobre taxa de ativação', :created_at
                            )
                        """),
                        {
                            "parceiro_id": dados.parceiro_id,
                            "cliente_id": cliente_id,
                            "assinatura_id": assinatura_id,
                            "valor_base": taxa_ativacao,
                            "percentual_aplicado": percentual_comissao,
                            "valor_comissao": comissao_ativacao,
                            "data_referencia": date.today(),
                            "created_at": agora
                        }
                    )
                    logger.info(f"[Aprovacao] Comissão ativação criada: R${comissao_ativacao:.2f} ({percentual_comissao}% de R${taxa_ativacao:.2f})")

                comissao_info = {
                    "parceiro_id": dados.parceiro_id,
                    "parceiro_nome": parceiro[1],
                    "valor_base_mensal": valor_comissionavel,
                    "valor_base_ativacao": taxa_ativacao if not assinatura_dados.ativacao_cortesia else 0,
                    "percentual": percentual_comissao,
                    "comissao_mensal": comissao_mensal,
                    "comissao_ativacao": comissao_ativacao,
                    "total_primeira_comissao": comissao_mensal + comissao_ativacao
                }
            else:
                logger.warning(f"[Aprovacao] Parceiro {dados.parceiro_id} não encontrado ou inativo")

        db.commit()

        # 11. Enviar email de ativacao
        link_ativacao = f"https://horariointeligente.com.br/static/ativar-conta.html?token={token_ativacao}"
        try:
            email_service = get_email_service()
            email_service.send_ativacao_conta(email_cliente, nome_cliente, token_ativacao)
            logger.info(f"[Aprovacao] Email de ativacao enviado para {email_cliente}")
        except Exception as e:
            logger.warning(f"[Aprovacao] Erro ao enviar email de ativacao: {e}")

        # 12. Notificar via Telegram
        try:
            asyncio.create_task(alerta_novo_cliente(
                nome_cliente=nome_cliente,
                plano=plano[2],
                subdomain=subdomain,
                valor_mensal=billing["valor_final"],
                periodo=assinatura_dados.periodo_cobranca
            ))
        except Exception as e:
            logger.warning(f"[Telegram] Erro ao enviar notificacao: {e}")

        # Montar resposta
        response = {
            "success": True,
            "cliente": {
                "id": cliente_id,
                "nome": nome_cliente,
                "subdomain": subdomain,
                "plano": plano[1],
                "plano_nome": plano[2],
                "status": "pendente_aceite"
            },
            "ativacao": {
                "status": "pendente_aceite",
                "link_ativacao": link_ativacao,
                "expira_em": token_expira_em.isoformat(),
                "email_enviado": True
            },
            "assinatura": {
                "valor_base_plano": float(plano[3]),
                "valor_final": billing["valor_final"],
                "periodo_cobranca": assinatura_dados.periodo_cobranca
            },
            "medico_principal": {
                "id": medico_principal[0],
                "nome": medico_principal[1],
                "email": medico_principal[2]
            },
            "credenciais": {
                "url_acesso": f"https://{subdomain}.horariointeligente.com.br",
                "email": medico_principal[2],
                "senha_temporaria": senha_temporaria
            }
        }

        if medicos_adicionais_response:
            response["medicos_adicionais"] = medicos_adicionais_response
        if secretaria_response:
            response["secretaria"] = secretaria_response
        if comissao_info:
            response["comissao"] = comissao_info

        return response

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Aprovacao] Erro ao aprovar cliente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao aprovar cliente: {str(e)}")


@router.post("/clientes/{cliente_id}/rejeitar")
async def rejeitar_cliente(
    cliente_id: int,
    dados: RejeicaoClienteRequest,
    admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Rejeita cliente com status 'pendente_aprovacao'.
    Opcionalmente notifica prospect por email.
    """
    try:
        cliente = db.execute(
            text("SELECT id, nome, email, status FROM clientes WHERE id = :id"),
            {"id": cliente_id}
        ).fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")

        if cliente[3] != 'pendente_aprovacao':
            raise HTTPException(
                status_code=400,
                detail=f"Cliente nao esta pendente de aprovacao (status atual: {cliente[3]})"
            )

        db.execute(
            text("""
                UPDATE clientes
                SET status = 'rejeitado', atualizado_em = :atualizado_em
                WHERE id = :id
            """),
            {"atualizado_em": datetime.now(), "id": cliente_id}
        )
        db.commit()

        logger.info(f"[Aprovacao] Cliente {cliente_id} rejeitado. Motivo: {dados.motivo}")

        # Notificar por email se solicitado
        if dados.notificar_email and cliente[2]:
            try:
                email_service = get_email_service()
                email_service.send_telegram_notification(
                    f"<b>Cliente Rejeitado</b>\n\n"
                    f"<b>Nome:</b> {cliente[1]}\n"
                    f"<b>Motivo:</b> {dados.motivo or 'Nao informado'}\n"
                )
            except Exception as e:
                logger.warning(f"[Aprovacao] Erro ao notificar rejeicao: {e}")

        return {
            "success": True,
            "message": f"Cliente {cliente[1]} rejeitado com sucesso",
            "status": "rejeitado"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[Aprovacao] Erro ao rejeitar cliente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao rejeitar cliente: {str(e)}")
