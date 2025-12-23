#!/usr/bin/env python3
"""
Script de Onboarding de Novo Cliente
Sistema ProSaúde Multi-Tenant
Versão: 1.0.0

Uso:
    python scripts/onboard_cliente.py

Ou:
    python scripts/onboard_cliente.py --nome "Clínica São Lucas" --subdomain "saolucas" --email "contato@saolucas.com.br"
"""

import sys
import os
from datetime import datetime
import argparse

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.cliente import Cliente
from app.models.medico import Medico
from app.models.configuracao import Configuracao
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def criar_cliente(nome, subdomain, email, cor_primaria="#3b82f6", cor_secundaria="#1e40af", logo_icon="fa-hospital"):
    """Cria um novo cliente no sistema"""
    db = SessionLocal()

    try:
        # Verificar se subdomínio já existe
        existe = db.query(Cliente).filter(Cliente.subdomain == subdomain).first()
        if existe:
            print(f"❌ Erro: Subdomínio '{subdomain}' já está em uso!")
            return None

        # Criar cliente
        cliente = Cliente(
            nome=nome,
            subdomain=subdomain,
            email=email,
            logo_icon=logo_icon,
            cor_primaria=cor_primaria,
            cor_secundaria=cor_secundaria,
            whatsapp_instance=subdomain.capitalize(),
            plano="profissional",
            ativo=True
        )

        db.add(cliente)
        db.commit()
        db.refresh(cliente)

        print(f"✅ Cliente criado com sucesso!")
        print(f"   ID: {cliente.id}")
        print(f"   Nome: {cliente.nome}")
        print(f"   Subdomínio: {cliente.subdomain}")
        print(f"   URL: https://{cliente.subdomain}.horariointeligente.com.br")

        return cliente

    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar cliente: {e}")
        return None
    finally:
        db.close()


def adicionar_medico(cliente_id, nome, email, especialidade, crm, telefone=None):
    """Adiciona um médico ao cliente"""
    db = SessionLocal()

    try:
        medico = Medico(
            nome=nome,
            email=email,
            especialidade=especialidade,
            crm=crm,
            telefone=telefone,
            cliente_id=cliente_id
        )

        db.add(medico)
        db.commit()
        db.refresh(medico)

        # Criar configuração padrão de agenda
        config = Configuracao(
            medico_id=medico.id,
            cliente_id=cliente_id,
            intervalo_consulta=30,
            horario_inicio="08:00",
            horario_fim="18:00",
            dias_atendimento="1,2,3,4,5"  # Segunda a sexta
        )

        db.add(config)
        db.commit()

        print(f"✅ Médico adicionado:")
        print(f"   Nome: {medico.nome}")
        print(f"   Email: {medico.email}")
        print(f"   Especialidade: {medico.especialidade}")

        return medico

    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao adicionar médico: {e}")
        return None
    finally:
        db.close()


def criar_usuario_admin(cliente_id, nome, email, senha, tipo="secretaria"):
    """Cria um usuário administrador para o cliente"""
    db = SessionLocal()

    try:
        from app.models.usuario import Usuario

        # Verificar se email já existe
        existe = db.query(Usuario).filter(Usuario.email == email).first()
        if existe:
            print(f"⚠️ Email '{email}' já cadastrado!")
            return None

        usuario = Usuario(
            nome=nome,
            email=email,
            senha=pwd_context.hash(senha),
            tipo=tipo,
            cliente_id=cliente_id,
            ativo=True
        )

        db.add(usuario)
        db.commit()
        db.refresh(usuario)

        print(f"✅ Usuário criado:")
        print(f"   Nome: {usuario.nome}")
        print(f"   Email: {usuario.email}")
        print(f"   Tipo: {usuario.tipo}")
        print(f"   Senha: {senha}")

        return usuario

    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar usuário: {e}")
        return None
    finally:
        db.close()


