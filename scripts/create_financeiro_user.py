#!/usr/bin/env python3
"""
Script para criar usuário financeiro no sistema Horário Inteligente
"""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import bcrypt
from sqlalchemy import text
from app.database import engine

def hash_password(password: str) -> str:
    """Gera hash bcrypt da senha"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_financeiro_user():
    """Cria usuário financeiro de teste"""

    email = "financeiro@horariointeligente.com.br"
    password = "financeiro123"
    nome = "Gestor Financeiro"
    perfil = "financeiro"

    # Gerar hash da senha
    senha_hash = hash_password(password)

    print("=" * 60)
    print("🔐 CRIANDO USUÁRIO FINANCEIRO")
    print("=" * 60)
    print(f"Nome: {nome}")
    print(f"Email: {email}")
    print(f"Senha: {password}")
    print(f"Perfil: {perfil}")
    print("=" * 60)

    with engine.connect() as conn:
        # Verificar se usuário já existe
        result = conn.execute(
            text("SELECT id FROM super_admins WHERE email = :email"),
            {"email": email}
        )
        existing = result.fetchone()

        if existing:
            print(f"\n⚠️  Usuário já existe (ID: {existing[0]})")
            print("Atualizando senha e perfil...")

            conn.execute(
                text("""
                    UPDATE super_admins
                    SET senha = :senha,
                        perfil = :perfil,
                        ativo = true,
                        atualizado_em = NOW()
                    WHERE email = :email
                """),
                {"senha": senha_hash, "perfil": perfil, "email": email}
            )
            conn.commit()
            print("✅ Usuário atualizado com sucesso!")
        else:
            print("\n📝 Criando novo usuário...")

            conn.execute(
                text("""
                    INSERT INTO super_admins (nome, email, senha, perfil, ativo, criado_em, atualizado_em)
                    VALUES (:nome, :email, :senha, :perfil, true, NOW(), NOW())
                """),
                {"nome": nome, "email": email, "senha": senha_hash, "perfil": perfil}
            )
            conn.commit()
            print("✅ Usuário criado com sucesso!")

    print("\n" + "=" * 60)
    print("🎉 USUÁRIO FINANCEIRO PRONTO PARA USO!")
    print("=" * 60)
    print("\n🌐 Acesse:")
    print("   URL: https://horariointeligente.com.br/static/financeiro/login.html")
    print(f"   Email: {email}")
    print(f"   Senha: {password}")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        create_financeiro_user()
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        sys.exit(1)
