#!/usr/bin/env python3
"""
Script para criptografar CPFs existentes no banco de dados.
Executar uma vez apos configurar ENCRYPTION_KEY no .env.

Uso: python scripts/encrypt_existing_cpfs.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.crypto_service import encrypt_value, decrypt_value, _get_fernet
from app.database import SessionLocal
from sqlalchemy import text


def main():
    if not _get_fernet():
        print("ERRO: ENCRYPTION_KEY nao configurada no .env")
        sys.exit(1)

    db = SessionLocal()
    try:
        # Buscar pacientes com CPF nao-criptografado
        result = db.execute(text("SELECT id, cpf FROM pacientes WHERE cpf IS NOT NULL"))
        rows = result.fetchall()
        count = 0

        for row in rows:
            cpf = row.cpf
            if not cpf:
                continue

            # Verificar se ja esta criptografado (tokens Fernet comecam com 'gAAA')
            if cpf.startswith("gAAA"):
                continue

            encrypted = encrypt_value(cpf)
            db.execute(
                text("UPDATE pacientes SET cpf = :cpf WHERE id = :id"),
                {"cpf": encrypted, "id": row.id}
            )
            count += 1

        db.commit()
        print(f"CPFs criptografados: {count} de {len(rows)} registros")

        # Tambem criptografar cpf_cnpj de parceiros comerciais
        result = db.execute(text("SELECT id, cpf_cnpj FROM parceiros_comerciais WHERE cpf_cnpj IS NOT NULL"))
        rows = result.fetchall()
        count_parceiros = 0

        for row in rows:
            cpf_cnpj = row.cpf_cnpj
            if not cpf_cnpj or cpf_cnpj.startswith("gAAA"):
                continue

            encrypted = encrypt_value(cpf_cnpj)
            db.execute(
                text("UPDATE parceiros_comerciais SET cpf_cnpj = :val WHERE id = :id"),
                {"val": encrypted, "id": row.id}
            )
            count_parceiros += 1

        db.commit()
        print(f"CPF/CNPJs de parceiros criptografados: {count_parceiros} de {len(rows)} registros")

    except Exception as e:
        db.rollback()
        print(f"ERRO: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
