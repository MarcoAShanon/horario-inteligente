"""
Service layer para operações de gestão de clientes no painel admin.
Extrai lógica de negócio dos endpoints para reutilização e testabilidade.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import secrets
import logging

from app.services.onboarding_service import (
    gerar_subdomain, gerar_senha_temporaria, hash_senha,
    verificar_subdomain_disponivel, verificar_email_disponivel,
    calcular_billing
)

logger = logging.getLogger(__name__)


def criar_medico_com_senha(
    db: Session,
    cliente_id: int,
    nome: str,
    email: str,
    especialidade: str,
    registro: str,
    telefone: str = None,
    is_secretaria: bool = False,
    is_admin: bool = False,
    pode_ver_financeiro: bool = True,
    agora: datetime = None
):
    """
    Cria médico/secretária na tabela medicos com senha temporária.

    Retorna: (medico_id, senha_temporaria)
    """
    if agora is None:
        agora = datetime.now()

    senha_temporaria = gerar_senha_temporaria()
    senha_hash = hash_senha(senha_temporaria)

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
                true, :is_admin, true,
                :is_secretaria, :pode_ver_financeiro,
                :criado_em, :atualizado_em
            )
            RETURNING id
        """),
        {
            "cliente_id": cliente_id,
            "nome": nome,
            "crm": registro,
            "especialidade": especialidade,
            "email": email,
            "telefone": telefone,
            "senha": senha_hash,
            "is_admin": is_admin,
            "is_secretaria": is_secretaria,
            "pode_ver_financeiro": pode_ver_financeiro,
            "criado_em": agora,
            "atualizado_em": agora
        }
    )
    medico_id = result.fetchone()[0]
    return medico_id, senha_temporaria


def vincular_parceiro_e_comissoes(
    db: Session,
    cliente_id: int,
    parceiro_id: int,
    assinatura_id: int,
    assinatura_dados,
    plano,
    total_profissionais: int,
    agora: datetime = None,
    verificar_existente: bool = False
):
    """
    Cria vínculo cliente-parceiro e registros de comissão.

    Args:
        plano: row do banco (id, codigo, nome, valor_mensal, profissionais_inclusos, taxa_ativacao)
        assinatura_dados: AssinaturaOnboarding com dados da assinatura
        verificar_existente: Se True, verifica vínculo existente antes de criar (usado na aprovação)

    Retorna: dict comissao_info ou None se parceiro inválido
    """
    if agora is None:
        agora = datetime.now()

    parceiro = db.execute(
        text("""
            SELECT id, nome, percentual_comissao, tipo_comissao, parceria_lancamento, limite_clientes_lancamento
            FROM parceiros_comerciais
            WHERE id = :parceiro_id AND ativo = true
        """),
        {"parceiro_id": parceiro_id}
    ).fetchone()

    if not parceiro:
        logger.warning(f"Parceiro {parceiro_id} não encontrado ou inativo")
        return None

    if verificar_existente:
        vinculo_existente = db.execute(
            text("SELECT id FROM clientes_parceiros WHERE cliente_id = :cid AND parceiro_id = :pid"),
            {"cid": cliente_id, "pid": parceiro_id}
        ).fetchone()
    else:
        vinculo_existente = None

    if not vinculo_existente:
        clientes_parceiro = db.execute(
            text("SELECT COUNT(*) FROM clientes_parceiros WHERE parceiro_id = :parceiro_id AND ativo = true"),
            {"parceiro_id": parceiro_id}
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
                "parceiro_id": parceiro_id,
                "data_vinculo": date.today(),
                "tipo_parceria": tipo_parceria,
                "ordem_cliente": ordem_cliente,
                "criado_em": agora
            }
        )
        logger.info(f"Vínculo cliente-parceiro criado: cliente {cliente_id} -> parceiro {parceiro_id}")
    else:
        ordem_cliente = None
        tipo_parceria = None

    # Calcular comissões
    percentual_comissao = float(parceiro[2]) if parceiro[2] else 40.0

    valor_base_plano = float(plano[3])
    profissionais_inclusos = plano[4]
    profissionais_extras = max(0, total_profissionais - profissionais_inclusos)
    valor_extras_profissionais = profissionais_extras * 50.0
    valor_comissionavel = valor_base_plano + valor_extras_profissionais
    comissao_mensal = valor_comissionavel * (percentual_comissao / 100)

    taxa_ativacao = float(plano[5]) if plano[5] else 150.0
    comissao_ativacao = 0.0 if assinatura_dados.ativacao_cortesia else taxa_ativacao * (percentual_comissao / 100)

    # Comissão mensal (mes_referencia=1)
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
            "parceiro_id": parceiro_id,
            "cliente_id": cliente_id,
            "assinatura_id": assinatura_id,
            "valor_base": valor_comissionavel,
            "percentual_aplicado": percentual_comissao,
            "valor_comissao": comissao_mensal,
            "data_referencia": date.today(),
            "created_at": agora
        }
    )
    logger.info(f"Comissão mensal criada: R${comissao_mensal:.2f} ({percentual_comissao}% de R${valor_comissionavel:.2f})")

    # Comissão sobre ativação (mes_referencia=0)
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
                "parceiro_id": parceiro_id,
                "cliente_id": cliente_id,
                "assinatura_id": assinatura_id,
                "valor_base": taxa_ativacao,
                "percentual_aplicado": percentual_comissao,
                "valor_comissao": comissao_ativacao,
                "data_referencia": date.today(),
                "created_at": agora
            }
        )
        logger.info(f"Comissão ativação criada: R${comissao_ativacao:.2f} ({percentual_comissao}% de R${taxa_ativacao:.2f})")

    comissao_info = {
        "parceiro_id": parceiro_id,
        "parceiro_nome": parceiro[1],
        "valor_base_mensal": valor_comissionavel,
        "valor_base_ativacao": taxa_ativacao if not assinatura_dados.ativacao_cortesia else 0,
        "percentual": percentual_comissao,
        "comissao_mensal": comissao_mensal,
        "comissao_ativacao": comissao_ativacao,
        "total_primeira_comissao": comissao_mensal + comissao_ativacao,
    }

    if tipo_parceria is not None:
        comissao_info["tipo_parceria"] = tipo_parceria
        comissao_info["ordem_cliente"] = ordem_cliente

    return comissao_info


