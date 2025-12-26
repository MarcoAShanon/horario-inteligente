#!/usr/bin/env python3
"""
Script para atualizar dados financeiros do cliente Demo
- Cria convênios com valores de repasse
- Define valores de consulta particular para médicos
- Atualiza agendamentos existentes com tipo_atendimento correto e valores
"""
import sys
import random
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import text
from app.database import engine

# Configurações de valores (em reais)
CONVENIOS_CONFIG = {
    'Unimed': {'valor_consulta': 180.00, 'valor_repasse': 120.00},
    'Amil': {'valor_consulta': 160.00, 'valor_repasse': 100.00},
    'Bradesco Saúde': {'valor_consulta': 200.00, 'valor_repasse': 140.00},
    'SulAmérica': {'valor_consulta': 190.00, 'valor_repasse': 130.00},
    'Hapvida': {'valor_consulta': 120.00, 'valor_repasse': 70.00},
}

VALORES_PARTICULAR = {
    'Dr. Carlos Silva': 350.00,
    'Dra. Ana Beatriz': 400.00,
    'Dr. Roberto Mendes': 380.00,
}

def main():
    print("=" * 60)
    print("ATUALIZAR DADOS FINANCEIROS - CLIENTE DEMO")
    print("=" * 60)

    with engine.connect() as conn:
        # 1. Buscar cliente demo
        result = conn.execute(text("SELECT id FROM clientes WHERE subdomain = 'demo'"))
        cliente = result.fetchone()
        if not cliente:
            print("Cliente demo não encontrado!")
            return
        cliente_id = cliente[0]
        print(f"\n Cliente Demo ID: {cliente_id}")

        # 2. Buscar médicos do demo
        result = conn.execute(
            text("SELECT id, nome FROM medicos WHERE cliente_id = :cid"),
            {'cid': cliente_id}
        )
        medicos = result.fetchall()
        print(f"\n Médicos encontrados: {len(medicos)}")

        # 3. Atualizar valores particulares dos médicos
        print("\n Atualizando valores de consulta particular...")
        for medico_id, nome in medicos:
            valor = VALORES_PARTICULAR.get(nome, 350.00)
            conn.execute(
                text("UPDATE medicos SET valor_consulta_particular = :valor WHERE id = :mid"),
                {'valor': valor, 'mid': medico_id}
            )
            print(f"   {nome}: R$ {valor:.2f}")

        # 4. Criar convênios para o cliente demo
        print("\n Criando convênios...")

        # Primeiro, verificar se já existem
        result = conn.execute(
            text("SELECT COUNT(*) FROM convenios WHERE cliente_id = :cid"),
            {'cid': cliente_id}
        )
        convenios_existentes = result.fetchone()[0]

        if convenios_existentes > 0:
            print(f"   Já existem {convenios_existentes} convênios. Limpando...")
            conn.execute(
                text("DELETE FROM convenios WHERE cliente_id = :cid"),
                {'cid': cliente_id}
            )

        convenios_ids = {}
        for nome, config in CONVENIOS_CONFIG.items():
            result = conn.execute(
                text("""
                    INSERT INTO convenios (cliente_id, nome, codigo, ativo, criado_em, atualizado_em)
                    VALUES (:cid, :nome, :codigo, true, NOW(), NOW())
                    RETURNING id
                """),
                {
                    'cid': cliente_id,
                    'nome': nome,
                    'codigo': nome.lower().replace(' ', '_').replace('á', 'a')
                }
            )
            convenio_id = result.fetchone()[0]
            convenios_ids[nome] = convenio_id
            print(f"   {nome} (ID: {convenio_id})")

        # 5. Criar valores de consulta por médico/convênio
        print("\n Criando valores de repasse por médico/convênio...")

        # Verificar se tabela valores_consulta existe
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'valores_consulta'
            )
        """))
        tabela_existe = result.fetchone()[0]

        if not tabela_existe:
            # Criar tabela valores_consulta
            print("   Criando tabela valores_consulta...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS valores_consulta (
                    id SERIAL PRIMARY KEY,
                    medico_id INTEGER REFERENCES medicos(id),
                    convenio_id INTEGER REFERENCES convenios(id),
                    valor_consulta DECIMAL(10,2),
                    valor_repasse DECIMAL(10,2),
                    criado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_em TIMESTAMP DEFAULT NOW(),
                    UNIQUE(medico_id, convenio_id)
                )
            """))

        # Limpar valores existentes
        conn.execute(text("""
            DELETE FROM valores_consulta
            WHERE medico_id IN (SELECT id FROM medicos WHERE cliente_id = :cid)
        """), {'cid': cliente_id})

        for medico_id, nome_medico in medicos:
            for nome_conv, convenio_id in convenios_ids.items():
                config = CONVENIOS_CONFIG[nome_conv]
                # Adicionar variação por médico (+/- 10%)
                variacao = random.uniform(0.9, 1.1)
                valor_consulta = round(config['valor_consulta'] * variacao, 2)
                valor_repasse = round(config['valor_repasse'] * variacao, 2)

                conn.execute(
                    text("""
                        INSERT INTO valores_consulta
                        (medico_id, convenio_id, valor_consulta, valor_repasse, criado_em, atualizado_em)
                        VALUES (:mid, :cid, :vc, :vr, NOW(), NOW())
                    """),
                    {
                        'mid': medico_id,
                        'cid': convenio_id,
                        'vc': valor_consulta,
                        'vr': valor_repasse
                    }
                )
            print(f"   Valores criados para {nome_medico}")

        # 6. Atualizar agendamentos existentes
        print("\n Atualizando agendamentos existentes...")

        # Buscar agendamentos do cliente demo
        result = conn.execute(text("""
            SELECT a.id, p.convenio, m.valor_consulta_particular
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            JOIN medicos m ON a.medico_id = m.id
            WHERE p.cliente_id = :cid
        """), {'cid': cliente_id})

        agendamentos = result.fetchall()
        print(f"   Total de agendamentos: {len(agendamentos)}")

        particulares = 0
        convenios_count = 0

        for agend_id, convenio_paciente, valor_particular in agendamentos:
            if convenio_paciente == 'Particular':
                # Consulta particular
                tipo = 'particular'
                valor = valor_particular or 350.00
                particulares += 1
            else:
                # Consulta por convênio
                tipo = 'convenio'
                config = CONVENIOS_CONFIG.get(convenio_paciente, {'valor_repasse': 100.00})
                valor = config['valor_repasse']
                convenios_count += 1

            conn.execute(
                text("""
                    UPDATE agendamentos
                    SET tipo_atendimento = :tipo, valor_consulta = :valor
                    WHERE id = :aid
                """),
                {'tipo': tipo, 'valor': str(valor), 'aid': agend_id}
            )

        print(f"   Particulares: {particulares}")
        print(f"   Convênios: {convenios_count}")

        # Commit todas as alterações
        conn.commit()

        # 7. Mostrar resumo financeiro
        print("\n" + "=" * 60)
        print("RESUMO FINANCEIRO ATUALIZADO")
        print("=" * 60)

        result = conn.execute(text("""
            SELECT
                tipo_atendimento,
                COUNT(*) as qtd,
                SUM(CAST(valor_consulta AS DECIMAL)) as total
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE p.cliente_id = :cid
            GROUP BY tipo_atendimento
        """), {'cid': cliente_id})

        total_geral = 0
        for row in result:
            print(f"  {row[0].upper()}: {row[1]} consultas = R$ {row[2]:,.2f}")
            total_geral += float(row[2] or 0)

        print(f"\n  TOTAL: R$ {total_geral:,.2f}")

        # Por convênio
        print("\n Por convênio do paciente:")
        result = conn.execute(text("""
            SELECT
                p.convenio,
                COUNT(*) as qtd,
                SUM(CAST(a.valor_consulta AS DECIMAL)) as total
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE p.cliente_id = :cid
            GROUP BY p.convenio
            ORDER BY total DESC
        """), {'cid': cliente_id})

        for row in result:
            print(f"   {row[0]}: {row[1]} consultas = R$ {row[2]:,.2f}")

        print("\n" + "=" * 60)
        print("DADOS FINANCEIROS ATUALIZADOS COM SUCESSO!")
        print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
