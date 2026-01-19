#!/usr/bin/env python3
"""
Seed Script - Clínica PróSaúde
Horário Inteligente SaaS

Cria dados de teste para validar o sistema completo:
- Cliente (tenant)
- Médicos com senhas
- Horários de atendimento

Uso:
    python scripts/seed_prosaude.py          # Dry-run (mostra o que seria criado)
    python scripts/seed_prosaude.py --execute  # Executa de verdade
"""

import sys
import os
from datetime import time

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from sqlalchemy import text
from app.database import SessionLocal
from app.models.cliente import Cliente
from app.models.medico import Medico


def hash_password(password: str) -> str:
    """Gera hash bcrypt da senha"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def seed_prosaude(execute: bool = False):
    """Cria dados de teste da Clínica PróSaúde"""

    db = SessionLocal()

    try:
        print("=" * 60)
        print("SEED: Clínica PróSaúde")
        print("=" * 60)

        # ============ 1. VERIFICAR SE JÁ EXISTE ============
        existing = db.query(Cliente).filter(Cliente.subdomain == "prosaude").first()
        if existing:
            print(f"\n✅ Cliente 'prosaude' já existe (ID: {existing.id})")
            print("   Vou atualizar os dados e adicionar médicos de teste.")
            cliente_id = existing.id

            # Atualizar whatsapp_numero se não tiver
            if not existing.whatsapp_numero:
                if execute:
                    existing.whatsapp_numero = "+5521923670092"
                    db.commit()
                    print("   ✅ WhatsApp atualizado: +5521923670092")
                else:
                    print("   (dry-run) Atualizaria WhatsApp")
        else:
            cliente_id = None  # Será criado abaixo

        # ============ 2. CRIAR CLIENTE (se não existir) ============
        if not cliente_id:
            print("\n📋 CLIENTE (Tenant):")
            cliente_data = {
                "nome": "Clínica PróSaúde",
                "cnpj": "12.345.678/0001-90",
                "email": "contato@prosaude.teste",
                "telefone": "(21) 3333-4444",
                "endereco": "Av. Rio Branco, 123 - Centro, Rio de Janeiro - RJ",
                "subdomain": "prosaude",
                "whatsapp_numero": "+5521923670092",
                "whatsapp_instance": "ProSaude",
                "logo_icon": "fa-clinic-medical",
                "cor_primaria": "#10b981",
                "cor_secundaria": "#059669",
                "plano": "profissional",
                "ativo": True
            }

            for key, value in cliente_data.items():
                print(f"   {key}: {value}")

            if execute:
                cliente = Cliente(**cliente_data)
                db.add(cliente)
                db.commit()
                db.refresh(cliente)
                cliente_id = cliente.id
                print(f"\n   ✅ Cliente criado (ID: {cliente_id})")
            else:
                cliente_id = "[NEW]"
                print("\n   (dry-run)")

        # ============ 3. CRIAR MÉDICOS ============
        medicos_data = [
            {
                "nome": "Ana Silva",
                "email": "ana@prosaude.teste",
                "senha": "ana123",
                "crm": "SEC-001",
                "especialidade": "Secretária",
                "telefone": "(21) 99999-1111",
                "horarios": None  # Secretária não tem horário de atendimento
            },
            {
                "nome": "Dr. Carlos Mendes",
                "email": "carlos@prosaude.teste",
                "senha": "carlos123",
                "crm": "CRM-RJ 12345",
                "especialidade": "Cardiologia",
                "telefone": "(21) 99999-2222",
                "horarios": {
                    # Seg-Sex, 08:00-12:00 e 14:00-18:00
                    "dias": [0, 1, 2, 3, 4],  # Seg a Sex
                    "turnos": [
                        {"inicio": "08:00", "fim": "12:00"},
                        {"inicio": "14:00", "fim": "18:00"}
                    ]
                }
            },
            {
                "nome": "Dra. Maria Santos",
                "email": "maria@prosaude.teste",
                "senha": "maria123",
                "crm": "CRM-RJ 54321",
                "especialidade": "Dermatologia",
                "telefone": "(21) 99999-3333",
                "horarios": {
                    # Seg, Qua, Sex, 09:00-17:00
                    "dias": [0, 2, 4],  # Seg, Qua, Sex
                    "turnos": [
                        {"inicio": "09:00", "fim": "17:00"}
                    ]
                }
            }
        ]

        print("\n👨‍⚕️ MÉDICOS/USUÁRIOS:")
        medico_ids = []

        for med_data in medicos_data:
            print(f"\n   --- {med_data['nome']} ---")
            print(f"   Email: {med_data['email']}")
            print(f"   Senha: {med_data['senha']} (será hasheada)")
            print(f"   CRM: {med_data['crm']}")
            print(f"   Especialidade: {med_data['especialidade']}")

            # Verificar se já existe
            existing_medico = db.query(Medico).filter(
                Medico.email == med_data['email'],
                Medico.cliente_id == cliente_id
            ).first()

            if existing_medico:
                print(f"   ⚠️  Já existe (ID: {existing_medico.id}) - atualizando senha...")
                if execute:
                    senha_hash = hash_password(med_data['senha'])
                    db.execute(
                        text("UPDATE medicos SET senha = :senha WHERE id = :id"),
                        {"senha": senha_hash, "id": existing_medico.id}
                    )
                    db.commit()
                    print(f"   ✅ Senha atualizada")
                medico_ids.append({"id": existing_medico.id, "data": med_data})
            else:
                if execute:
                    # Criar médico
                    medico = Medico(
                        cliente_id=cliente_id,
                        nome=med_data['nome'],
                        email=med_data['email'],
                        crm=med_data['crm'],
                        especialidade=med_data['especialidade'],
                        telefone=med_data['telefone'],
                        ativo=True
                    )
                    db.add(medico)
                    db.commit()
                    db.refresh(medico)

                    # Atualizar senha via SQL direto (campo não está no model)
                    senha_hash = hash_password(med_data['senha'])
                    db.execute(
                        text("UPDATE medicos SET senha = :senha WHERE id = :id"),
                        {"senha": senha_hash, "id": medico.id}
                    )
                    db.commit()

                    medico_ids.append({"id": medico.id, "data": med_data})
                    print(f"   ✅ Criado (ID: {medico.id})")
                else:
                    medico_ids.append({"id": "[NEW]", "data": med_data})
                    print("   (dry-run)")

        # ============ 4. CRIAR HORÁRIOS DE ATENDIMENTO ============
        print("\n🕐 HORÁRIOS DE ATENDIMENTO:")

        dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

        for med_info in medico_ids:
            med_data = med_info['data']
            if not med_data.get('horarios'):
                print(f"\n   {med_data['nome']}: Sem horários (secretária)")
                continue

            print(f"\n   {med_data['nome']}:")

            # Verificar se já tem horários
            existing_horarios = db.execute(
                text("SELECT COUNT(*) FROM horarios_atendimento WHERE medico_id = :mid"),
                {"mid": med_info['id']}
            ).scalar()

            if existing_horarios > 0:
                print(f"      ⚠️  Já possui {existing_horarios} horários cadastrados - pulando")
                continue

            horarios = med_data['horarios']
            for dia in horarios['dias']:
                for turno in horarios['turnos']:
                    print(f"      {dias_semana[dia]}: {turno['inicio']} - {turno['fim']}")

                    if execute:
                        hora_inicio = time.fromisoformat(turno['inicio'])
                        hora_fim = time.fromisoformat(turno['fim'])

                        db.execute(
                            text("""
                                INSERT INTO horarios_atendimento
                                (medico_id, dia_semana, hora_inicio, hora_fim, ativo)
                                VALUES (:medico_id, :dia, :inicio, :fim, true)
                            """),
                            {
                                "medico_id": med_info['id'],
                                "dia": dia,
                                "inicio": hora_inicio,
                                "fim": hora_fim
                            }
                        )

            if execute:
                db.commit()
                print(f"      ✅ Horários salvos")

        # ============ 5. RESUMO ============
        print("\n" + "=" * 60)
        print("RESUMO")
        print("=" * 60)

        if execute:
            print(f"""
