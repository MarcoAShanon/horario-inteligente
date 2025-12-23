"""
Utilitários para normalização de telefone
Arquivo: app/utils/phone_utils.py
Sistema Horário Inteligente
"""
import re


def normalize_phone(phone: str) -> str:
    """
    Normaliza número de telefone para o formato do WhatsApp
    Remove todos os caracteres não numéricos e garante DDI 55 (Brasil)

    Exemplos:
        (24) 98849-3257      → 5524988493257
        24 98849-3257        → 5524988493257
        +55 24 98849-3257    → 5524988493257
        5524988493257        → 5524988493257
        11999998888          → 5511999998888

    Args:
        phone: Número de telefone em qualquer formato

    Returns:
        Número normalizado com DDI (apenas dígitos)
    """
    if not phone:
        return ""

    # Remover todos os caracteres não numéricos
    phone_digits = re.sub(r'\D', '', phone)

    # Se já começa com 55 (DDI Brasil), retornar como está
    if phone_digits.startswith('55'):
        return phone_digits

    # Se não tem DDI, adicionar 55
    # Telefone brasileiro: DDD (2 dígitos) + número (8 ou 9 dígitos)
    # Total: 10 ou 11 dígitos sem DDI
    if len(phone_digits) >= 10:
        return '55' + phone_digits

    # Se for muito curto, retornar como está (pode ser inválido)
    return phone_digits


def format_phone_display(phone: str) -> str:
    """
    Formata telefone para exibição amigável

    Exemplos:
        5524988493257 → +55 (24) 98849-3257
        5511999998888 → +55 (11) 99999-8888

    Args:
        phone: Número normalizado (apenas dígitos)

    Returns:
        Número formatado para exibição
    """
    if not phone:
        return ""

    # Remover caracteres não numéricos
    phone_digits = re.sub(r'\D', '', phone)

    # Se não tiver pelo menos 12 dígitos (55 + DDD + número), retornar original
    if len(phone_digits) < 12:
        return phone

    # Extrair partes: DDI (2) + DDD (2) + Número (8 ou 9)
    ddi = phone_digits[:2]
    ddd = phone_digits[2:4]
    numero = phone_digits[4:]

    # Formatar número baseado no tamanho
    if len(numero) == 9:  # Celular (9 dígitos)
        numero_formatado = f"{numero[:5]}-{numero[5:]}"
    elif len(numero) == 8:  # Fixo (8 dígitos)
        numero_formatado = f"{numero[:4]}-{numero[4:]}"
    else:
        numero_formatado = numero

    return f"+{ddi} ({ddd}) {numero_formatado}"


def validate_phone(phone: str) -> bool:
    """
    Valida se o telefone está em formato válido

    Args:
        phone: Número de telefone

    Returns:
        True se válido, False caso contrário
    """
    if not phone:
        return False

    # Normalizar
    phone_normalized = normalize_phone(phone)

    # Telefone brasileiro completo: 55 (DDI) + DDD (2) + número (8 ou 9)
    # Total: 12 ou 13 dígitos
    if not phone_normalized.startswith('55'):
        return False

    length = len(phone_normalized)
    return length == 12 or length == 13


# Testes da função (executar apenas em desenvolvimento)
if __name__ == "__main__":
    # Casos de teste
    test_cases = [
        ("(24) 98849-3257", "5524988493257"),
        ("24 98849-3257", "5524988493257"),
        ("+55 24 98849-3257", "5524988493257"),
        ("5524988493257", "5524988493257"),
        ("11999998888", "5511999998888"),
        ("+55 11 99999-8888", "5511999998888"),
        ("(11) 3333-4444", "55113333444"),  # Fixo
    ]

    print("🧪 Testando normalização de telefone:\n")
    for input_phone, expected in test_cases:
        result = normalize_phone(input_phone)
        status = "✅" if result == expected else "❌"
        print(f"{status} Input: '{input_phone}' → Output: '{result}' (esperado: '{expected}')")

    print("\n🧪 Testando formatação para exibição:\n")
    display_cases = [
        "5524988493257",
        "5511999998888",
        "551133334444"
    ]

    for phone in display_cases:
        formatted = format_phone_display(phone)
        print(f"📱 {phone} → {formatted}")

    print("\n🧪 Testando validação:\n")
    validation_cases = [
        ("5524988493257", True),
        ("11999998888", False),  # Sem DDI
        ("invalid", False),
        ("+55 11 99999-8888", True),
    ]

    for phone, expected in validation_cases:
        result = validate_phone(phone)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{phone}' → válido={result} (esperado: {expected})")