def onboarding_completo_interativo():
    """Onboarding completo com perguntas interativas"""
    print("=" * 70)
    print("🚀 ONBOARDING DE NOVO CLIENTE - SISTEMA PROSAÚDE")
    print("=" * 70)
    print()

    # Dados do cliente
    print("📋 DADOS DA CLÍNICA:")
    nome = input("Nome da clínica: ").strip()
    subdomain = input("Subdomínio (ex: saolucas): ").strip().lower()
    email = input("Email da clínica: ").strip()

    print()
    print("🎨 PERSONALIZAÇÃO (pressione Enter para usar padrão):")
    cor_primaria = input("Cor primária (hex, ex: #10b981): ").strip() or "#3b82f6"
    cor_secundaria = input("Cor secundária (hex, ex: #059669): ").strip() or "#1e40af"
    logo_icon = input("Ícone FontAwesome (ex: fa-hospital): ").strip() or "fa-hospital"

    print()
    print("🏥 Criando cliente...")
    cliente = criar_cliente(nome, subdomain, email, cor_primaria, cor_secundaria, logo_icon)

    if not cliente:
        return

    # Adicionar médicos
    print()
    print("👨‍⚕️ CADASTRO DE MÉDICOS:")
    adicionar_mais = True

    while adicionar_mais:
        print()
        medico_nome = input("Nome do médico: ").strip()
        medico_email = input("Email do médico: ").strip()
        medico_especialidade = input("Especialidade: ").strip()
        medico_crm = input("CRM (ex: CRM-SP 123456): ").strip()
        medico_telefone = input("Telefone (opcional): ").strip() or None

        adicionar_medico(cliente.id, medico_nome, medico_email, medico_especialidade, medico_crm, medico_telefone)

        mais = input("\nAdicionar outro médico? (s/N): ").strip().lower()
        adicionar_mais = mais == 's'

    # Criar usuário admin
    print()
    print("👤 USUÁRIO ADMINISTRADOR:")
    admin_nome = input("Nome do usuário: ").strip()
    admin_email = input("Email de login: ").strip()
    admin_senha = input("Senha: ").strip()

    criar_usuario_admin(cliente.id, admin_nome, admin_email, admin_senha)

    # Resumo final
    print()
    print("=" * 70)
    print("🎉 ONBOARDING CONCLUÍDO COM SUCESSO!")
    print("=" * 70)
    print()
    print(f"🌐 URL de Acesso:")
    print(f"   https://{subdomain}.horariointeligente.com.br")
    print()
    print(f"👤 Login:")
    print(f"   Email: {admin_email}")
    print(f"   Senha: {admin_senha}")
    print()
    print("📝 Próximos Passos:")
    print("   1. Configurar WhatsApp Evolution API (se necessário)")
    print("   2. Fazer upload da logo (se tiver)")
    print("   3. Testar acesso e funcionalidades")
    print("   4. Treinar equipe do cliente")
    print()
    print("=" * 70)


def onboarding_rapido(args):
    """Onboarding rápido via argumentos de linha de comando"""
    print("🚀 Onboarding Rápido")
    print("=" * 70)

    # Criar cliente
    cliente = criar_cliente(
        args.nome,
        args.subdomain,
        args.email,
        args.cor_primaria,
        args.cor_secundaria,
        args.logo_icon
    )

    if not cliente:
        return

    # Adicionar médico padrão se fornecido
    if args.medico_nome:
        adicionar_medico(
            cliente.id,
            args.medico_nome,
            args.medico_email,
            args.medico_especialidade,
            args.medico_crm,
            args.medico_telefone
        )

    # Criar usuário admin se fornecido
    if args.admin_email:
        criar_usuario_admin(
            cliente.id,
            args.admin_nome or "Administrador",
            args.admin_email,
            args.admin_senha
        )

    print()
    print(f"✅ Cliente '{args.nome}' configurado!")
    print(f"🌐 Acesse: https://{args.subdomain}.horariointeligente.com.br")
    print()


def main():
    parser = argparse.ArgumentParser(description="Onboarding de novo cliente no sistema ProSaúde")

    # Argumentos do cliente
    parser.add_argument("--nome", help="Nome da clínica")
    parser.add_argument("--subdomain", help="Subdomínio (ex: saolucas)")
    parser.add_argument("--email", help="Email da clínica")
    parser.add_argument("--cor-primaria", dest="cor_primaria", default="#3b82f6", help="Cor primária (hex)")
    parser.add_argument("--cor-secundaria", dest="cor_secundaria", default="#1e40af", help="Cor secundária (hex)")
    parser.add_argument("--logo-icon", dest="logo_icon", default="fa-hospital", help="Ícone FontAwesome")

    # Argumentos do médico (opcional)
    parser.add_argument("--medico-nome", dest="medico_nome", help="Nome do médico")
    parser.add_argument("--medico-email", dest="medico_email", help="Email do médico")
    parser.add_argument("--medico-especialidade", dest="medico_especialidade", help="Especialidade")
    parser.add_argument("--medico-crm", dest="medico_crm", help="CRM")
    parser.add_argument("--medico-telefone", dest="medico_telefone", help="Telefone do médico")

    # Argumentos do usuário admin (opcional)
    parser.add_argument("--admin-nome", dest="admin_nome", help="Nome do usuário admin")
    parser.add_argument("--admin-email", dest="admin_email", help="Email do usuário admin")
    parser.add_argument("--admin-senha", dest="admin_senha", help="Senha do usuário admin")

    args = parser.parse_args()

    # Se nenhum argumento foi passado, usar modo interativo
    if not args.nome:
        onboarding_completo_interativo()
    else:
        if not args.subdomain or not args.email:
            print("❌ Erro: --nome, --subdomain e --email são obrigatórios no modo rápido")
            parser.print_help()
            sys.exit(1)

        onboarding_rapido(args)


if __name__ == "__main__":
    main()