✅ Dados criados com sucesso!

🏥 Cliente: Clínica PróSaúde (ID: {cliente_id})
   Subdomain: prosaude
   WhatsApp: +5521923670092

👤 Usuários criados:
   1. Ana Silva (Secretária)
      Email: ana@prosaude.teste
      Senha: ana123

   2. Dr. Carlos Mendes (Cardiologia)
      Email: carlos@prosaude.teste
      Senha: carlos123
      Horários: Seg-Sex 08:00-12:00, 14:00-18:00

   3. Dra. Maria Santos (Dermatologia)
      Email: maria@prosaude.teste
      Senha: maria123
      Horários: Seg/Qua/Sex 09:00-17:00

🔗 Acesse:
   - Login: https://prosaude.horariointeligente.com.br/static/login.html
   - Dashboard: https://prosaude.horariointeligente.com.br/static/dashboard.html
   - Conversas: https://prosaude.horariointeligente.com.br/static/conversas.html
""")
        else:
            print("""
🔍 DRY-RUN: Nenhum dado foi criado.

Para executar de verdade, use:
   python scripts/seed_prosaude.py --execute

Para recriar dados existentes:
   python scripts/seed_prosaude.py --execute --force
""")

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERRO: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    execute = "--execute" in sys.argv
    seed_prosaude(execute=execute)