def executar_onboarding_cliente(db: Session, dados, admin_id: int):
    """
    Executa todo o fluxo de criação de cliente (onboarding).

    NÃO envia email/Telegram — o endpoint cuida dos side-effects.

    Retorna: dict com dados do cliente, credenciais, info de comissão, etc.
    """
    from app.api.admin_clientes.schemas import AssinaturaOnboarding

    logger.info(f"[Onboarding] Iniciando criação de cliente: {dados.nome_fantasia}")

    # 1. Gerar e validar subdomain
    subdomain_base = gerar_subdomain(dados.nome_fantasia)
    subdomain = subdomain_base
    contador = 1

    while not verificar_subdomain_disponivel(db, subdomain):
        subdomain = f"{subdomain_base}-{contador}"
        contador += 1
        if contador > 10:
            raise ValueError("Não foi possível gerar subdomain único. Tente outro nome.")

    logger.info(f"[Onboarding] Subdomain gerado: {subdomain}")

    # 2. Verificar documento duplicado
    doc_existente = db.execute(
        text("SELECT id, nome FROM clientes WHERE cnpj = :cnpj"),
        {"cnpj": dados.documento}
    ).fetchone()
    if doc_existente:
        raise ValueError(
            f"CPF/CNPJ {dados.documento} já está cadastrado (Cliente: {doc_existente[1]}, ID: {doc_existente[0]})"
        )

    # 2b. Verificar email do médico
    if not verificar_email_disponivel(db, dados.medico_principal.email, "medicos"):
        raise ValueError(f"Email {dados.medico_principal.email} já está em uso por outro profissional")

    # 3. Buscar plano
    plano = db.execute(
        text("SELECT id, codigo, nome, valor_mensal, profissionais_inclusos, taxa_ativacao FROM planos WHERE id = :id AND ativo = true"),
        {"id": dados.plano_id}
    ).fetchone()

    if not plano:
        raise ValueError(f"Plano {dados.plano_id} não encontrado ou inativo")

    # 4. Criar cliente
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
            "plano": plano[1],
            "valor_mensalidade": str(plano[3]),
            "token_ativacao": token_ativacao,
            "token_expira_em": token_expira_em,
            "cadastrado_por_id": admin_id,
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
    medico_id, senha_temporaria = criar_medico_com_senha(
        db, cliente_id,
        nome=dados.medico_principal.nome,
        email=dados.medico_principal.email,
        especialidade=dados.medico_principal.especialidade,
        registro=dados.medico_principal.registro_profissional,
        telefone=dados.medico_principal.telefone,
        is_secretaria=False,
        is_admin=True,
        pode_ver_financeiro=True,
        agora=agora
    )
    logger.info(f"[Onboarding] Médico principal criado: ID={medico_id}")

    # 7. Calcular billing e criar assinatura
    assinatura_dados = dados.assinatura or AssinaturaOnboarding()

    total_profissionais = 1
    if dados.medicos_adicionais:
        total_profissionais += len(dados.medicos_adicionais)

    billing = calcular_billing(
        valor_base_plano=float(plano[3]),
        profissionais_inclusos=plano[4],
        total_profissionais=total_profissionais,
        assinatura_dados=assinatura_dados
    )

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
    logger.info(f"[Onboarding] Assinatura criada para cliente {cliente_id}: R${billing['valor_final']:.2f}/mês (original: R${billing['valor_original']:.2f})")

    # 7.5 Buscar ID da assinatura
    assinatura_result = db.execute(
        text("SELECT id FROM assinaturas WHERE cliente_id = :cliente_id ORDER BY criado_em DESC LIMIT 1"),
        {"cliente_id": cliente_id}
    ).fetchone()
    assinatura_id = assinatura_result[0] if assinatura_result else None

    # 7.6 Vincular parceiro
    comissao_info = None
    if dados.parceiro_id:
        comissao_info = vincular_parceiro_e_comissoes(
            db, cliente_id, dados.parceiro_id, assinatura_id,
            assinatura_dados, plano, total_profissionais,
            agora=agora, verificar_existente=False
        )

    # 8. Commit
    db.commit()

    # 9. Log de auditoria (não-crítico)
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
                "usuario_id": admin_id,
                "ip": "api",
                "criado_em": agora
            }
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"[Onboarding] Erro ao criar log de auditoria: {e}")

    logger.info(f"[Onboarding] ✅ Cliente {dados.nome_fantasia} criado com sucesso!")

    # 10. Criar médicos adicionais
    medicos_adicionais_response = []
    if dados.medicos_adicionais:
        for med in dados.medicos_adicionais:
            med_id, med_senha = criar_medico_com_senha(
                db, cliente_id,
                nome=med.nome,
                email=med.email,
                especialidade=med.especialidade,
                registro=med.registro_profissional,
                telefone=med.telefone,
                is_secretaria=False,
                is_admin=False,
                pode_ver_financeiro=True,
                agora=agora
            )
            medicos_adicionais_response.append({
                "id": med_id,
                "nome": med.nome,
                "email": med.email,
                "senha_temporaria": med_senha
            })
            logger.info(f"[Onboarding] Médico adicional criado: {med.nome} (ID={med_id})")
        db.commit()

    # 11. Criar secretária
    secretaria_response = None
    if dados.secretaria:
        sec_id, sec_senha = criar_medico_com_senha(
            db, cliente_id,
            nome=dados.secretaria.nome,
            email=dados.secretaria.email,
            especialidade='Secretária',
            registro='N/A',
            telefone=dados.secretaria.telefone,
            is_secretaria=True,
            is_admin=False,
            pode_ver_financeiro=False,
            agora=agora
        )
        db.commit()
        secretaria_response = {
            "id": sec_id,
            "nome": dados.secretaria.nome,
            "email": dados.secretaria.email,
            "senha_temporaria": sec_senha,
            "tipo": "secretaria"
        }
        logger.info(f"[Onboarding] Secretária criada: {dados.secretaria.nome} (ID={sec_id})")

    return {
        "cliente_id": cliente_id,
        "subdomain": subdomain,
        "plano": plano,
        "token_ativacao": token_ativacao,
        "token_expira_em": token_expira_em,
        "medico_id": medico_id,
        "senha_temporaria": senha_temporaria,
        "medico_principal_nome": dados.medico_principal.nome,
        "medico_principal_email": dados.medico_principal.email,
        "billing": billing,
        "assinatura_dados": assinatura_dados,
        "comissao_info": comissao_info,
        "medicos_adicionais_response": medicos_adicionais_response,
        "secretaria_response": secretaria_response,
        "nome_fantasia": dados.nome_fantasia,
        "email": dados.email,
    }


