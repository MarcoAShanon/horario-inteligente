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

from app.database import get_db
from app.api.admin import get_current_admin
from app.services.telegram_service import alerta_novo_cliente, alerta_cliente_inativo
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
    desconto_percentual: Optional[float] = None  # Desconto promocional percentual
    desconto_valor_fixo: Optional[float] = None  # Desconto promocional fixo
    desconto_duracao_meses: Optional[int] = None  # Duração do desconto (null=permanente)
    desconto_motivo: Optional[str] = None  # Motivo do desconto


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


# ==================== FUNÇÕES AUXILIARES ====================

def gerar_subdomain(nome: str) -> str:
    """
    Gera subdomain único a partir do nome.
    Ex: "Dr. João Silva" -> "dr-joao-silva"
    """
    # Normalizar unicode (remove acentos)
    nome_normalizado = unicodedata.normalize('NFKD', nome)
    nome_ascii = nome_normalizado.encode('ASCII', 'ignore').decode('ASCII')

    # Converter para minúsculas e substituir espaços/caracteres especiais
    subdomain = nome_ascii.lower()
    subdomain = re.sub(r'[^a-z0-9]+', '-', subdomain)
    subdomain = subdomain.strip('-')

    # Limitar tamanho
    if len(subdomain) > 30:
        subdomain = subdomain[:30].rstrip('-')

    return subdomain


def gerar_senha_temporaria() -> str:
    """Gera senha temporária segura"""
    # Formato: HI@2025 + 4 dígitos aleatórios
    digitos = ''.join([str(secrets.randbelow(10)) for _ in range(4)])
    return f"HI@2025{digitos}"


def hash_senha(senha: str) -> str:
    """Gera hash bcrypt da senha"""
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verificar_subdomain_disponivel(db: Session, subdomain: str) -> bool:
    """Verifica se subdomain está disponível"""
    result = db.execute(
        text("SELECT id FROM clientes WHERE subdomain = :subdomain"),
        {"subdomain": subdomain}
    ).fetchone()
    return result is None


