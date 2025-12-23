#!/usr/bin/env python3
"""
Script para popular banco de dados com dados de demonstração
Cliente: ProSaude
- 100 agendamentos no mês de dezembro 2025
- 70 confirmados, 18 remarcados, 12 cancelados
- 30 pacientes fictícios
"""
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import text
from app.database import engine

# Timezone Brasil
TZ = ZoneInfo('America/Sao_Paulo')

# Dados fictícios
NOMES_PACIENTES = [
    "Ana Silva Santos", "Carlos Eduardo Oliveira", "Maria José Costa",
    "João Pedro Almeida", "Fernanda Lima Souza", "Roberto Carlos Martins",
    "Juliana Ferreira Rocha", "Paulo Henrique Santos", "Amanda Cristina Lima",
    "Ricardo Alves Pereira", "Luciana Moreira Silva", "Felipe Augusto Costa",
    "Patrícia Gomes Oliveira", "Marcelo Vieira Santos", "Camila Rodrigues Lima",
    "Bruno Henrique Souza", "Débora Cristina Alves", "Rafael Moura Santos",
    "Vanessa Paula Costa", "Diego Henrique Lima", "Renata Silva Oliveira",
    "Thiago Augusto Santos", "Bianca Fernandes Costa", "Leonardo Silva Lima",
    "Gabriela Moreira Santos", "André Luiz Oliveira", "Carla Beatriz Costa",
    "Rodrigo Henrique Lima", "Larissa Cristina Santos", "Fábio Roberto Costa"
]

TELEFONES = [
    "21987654321", "21976543210", "21965432109", "21954321098",
    "21943210987", "21932109876", "21921098765", "21910987654",
    "21999876543", "21988765432", "21977654321", "21966543210",
    "21955432109", "21944321098", "21933210987", "21922109876",
    "21911098765", "21900987654", "21989876543", "21978765432",
    "21967654321", "21956543210", "21945432109", "21934321098",
    "21923210987", "21912109876", "21901098765", "21990987654",
    "21979876543", "21968765432"
]

CONVENIOS = ["Particular", "Unimed", "Amil", "Bradesco Saúde", "SulAmérica"]

MOTIVOS_CONSULTA = [
    "Consulta de rotina",
    "Retorno médico",
    "Primeira consulta",
    "Exame de acompanhamento",
    "Check-up anual",
    "Avaliação de sintomas",
    "Renovação de receita",
    "Consulta preventiva"
]

OBSERVACOES = [
    "Paciente pontual",
    "Primeira consulta no local",
    "Retorno de 30 dias",
    "Trazer exames anteriores",
    "Solicitar jejum de 12h",
    None,  # Sem observações
    None,
    None
]

def create_pacientes(conn, cliente_id: int, count: int = 30):
    """Cria pacientes fictícios"""
    print(f"\n📋 Criando {count} pacientes fictícios...")

    pacientes_ids = []

    for i in range(count):
        nome = NOMES_PACIENTES[i]
        telefone = TELEFONES[i]
        convenio = random.choice(CONVENIOS)
        email = f"{nome.lower().replace(' ', '.')}@email.com"

        # Data de nascimento aleatória (18 a 80 anos)
        anos = random.randint(18, 80)
        data_nascimento = datetime.now() - timedelta(days=anos*365)

        result = conn.execute(
            text("""
                INSERT INTO pacientes
                (cliente_id, nome, telefone, email, data_nascimento, convenio, criado_em, atualizado_em)
                VALUES
                (:cliente_id, :nome, :telefone, :email, :data_nascimento, :convenio, NOW(), NOW())
                RETURNING id
            """),
            {
                'cliente_id': cliente_id,
                'nome': nome,
                'telefone': telefone,
                'email': email,
                'data_nascimento': data_nascimento,
                'convenio': convenio
            }
        )
        paciente_id = result.fetchone()[0]
        pacientes_ids.append(paciente_id)

        if (i + 1) % 10 == 0:
            print(f"  ✓ {i + 1}/{count} pacientes criados")

    conn.commit()
    print(f"✅ {count} pacientes criados com sucesso!")
    return pacientes_ids