def executar_aprovacao_cliente(db: Session, cliente_id: int, dados):
    """
    Executa todo o fluxo de aprovação de cliente pendente.

    NÃO envia email/Telegram — o endpoint cuida dos side-effects.

    Retorna: dict com dados completos para resposta.
    """
    from app.api.admin_clientes.schemas import AssinaturaOnboarding

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
        raise ValueError("Cliente nao encontrado")

    if cliente[4] != 'pendente_aprovacao':
        raise ValueError(f"Cliente nao esta pendente de aprovacao (status atual: {cliente[4]})")

    nome_cliente = cliente[1]
    email_cliente = cliente[2]
    subdomain = cliente[3]

    # 2. Buscar plano
    plano = db.execute(
        text("SELECT id, codigo, nome, valor_mensal, profissionais_inclusos, taxa_ativacao FROM planos WHERE id = :id AND ativo = true"),
        {"id": dados.plano_id}
    ).fetchone()

    if not plano:
        raise ValueError(f"Plano {dados.plano_id} nao encontrado ou inativo")

    # 3. Buscar médico principal
    medico_principal = db.execute(
        text("""
            SELECT id, nome, email FROM medicos
            WHERE cliente_id = :cliente_id AND is_secretaria = false
            ORDER BY criado_em ASC LIMIT 1
        """),
        {"cliente_id": cliente_id}
    ).fetchone()

    if not medico_principal:
        raise ValueError("Medico principal nao encontrado para este cliente")

    agora = datetime.now()

    # 4. Gerar senha e atualizar médico principal
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
    total_profissionais = 1
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

    # 6. Criar médicos adicionais
    medicos_adicionais_response = []
    if dados.medicos_adicionais:
        for med in dados.medicos_adicionais:
            med_id, med_senha = criar_medico_com_senha(
                db, cliente_id,
                nome=med.nome,
                email=med.email,
                especialidade=med.especialidade,
                registro=med.registro_profissional,
                telefone=med.telefone,
                is_secretaria=False,
                is_admin=False,
                pode_ver_financeiro=True,
                agora=agora
            )
            medicos_adicionais_response.append({
                "id": med_id,
                "nome": med.nome,
                "email": med.email,
                "senha_temporaria": med_senha
            })

    # 7. Criar secretária
    secretaria_response = None
    if dados.secretaria:
        sec_id, sec_senha = criar_medico_com_senha(
            db, cliente_id,
            nome=dados.secretaria.nome,
            email=dados.secretaria.email,
            especialidade='Secretaria',
            registro='N/A',
            telefone=dados.secretaria.telefone,
            is_secretaria=True,
            is_admin=False,
            pode_ver_financeiro=False,
            agora=agora
        )
        secretaria_response = {
            "id": sec_id,
            "nome": dados.secretaria.nome,
            "email": dados.secretaria.email,
            "senha_temporaria": sec_senha
        }

    # 8. Criar configuração default
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

    # 9. Gerar token de ativação e atualizar status
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

    # 10. Vincular parceiro e criar comissões
    comissao_info = None
    if dados.parceiro_id:
        comissao_info = vincular_parceiro_e_comissoes(
            db, cliente_id, dados.parceiro_id, assinatura_id,
            assinatura_dados, plano, total_profissionais,
            agora=agora, verificar_existente=True
        )

    db.commit()

    return {
        "cliente_id": cliente_id,
        "nome_cliente": nome_cliente,
        "email_cliente": email_cliente,
        "subdomain": subdomain,
        "plano": plano,
        "token_ativacao": token_ativacao,
        "token_expira_em": token_expira_em,
        "medico_principal": medico_principal,
        "senha_temporaria": senha_temporaria,
        "billing": billing,
        "assinatura_dados": assinatura_dados,
        "comissao_info": comissao_info,
        "medicos_adicionais_response": medicos_adicionais_response,
        "secretaria_response": secretaria_response,
    }