def verificar_email_disponivel(db: Session, email: str, tabela: str = "medicos") -> bool:
    """Verifica se email está disponível"""
    query = text(f"SELECT id FROM {tabela} WHERE email = :email")
    result = db.execute(query, {"email": email}).fetchone()
    return result is None


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

        # 2. Verificar email do médico
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

        # 4. Criar cliente
        agora = datetime.now()
        result_cliente = db.execute(
            text("""
                INSERT INTO clientes (
                    nome, cnpj, email, telefone, endereco,
                    subdomain, plano, ativo, valor_mensalidade,
                    logo_icon, cor_primaria, cor_secundaria,
                    criado_em, atualizado_em
                ) VALUES (
                    :nome, :cnpj, :email, :telefone, :endereco,
                    :subdomain, :plano, true, :valor_mensalidade,
                    'fa-heartbeat', '#3b82f6', '#1e40af',
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
                "criado_em": agora,
                "atualizado_em": agora
            }
        )
        cliente_id = result_cliente.fetchone()[0]
        logger.info(f"[Onboarding] Cliente criado: ID={cliente_id}")

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

        # Adicional linha WhatsApp dedicada (+R$40)
        valor_linha_dedicada = 40.0 if assinatura_dados.linha_dedicada else 0.0

        # Valor original (antes de descontos)
        valor_original = valor_base_plano + valor_extras_profissionais + valor_linha_dedicada

        # Aplicar desconto do período
        percentual_periodo = assinatura_dados.percentual_periodo or 0
        valor_apos_desconto_periodo = valor_original * (1 - percentual_periodo / 100)

        # Aplicar desconto promocional
        valor_final = valor_apos_desconto_periodo
        if assinatura_dados.desconto_percentual and assinatura_dados.desconto_percentual > 0:
            valor_final = valor_final * (1 - assinatura_dados.desconto_percentual / 100)
        elif assinatura_dados.desconto_valor_fixo and assinatura_dados.desconto_valor_fixo > 0:
            valor_final = max(0, valor_final - assinatura_dados.desconto_valor_fixo)

        # Calcular data fim do desconto promocional
        data_fim_desconto = None
        if assinatura_dados.desconto_duracao_meses and assinatura_dados.desconto_duracao_meses > 0:
            from datetime import timedelta
            # Aproximação: 30 dias por mês
            dias = assinatura_dados.desconto_duracao_meses * 30
            data_fim_desconto = date.today() + timedelta(days=dias)

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
                    criado_em
                ) VALUES (
                    :cliente_id, :plano_id, :valor_mensal,
                    :profissionais, :taxa_ativacao,
                    :data_inicio, 'pendente', 10,
                    :periodo_cobranca, :percentual_periodo,
                    :valor_original, :valor_com_desconto,
                    :desconto_percentual, :desconto_valor_fixo,
                    :desconto_duracao_meses, :desconto_motivo,
                    :data_fim_desconto, :linha_dedicada,
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
                valor_comissao = valor_final * (percentual_comissao / 100)

                # Criar registro de comissão
                db.execute(
                    text("""
                        INSERT INTO comissoes (
                            parceiro_id, cliente_id, assinatura_id,
                            valor_base, percentual_aplicado, valor_comissao,
                            mes_referencia, data_referencia, status,
                            created_at
                        ) VALUES (
                            :parceiro_id, :cliente_id, :assinatura_id,
                            :valor_base, :percentual_aplicado, :valor_comissao,
                            1, :data_referencia, 'pendente',
                            :created_at
                        )
                    """),
                    {
                        "parceiro_id": dados.parceiro_id,
                        "cliente_id": cliente_id,
                        "assinatura_id": assinatura_id,
                        "valor_base": valor_final,
                        "percentual_aplicado": percentual_comissao,
                        "valor_comissao": valor_comissao,
                        "data_referencia": date.today(),
                        "created_at": agora
                    }
                )
                logger.info(f"[Onboarding] Comissão criada: R${valor_comissao:.2f} ({percentual_comissao}% de R${valor_final:.2f})")

                comissao_info = {
                    "parceiro_id": dados.parceiro_id,
                    "parceiro_nome": parceiro[1],
                    "valor_base": valor_final,
                    "percentual": percentual_comissao,
                    "valor_comissao": valor_comissao,
                    "tipo_parceria": tipo_parceria,
                    "ordem_cliente": ordem_cliente
                }
            else:
                logger.warning(f"[Onboarding] Parceiro {dados.parceiro_id} não encontrado ou inativo")

        # 8. Commit da transação
        db.commit()

        # 9. Log de auditoria
        try:
            db.execute(
                text("""
                    INSERT INTO log_auditoria (
                        tabela, registro_id, acao, dados_novos,
                        usuario_id, usuario_tipo, ip_address, criado_em
                    ) VALUES (
                        'clientes', :registro_id, 'INSERT', :dados,
                        :usuario_id, 'admin', :ip, :criado_em
                    )
                """),
                {
                    "registro_id": cliente_id,
                    "dados": f'{{"nome": "{dados.nome_fantasia}", "plano": "{plano[1]}", "medico": "{dados.medico_principal.nome}"}}',
                    "usuario_id": admin.get("id"),
                    "ip": request.client.host if request.client else "unknown",
                    "criado_em": agora
                }
            )
            db.commit()
        except Exception as e:
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

        # Montar resposta
        response = {
            "success": True,
            "cliente": {
                "id": cliente_id,
                "nome": dados.nome_fantasia,
                "subdomain": subdomain,
                "plano": plano[1],
                "plano_nome": plano[2]
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
                "Enviar credenciais ao cliente por email/WhatsApp",
                "Configurar número WhatsApp na WABA (Meta Business)",
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

        # Atualizar status
        db.execute(
            text("UPDATE clientes SET ativo = :ativo, atualizado_em = :atualizado_em WHERE id = :id"),
            {"id": cliente_id, "ativo": dados.ativo, "atualizado_em": datetime.now()}
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