def create_agendamentos(conn, pacientes_ids: list, medicos_ids: list, count: int = 100):
    """Cria agendamentos com distribuição realista"""
    print(f"\n📅 Criando {count} agendamentos...")

    # Distribuição de status
    status_list = (
        ['confirmado'] * 70 +
        ['remarcado'] * 18 +
        ['cancelado'] * 12
    )
    random.shuffle(status_list)

    # Período: Dezembro 2025 (próximo mês)
    ano = 2025
    mes = 12
    dias_uteis = [d for d in range(1, 32) if datetime(ano, mes, d).weekday() < 5]  # Seg-Sex

    # Horários comerciais (8h às 18h)
    horarios = list(range(8, 18))

    agendamentos_criados = 0

    for i in range(count):
        # Selecionar paciente e médico aleatórios
        paciente_id = random.choice(pacientes_ids)
        medico_id = random.choice(medicos_ids)

        # Data e hora aleatórias
        dia = random.choice(dias_uteis)
        hora = random.choice(horarios)
        data_hora = datetime(ano, mes, dia, hora, 0, tzinfo=TZ)

        # Status
        status = status_list[i]

        # Outros campos
        tipo_atendimento = random.choice(['Consulta', 'Retorno', 'Exame'])
        valor = random.choice(['200.00', '150.00', '180.00', '220.00'])
        motivo = random.choice(MOTIVOS_CONSULTA)
        obs = random.choice(OBSERVACOES)

        try:
            conn.execute(
                text("""
                    INSERT INTO agendamentos
                    (paciente_id, medico_id, data_hora, status, tipo_atendimento,
                     valor_consulta, motivo_consulta, observacoes, criado_em, atualizado_em)
                    VALUES
                    (:paciente_id, :medico_id, :data_hora, :status, :tipo_atendimento,
                     :valor_consulta, :motivo_consulta, :observacoes, NOW(), NOW())
                """),
                {
                    'paciente_id': paciente_id,
                    'medico_id': medico_id,
                    'data_hora': data_hora,
                    'status': status,
                    'tipo_atendimento': tipo_atendimento,
                    'valor_consulta': valor,
                    'motivo_consulta': motivo,
                    'observacoes': obs
                }
            )
            agendamentos_criados += 1

            if (i + 1) % 20 == 0:
                print(f"  ✓ {i + 1}/{count} agendamentos criados")

        except Exception as e:
            print(f"⚠️  Erro ao criar agendamento {i+1}: {e}")
            continue

    conn.commit()
    print(f"✅ {agendamentos_criados} agendamentos criados com sucesso!")

    # Mostrar estatísticas
    print("\n📊 ESTATÍSTICAS:")
    for status in ['confirmado', 'remarcado', 'cancelado']:
        count = status_list.count(status)
        print(f"  • {status.capitalize()}: {count}")

def main():
    """Função principal"""
    print("=" * 60)
    print("🎯 POPULAR BANCO COM DADOS DE DEMONSTRAÇÃO")
    print("=" * 60)
    print("Cliente: ProSaude")
    print("Período: Dezembro 2025")
    print("Agendamentos: 100 (70 confirmados, 18 remarcados, 12 cancelados)")
    print("=" * 60)

    # Confirmar
    resposta = input("\n⚠️  Deseja continuar? (s/N): ").strip().lower()
    if resposta != 's':
        print("❌ Operação cancelada.")
        return

    with engine.connect() as conn:
        # 1. Buscar cliente ProSaude
        result = conn.execute(
            text("SELECT id FROM clientes WHERE subdomain = 'prosaude'")
        )
        cliente = result.fetchone()
        if not cliente:
            print("❌ Cliente ProSaude não encontrado!")
            return
        cliente_id = cliente[0]
        print(f"\n✓ Cliente encontrado (ID: {cliente_id})")

        # 2. Buscar médicos
        result = conn.execute(
            text("SELECT id, nome FROM medicos WHERE cliente_id = :cliente_id"),
            {'cliente_id': cliente_id}
        )
        medicos = result.fetchall()
        medicos_ids = [m[0] for m in medicos]
        print(f"✓ {len(medicos)} médicos encontrados:")
        for m in medicos:
            print(f"  • {m[1]} (ID: {m[0]})")

        # 3. Verificar pacientes existentes
        result = conn.execute(
            text("SELECT COUNT(*) FROM pacientes WHERE cliente_id = :cliente_id"),
            {'cliente_id': cliente_id}
        )
        pacientes_existentes = result.fetchone()[0]

        # 4. Criar pacientes
        if pacientes_existentes < 30:
            pacientes_a_criar = 30 - pacientes_existentes
            novos_pacientes = create_pacientes(conn, cliente_id, pacientes_a_criar)
        else:
            print(f"\n✓ Já existem {pacientes_existentes} pacientes")
            novos_pacientes = []

        # 5. Buscar todos os pacientes
        result = conn.execute(
            text("SELECT id FROM pacientes WHERE cliente_id = :cliente_id"),
            {'cliente_id': cliente_id}
        )
        todos_pacientes = [row[0] for row in result]
        print(f"✓ Total de pacientes disponíveis: {len(todos_pacientes)}")

        # 6. Criar agendamentos
        create_agendamentos(conn, todos_pacientes, medicos_ids, 100)

        # 7. Verificar resultado final
        print("\n" + "=" * 60)
        print("📈 RESULTADO FINAL")
        print("=" * 60)

        result = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM agendamentos a
                JOIN pacientes p ON a.paciente_id = p.id
                WHERE p.cliente_id = :cliente_id
            """),
            {'cliente_id': cliente_id}
        )
        total_agendamentos = result.fetchone()[0]
        print(f"Total de agendamentos: {total_agendamentos}")

        result = conn.execute(
            text("""
                SELECT status, COUNT(*)
                FROM agendamentos a
                JOIN pacientes p ON a.paciente_id = p.id
                WHERE p.cliente_id = :cliente_id
                GROUP BY status
            """),
            {'cliente_id': cliente_id}
        )
        print("\nPor status:")
        for row in result:
            print(f"  • {row[0]}: {row[1]}")

        print("\n" + "=" * 60)
        print("🎉 DADOS DE DEMONSTRAÇÃO CRIADOS COM SUCESSO!")
        print("=" * 60)
        print("\n💡 Agora você pode:")
        print("  1. Acessar o dashboard em: https://horariointeligente.com.br")
        print("  2. Fazer login como: admin@prosaude.com")
        print("  3. Ver as estatísticas e gráficos com dados reais")
        print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
