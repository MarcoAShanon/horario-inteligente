#!/usr/bin/env python3
"""
Script para migrar senhas de médicos de texto plano para bcrypt
Horário Inteligente SaaS
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from app.database import SessionLocal
from sqlalchemy import text


def hash_password(plain_password: str) -> str:
    """Gera hash bcrypt da senha"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')


def is_bcrypt_hash(password: str) -> bool:
    """Verifica se já é um hash bcrypt"""
    return password is not None and password.startswith('$2')


def migrate_passwords(dry_run: bool = True):
    """
    Migra senhas de texto plano para bcrypt

    Args:
        dry_run: Se True, apenas mostra o que seria feito sem alterar
    """
    db = SessionLocal()

    try:
        # Buscar todos os médicos com senha
        result = db.execute(text('SELECT id, nome, email, senha FROM medicos WHERE senha IS NOT NULL'))
        medicos = result.fetchall()

        print("=" * 70)
        print("MIGRAÇÃO DE SENHAS - MÉDICOS")
        print("=" * 70)
        print(f"Modo: {'DRY RUN (simulação)' if dry_run else 'EXECUÇÃO REAL'}")
        print(f"Total de médicos com senha: {len(medicos)}")
        print("-" * 70)

        migrados = 0
        ja_hash = 0

        for medico in medicos:
            id_, nome, email, senha = medico

            if is_bcrypt_hash(senha):
                print(f"✅ ID {id_} | {nome[:30]:30} | JÁ TEM BCRYPT")
                ja_hash += 1
            else:
                # Senha em texto plano - precisa migrar
                if dry_run:
                    print(f"⚠️  ID {id_} | {nome[:30]:30} | TEXTO PLANO -> seria migrado")
                else:
                    # Gerar hash da senha atual
                    novo_hash = hash_password(senha)

                    # Atualizar no banco
                    db.execute(
                        text('UPDATE medicos SET senha = :hash WHERE id = :id'),
                        {"hash": novo_hash, "id": id_}
                    )
                    print(f"🔒 ID {id_} | {nome[:30]:30} | MIGRADO PARA BCRYPT")

                migrados += 1

        if not dry_run:
            db.commit()

        print("-" * 70)
        print(f"Já com bcrypt: {ja_hash}")
        print(f"Migrados: {migrados}")

        if dry_run and migrados > 0:
            print("\n⚠️  Execute novamente com --execute para aplicar as mudanças")
        elif not dry_run and migrados > 0:
            print("\n✅ Migração concluída com sucesso!")

    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Função principal"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrar senhas de médicos para bcrypt')
    parser.add_argument('--execute', action='store_true',
                        help='Executar a migração (sem isso, apenas simula)')

    args = parser.parse_args()

    migrate_passwords(dry_run=not args.execute)


if __name__ == "__main__":
    main()
