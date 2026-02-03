"""
Servico de Onboarding - Funcoes auxiliares para criacao de clientes
Extraido de app/api/admin_clientes.py para reutilizacao
"""
import re
import secrets
import unicodedata
import bcrypt
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import date, timedelta

logger = logging.getLogger(__name__)


# ==================== GERACAO DE SUBDOMAIN ====================

def gerar_subdomain(nome: str) -> str:
    """
    Gera subdomain unico a partir do nome.
    Ex: "Dr. Joao Silva" -> "dr-joao-silva"
    """
    # Normalizar unicode (remove acentos)
    nome_normalizado = unicodedata.normalize('NFKD', nome)
    nome_ascii = nome_normalizado.encode('ASCII', 'ignore').decode('ASCII')

    # Converter para minusculas e substituir espacos/caracteres especiais
    subdomain = nome_ascii.lower()
    subdomain = re.sub(r'[^a-z0-9]+', '-', subdomain)
    subdomain = subdomain.strip('-')

    # Limitar tamanho
    if len(subdomain) > 30:
        subdomain = subdomain[:30].rstrip('-')

    return subdomain


def verificar_subdomain_disponivel(db: Session, subdomain: str) -> bool:
    """Verifica se subdomain esta disponivel"""
    result = db.execute(
        text("SELECT id FROM clientes WHERE subdomain = :subdomain"),
        {"subdomain": subdomain}
    ).fetchone()
    return result is None


def gerar_subdomain_unico(db: Session, nome: str) -> str:
    """Gera e valida um subdomain unico, adicionando sufixo numerico se necessario"""
    subdomain_base = gerar_subdomain(nome)
    subdomain = subdomain_base
    contador = 1

    while not verificar_subdomain_disponivel(db, subdomain):
        subdomain = f"{subdomain_base}-{contador}"
        contador += 1
        if contador > 10:
            raise ValueError("Nao foi possivel gerar subdomain unico. Tente outro nome.")

    return subdomain


# ==================== SENHAS ====================

def gerar_senha_temporaria() -> str:
    """Gera senha temporaria segura"""
    # Formato: HI@ + 8 caracteres alfanumericos (2.8 trilhoes de combinacoes)
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    codigo = ''.join([chars[secrets.randbelow(len(chars))] for _ in range(8)])
    return f"HI@{codigo}"


def hash_senha(senha: str) -> str:
    """Gera hash bcrypt da senha"""
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# ==================== VERIFICACOES ====================

TABELAS_EMAIL_VALIDAS = {"medicos", "usuarios", "super_admins"}


def verificar_email_disponivel(db: Session, email: str, tabela: str = "medicos") -> bool:
    """Verifica se email esta disponivel"""
    if tabela not in TABELAS_EMAIL_VALIDAS:
        raise ValueError(f"Tabela invalida para verificacao de email: {tabela}")
    query = text(f"SELECT id FROM {tabela} WHERE email = :email")
    result = db.execute(query, {"email": email}).fetchone()
    return result is None


# ==================== CALCULO DE BILLING ====================

def calcular_billing(valor_base_plano: float, profissionais_inclusos: int,
                     total_profissionais: int, assinatura_dados) -> dict:
    """
    Calcula valores de billing para assinatura.

    Args:
        valor_base_plano: Valor mensal base do plano
        profissionais_inclusos: Quantidade de profissionais inclusos no plano
        total_profissionais: Total de profissionais contratados
        assinatura_dados: Objeto com dados da assinatura (AssinaturaOnboarding)

    Returns:
        Dict com todos os valores calculados
    """
    # Calcular profissionais extras (R$50 cada)
    profissionais_extras = max(0, total_profissionais - profissionais_inclusos)
    valor_extras_profissionais = profissionais_extras * 50.0

    # Adicional linha WhatsApp dedicada (+R$40)
    valor_linha_dedicada = 40.0 if assinatura_dados.linha_dedicada else 0.0

    # Subtotal descontavel (sem linha dedicada)
    subtotal_descontavel = valor_base_plano + valor_extras_profissionais

    # Valor original (para registro, antes de descontos)
    valor_original = subtotal_descontavel + valor_linha_dedicada

    # Aplicar desconto do periodo apenas sobre plano + extras
    percentual_periodo = assinatura_dados.percentual_periodo or 0
    valor_apos_desconto_periodo = subtotal_descontavel * (1 - percentual_periodo / 100)
    valor_apos_desconto_periodo += valor_linha_dedicada

    # Aplicar desconto promocional
    valor_final = valor_apos_desconto_periodo
    if assinatura_dados.desconto_percentual and assinatura_dados.desconto_percentual > 0:
        valor_final = valor_final * (1 - assinatura_dados.desconto_percentual / 100)
    elif assinatura_dados.desconto_valor_fixo and assinatura_dados.desconto_valor_fixo > 0:
        valor_final = max(0, valor_final - assinatura_dados.desconto_valor_fixo)

    # Calcular data fim do desconto promocional
    data_fim_desconto = None
    if assinatura_dados.desconto_duracao_meses and assinatura_dados.desconto_duracao_meses > 0:
        dias = assinatura_dados.desconto_duracao_meses * 30
        data_fim_desconto = date.today() + timedelta(days=dias)

    # Cortesia na taxa de ativacao
    desconto_ativacao_pct = 100 if assinatura_dados.ativacao_cortesia else 0
    motivo_desconto_ativacao = "Cortesia" if assinatura_dados.ativacao_cortesia else None

    return {
        "profissionais_extras": profissionais_extras,
        "valor_extras_profissionais": valor_extras_profissionais,
        "valor_linha_dedicada": valor_linha_dedicada,
        "valor_original": valor_original,
        "percentual_periodo": percentual_periodo,
        "valor_final": valor_final,
        "data_fim_desconto": data_fim_desconto,
        "desconto_ativacao_pct": desconto_ativacao_pct,
        "motivo_desconto_ativacao": motivo_desconto_ativacao,
    }
