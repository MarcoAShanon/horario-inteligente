#!/usr/bin/env python3
"""
Script de Reset do Ambiente Demo
Executado diariamente via cron para manter dados consistentes
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Adicionar o diretório do projeto ao path
sys.path.insert(0, '/root/sistema_agendamento')

from app.database import SessionLocal
from sqlalchemy import text
import bcrypt

def reset_demo():
    """Reseta todos os dados do ambiente demo"""
    print(f"[{datetime.now()}] Iniciando reset do ambiente demo...")

    db = SessionLocal()
    demo_cliente_id = 3

    try:
        # 1. Limpar agendamentos do demo
        db.execute(text("""
            DELETE FROM agendamentos
            WHERE medico_id IN (SELECT id FROM medicos WHERE cliente_id = :cid)
        """), {"cid": demo_cliente_id})
        print("  ✓ Agendamentos limpos")

        # 2. Limpar pacientes do demo
        db.execute(text("DELETE FROM pacientes WHERE cliente_id = :cid"), {"cid": demo_cliente_id})
        print("  ✓ Pacientes limpos")

        # 3. Limpar médicos do demo
        db.execute(text("DELETE FROM medicos WHERE cliente_id = :cid"), {"cid": demo_cliente_id})
        print("  ✓ Médicos limpos")

        db.commit()

        # 4. Recriar médicos
        senha_hash = bcrypt.hashpw("demo123".encode(), bcrypt.gensalt()).decode()
        medicos_data = [
            {"nome": "Dr. Carlos Silva", "email": "dr.carlos@demo.horariointeligente.com.br", "especialidade": "Clínico Geral", "crm": "123456-SP"},
            {"nome": "Dra. Ana Beatriz", "email": "dra.ana@demo.horariointeligente.com.br", "especialidade": "Cardiologia", "crm": "234567-SP"},
            {"nome": "Dr. Roberto Mendes", "email": "dr.roberto@demo.horariointeligente.com.br", "especialidade": "Ortopedia", "crm": "345678-SP"}
        ]

        medico_ids = []
        for med in medicos_data:
            result = db.execute(text("""
                INSERT INTO medicos (nome, email, especialidade, crm, telefone, cliente_id, senha, ativo, email_verificado, criado_em, atualizado_em)
                VALUES (:nome, :email, :especialidade, :crm, '(11) 98888-0000', :cliente_id, :senha, true, true, NOW(), NOW())
                RETURNING id
            """), {**med, "cliente_id": demo_cliente_id, "senha": senha_hash})
            medico_ids.append(result.fetchone()[0])

        db.commit()
        print(f"  ✓ {len(medico_ids)} médicos criados")

        # 5. Criar pacientes
        nomes_pacientes = [
            "Maria Santos", "João Oliveira", "Ana Paula Costa", "Pedro Almeida",
            "Carla Fernandes", "Lucas Souza", "Fernanda Lima", "Ricardo Pereira",
            "Juliana Martins", "Marcos Rodrigues", "Patrícia Gomes", "Bruno Silva",
            "Camila Nunes", "Rafael Mendes", "Larissa Castro", "Gabriel Rocha",
            "Amanda Ribeiro", "Felipe Dias", "Natália Araújo", "Thiago Cardoso"
        ]

        convenios = ['Particular', 'Unimed', 'Bradesco Saúde', 'Amil', 'SulAmérica']
        paciente_ids = []

        for nome in nomes_pacientes:
            telefone = f"(11) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
            result = db.execute(text("""
                INSERT INTO pacientes (nome, telefone, cliente_id, convenio, criado_em, atualizado_em)
                VALUES (:nome, :telefone, :cliente_id, :convenio, NOW(), NOW())
                RETURNING id
            """), {
                "nome": nome,
                "telefone": telefone,
                "cliente_id": demo_cliente_id,
                "convenio": random.choice(convenios)
            })
            paciente_ids.append(result.fetchone()[0])

        db.commit()
        print(f"  ✓ {len(paciente_ids)} pacientes criados")

        # 6. Criar agendamentos
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tipos_atendimento = ['Consulta', 'Retorno', 'Primeira Consulta']
        valores = ['150.00', '200.00', '250.00', '180.00']
        agendamentos_criados = 0

        # Passados (últimos 30 dias)
        for i in range(40):
            data = hoje - timedelta(days=random.randint(1, 30))
            hora = random.choice([8, 9, 10, 11, 14, 15, 16, 17])
            data_hora = data.replace(hour=hora, minute=random.choice([0, 30]))

            db.execute(text("""
                INSERT INTO agendamentos (paciente_id, medico_id, data_hora, status, tipo_atendimento, valor_consulta, observacoes, criado_em, atualizado_em)
                VALUES (:paciente_id, :medico_id, :data_hora, 'realizado', :tipo, :valor, 'Consulta de demonstração', NOW(), NOW())
            """), {
                "paciente_id": random.choice(paciente_ids),
                "medico_id": random.choice(medico_ids),
                "data_hora": data_hora,
                "tipo": random.choice(tipos_atendimento),
                "valor": random.choice(valores)
            })
            agendamentos_criados += 1

        # Futuros (próximos 14 dias)
        for i in range(25):
            data = hoje + timedelta(days=random.randint(0, 14))
            hora = random.choice([8, 9, 10, 11, 14, 15, 16, 17])
            data_hora = data.replace(hour=hora, minute=random.choice([0, 30]))

            db.execute(text("""
                INSERT INTO agendamentos (paciente_id, medico_id, data_hora, status, tipo_atendimento, valor_consulta, observacoes, criado_em, atualizado_em)
                VALUES (:paciente_id, :medico_id, :data_hora, :status, :tipo, :valor, 'Consulta de demonstração', NOW(), NOW())
            """), {
                "paciente_id": random.choice(paciente_ids),
                "medico_id": random.choice(medico_ids),
                "data_hora": data_hora,
                "status": random.choice(['confirmado', 'confirmado', 'pendente']),
                "tipo": random.choice(tipos_atendimento),
                "valor": random.choice(valores)
            })
            agendamentos_criados += 1

        db.commit()
        print(f"  ✓ {agendamentos_criados} agendamentos criados")

        print(f"\n[{datetime.now()}] ✅ Reset do ambiente demo concluído com sucesso!")
        print(f"  - {len(medico_ids)} médicos")
        print(f"  - {len(paciente_ids)} pacientes")
        print(f"  - {agendamentos_criados} agendamentos")

    except Exception as e:
        print(f"\n[{datetime.now()}] ❌ Erro no reset do demo: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    reset_demo()
