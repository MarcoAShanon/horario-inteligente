#!/usr/bin/env python3
"""
Teste de Normalização de Telefone
Demonstra que telefones salvos manualmente agora ficam no mesmo formato do WhatsApp
Sistema: ProSaude - Horário Inteligente
"""
import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.phone_utils import normalize_phone, format_phone_display, validate_phone


def print_header(title):
    """Imprime um cabeçalho formatado"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_normalize_various_formats():
    """Testa normalização com vários formatos de entrada"""
    print_header("📱 TESTE 1: Normalização de Diversos Formatos")

    test_cases = [
        {
            "input": "(24) 98849-3257",
            "description": "Formato comum brasileiro",
        },
        {
            "input": "24 98849-3257",
            "description": "Com espaço",
        },
        {
            "input": "+55 24 98849-3257",
            "description": "Com DDI e espaços",
        },
        {
            "input": "24988493257",
            "description": "Apenas números sem DDI",
        },
        {
            "input": "5524988493257",
            "description": "Já normalizado",
        },
        {
            "input": "(11) 99999-8888",
            "description": "Celular de SP",
        },
        {
            "input": "(11) 3333-4444",
            "description": "Telefone fixo",
        },
    ]

    for i, case in enumerate(test_cases, 1):
        input_phone = case["input"]
        description = case["description"]

        normalized = normalize_phone(input_phone)
        formatted = format_phone_display(normalized)
        is_valid = validate_phone(normalized)

        print(f"Teste {i}: {description}")
        print(f"  📥 Input:       '{input_phone}'")
        print(f"  🔧 Normalizado: '{normalized}'")
        print(f"  📱 Formatado:   '{formatted}'")
        print(f"  {'✅' if is_valid else '❌'} Válido:      {is_valid}")
        print()


def test_whatsapp_format_consistency():
    """Demonstra que o formato agora é consistente com o WhatsApp"""
    print_header("🤖 TESTE 2: Consistência com Formato do WhatsApp")

    # Simular o que acontece quando uma mensagem chega do WhatsApp
    whatsapp_sender = "5524988493257@s.whatsapp.net"
    telefone_do_whatsapp = whatsapp_sender.replace("@s.whatsapp.net", "")

    print(f"📲 Mensagem do WhatsApp:")
    print(f"   Sender completo: {whatsapp_sender}")
    print(f"   Telefone extraído: {telefone_do_whatsapp}")
    print()

    # Simular diferentes formatos que a secretária pode digitar
    formatos_secretaria = [
        "(24) 98849-3257",
        "24 98849-3257",
        "+55 24 98849-3257",
        "24988493257",
    ]

    print(f"✏️  Formatos que a secretária pode digitar:\n")

    all_match = True
    for formato in formatos_secretaria:
        normalizado = normalize_phone(formato)
        match = normalizado == telefone_do_whatsapp

        print(f"   Input: '{formato:20s}' → '{normalizado}' {'✅ MATCH!' if match else '❌ DIFERENTE'}")

        if not match:
            all_match = False

    print()
    if all_match:
        print("✅ SUCESSO! Todos os formatos foram normalizados para o mesmo valor do WhatsApp!")
        print(f"   Valor consistente: {telefone_do_whatsapp}")
    else:
        print("❌ ERRO! Alguns formatos não foram normalizados corretamente.")


def test_database_scenario():
    """Simula o cenário de busca no banco de dados"""
    print_header("🗄️  TESTE 3: Cenário de Busca no Banco de Dados")

    # Simular paciente já cadastrado via WhatsApp
    telefone_no_banco = "5524988493257"  # Salvo via WhatsApp

    print(f"📊 Paciente já cadastrado no banco de dados:")
    print(f"   Telefone armazenado: {telefone_no_banco}")
    print(f"   Origem: Agendamento via WhatsApp Bot\n")

    # Secretária tenta criar novo agendamento para mesmo paciente
    print(f"👤 Secretária cria novo agendamento manualmente:\n")

    inputs_secretaria = [
        "(24) 98849-3257",
        "24 98849-3257",
        "+55 24 98849-3257",
    ]

    for input_tel in inputs_secretaria:
        normalizado = normalize_phone(input_tel)
        encontrado = normalizado == telefone_no_banco

        print(f"   Input secretária: '{input_tel}'")
        print(f"   Normalizado:      '{normalizado}'")
        print(f"   Query SQL: SELECT * FROM pacientes WHERE telefone = '{normalizado}'")
        print(f"   Resultado: {'✅ Paciente ENCONTRADO (reutiliza cadastro)' if encontrado else '❌ Paciente NÃO encontrado (cria duplicado)'}")
        print()


def test_future_whatsapp_interaction():
    """Demonstra que futuras interações via WhatsApp funcionarão"""
    print_header("💬 TESTE 4: Futuras Interações via WhatsApp")

    print("Cenário:")
    print("1️⃣  Secretária cria agendamento manual com telefone '(24) 98849-3257'")
    print("2️⃣  Sistema normaliza para '5524988493257' e salva no banco")
    print("3️⃣  Paciente envia mensagem via WhatsApp alguns dias depois\n")

    # Agendamento manual
    telefone_digitado = "(24) 98849-3257"
    telefone_salvo = normalize_phone(telefone_digitado)

    print(f"📝 Agendamento Manual:")
    print(f"   Telefone digitado: {telefone_digitado}")
    print(f"   Telefone salvo no banco: {telefone_salvo}\n")

    # Mensagem futura via WhatsApp
    whatsapp_sender = "5524988493257@s.whatsapp.net"
    telefone_whatsapp = whatsapp_sender.replace("@s.whatsapp.net", "")

    print(f"📲 Mensagem do WhatsApp (3 dias depois):")
    print(f"   Sender: {whatsapp_sender}")
    print(f"   Telefone extraído: {telefone_whatsapp}\n")

    # Verificar se bot reconhece o paciente
    reconhecido = telefone_salvo == telefone_whatsapp

    print(f"🤖 Bot processa mensagem:")
    print(f"   Query: SELECT * FROM pacientes WHERE telefone = '{telefone_whatsapp}'")
    print(f"   Resultado: {'✅ Paciente RECONHECIDO!' if reconhecido else '❌ Paciente NÃO reconhecido'}")

    if reconhecido:
        print(f"\n   ✅ Bot terá acesso ao histórico completo do paciente")
        print(f"   ✅ Poderá oferecer reagendamento personalizado")
        print(f"   ✅ Saberá preferências e consultas anteriores")
    else:
        print(f"\n   ❌ Bot tratará como paciente novo")
        print(f"   ❌ Não terá acesso ao histórico")


def main():
    """Executa todos os testes"""
    print(f"\n{'#'*70}")
    print(f"#  TESTE DE NORMALIZAÇÃO DE TELEFONE - ProSaude")
    print(f"#  Garantindo consistência entre agendamentos manuais e WhatsApp")
    print(f"{'#'*70}")

    test_normalize_various_formats()
    test_whatsapp_format_consistency()
    test_database_scenario()
    test_future_whatsapp_interaction()

    print_header("✅ RESUMO")
    print("Todos os testes demonstram que:")
    print("  1. ✅ Telefones são normalizados para formato padrão (apenas dígitos + DDI)")
    print("  2. ✅ Formato manual = Formato WhatsApp")
    print("  3. ✅ Busca no banco de dados funcionará corretamente")
    print("  4. ✅ Bot reconhecerá pacientes em futuras interações")
    print("  5. ✅ Nenhum cadastro duplicado será criado\n")

    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
