#!/usr/bin/env python3
"""
Script para popular agendamentos de Janeiro/2026 no ambiente demo
"""

import random
from datetime import datetime, timedelta
import psycopg2

# Configuração do banco
DB_CONFIG = {
    'host': 'localhost',
    'database': 'agendamento_saas',
    'user': 'postgres',
    'password': 'postgres'
}

# Cliente demo
CLIENTE_ID = 3

# Médicos do cliente demo
MEDICOS = [
    {'id': 18, 'nome': 'Dr. Carlos Silva', 'especialidade': 'Clínico Geral'},
    {'id': 19, 'nome': 'Dra. Ana Beatriz', 'especialidade': 'Cardiologia'},
    {'id': 20, 'nome': 'Dr. Roberto Mendes', 'especialidade': 'Ortopedia'}
]

# Convênios do cliente demo
CONVENIOS = ['Particular', 'Unimed', 'Amil', 'Bradesco Saúde', 'SulAmérica', 'Hapvida']

# Valores por convênio
VALORES_CONVENIO = {
    'Particular': ['250.00', '300.00', '350.00'],
    'Unimed': ['180.00', '200.00'],
    'Amil': ['170.00', '190.00'],
    'Bradesco Saúde': ['185.00', '210.00'],
    'SulAmérica': ['175.00', '195.00'],
    'Hapvida': ['120.00', '150.00']
}

# Nomes brasileiros
NOMES = [
    'Maria Silva', 'João Santos', 'Ana Oliveira', 'Pedro Costa', 'Juliana Souza',
    'Carlos Ferreira', 'Fernanda Lima', 'Ricardo Alves', 'Patricia Gomes', 'Marcelo Ribeiro',
    'Luciana Martins', 'Bruno Carvalho', 'Camila Rodrigues', 'Rafael Nascimento', 'Amanda Pereira',
    'Lucas Barbosa', 'Vanessa Araújo', 'Gabriel Moreira', 'Isabela Cardoso', 'Thiago Mendes',
    'Letícia Correia', 'Diego Monteiro', 'Larissa Teixeira', 'Felipe Cavalcanti', 'Mariana Dias',
    'André Nunes', 'Beatriz Ramos', 'Rodrigo Castro', 'Carolina Vieira', 'Gustavo Pinto',
    'Renata Lopes', 'Eduardo Rocha', 'Priscila Freitas', 'Leandro Medeiros', 'Tatiana Reis',
    'Henrique Campos', 'Aline Cunha', 'Marcos Paulo', 'Débora Borges', 'Vinícius Melo',
    'Sandra Regina', 'Paulo Henrique', 'Cristiane Duarte', 'Roberto Junior', 'Michele Santos',
    'Fábio Andrade', 'Simone Farias', 'Alexandre Braga', 'Eliane Costa', 'Sérgio Moura',
    'Cláudia Bezerra', 'Antônio Carlos', 'Rosana Lima', 'José Ricardo', 'Mônica Silveira',
    'Wellington Souza', 'Adriana Prado', 'Márcio Viana', 'Daniela Queiroz', 'Leonardo Bastos',
    'Natália Fonseca', 'Rogério Sampaio', 'Juliana Matos', 'Cássio Miranda', 'Raquel Amorim'
]

# Motivos de consulta por especialidade
MOTIVOS = {
    'Clínico Geral': [
        'Consulta de rotina', 'Check-up anual', 'Dor de cabeça frequente',
        'Fadiga e cansaço', 'Gripe persistente', 'Dor abdominal',
        'Exames preventivos', 'Acompanhamento de saúde', 'Mal estar geral'
    ],
    'Cardiologia': [
        'Dor no peito', 'Palpitações', 'Pressão alta',
        'Falta de ar', 'Avaliação cardíaca', 'Eletrocardiograma',
        'Acompanhamento de hipertensão', 'Check-up cardíaco', 'Arritmia'
    ],
    'Ortopedia': [
        'Dor nas costas', 'Dor no joelho', 'Lesão no ombro',
        'Entorse de tornozelo', 'Dor na coluna', 'Avaliação postural',
        'Dor no quadril', 'Tendinite', 'Fratura antiga'
    ]
}

# Status possíveis
STATUS_PASSADO = ['realizada', 'cancelada', 'faltou']
STATUS_FUTURO = ['agendada', 'confirmada']
PESOS_STATUS_PASSADO = [0.75, 0.15, 0.10]  # 75% realizada, 15% cancelada, 10% faltou

# Horários de consulta (8h às 18h, de 30 em 30 min)
HORARIOS = [f"{h:02d}:{m:02d}" for h in range(8, 18) for m in [0, 30]]


def gerar_telefone():
    """Gera telefone brasileiro aleatório"""
    ddd = random.choice(['21', '11', '31', '41', '51', '61', '71', '81', '85', '92'])
    numero = f"9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
    return f"({ddd}) {numero}"


def gerar_cpf():
    """Gera CPF formatado (não válido, apenas para demo)"""
    numeros = [random.randint(0, 9) for _ in range(11)]
    return f"{numeros[0]}{numeros[1]}{numeros[2]}.{numeros[3]}{numeros[4]}{numeros[5]}.{numeros[6]}{numeros[7]}{numeros[8]}-{numeros[9]}{numeros[10]}"


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("=== Populando Janeiro/2026 para Demo ===\n")

    # Data atual
    hoje = datetime(2026, 1, 4)

    # Criar pacientes e agendamentos para todo janeiro
    pacientes_criados = 0
    agendamentos_criados = 0

    # Gerar agendamentos para cada dia de janeiro
    for dia in range(1, 32):
        try:
            data = datetime(2026, 1, dia)
        except ValueError:
            continue  # Dia inválido

        # Pular domingos
        if data.weekday() == 6:
            continue

        # Sábado: menos consultas
        if data.weekday() == 5:
            num_consultas = random.randint(3, 8)
        else:
            num_consultas = random.randint(8, 15)

        print(f"Dia {dia:02d}/01/2026 ({data.strftime('%A')}): {num_consultas} consultas")

        horarios_usados = {m['id']: [] for m in MEDICOS}

        for _ in range(num_consultas):
            # Escolher médico
            medico = random.choice(MEDICOS)

            # Escolher horário não usado para este médico
            horarios_disponiveis = [h for h in HORARIOS if h not in horarios_usados[medico['id']]]
            if not horarios_disponiveis:
                continue

            horario = random.choice(horarios_disponiveis)
            horarios_usados[medico['id']].append(horario)

            # Dados do paciente
            nome = random.choice(NOMES)
            telefone = gerar_telefone()
            convenio = random.choice(CONVENIOS)
            valor = random.choice(VALORES_CONVENIO[convenio])

            # Verificar se telefone já existe
            cur.execute("SELECT id FROM pacientes WHERE telefone = %s", (telefone,))
            paciente_existente = cur.fetchone()

            if paciente_existente:
                paciente_id = paciente_existente[0]
            else:
                # Criar paciente
                cur.execute("""
                    INSERT INTO pacientes (cliente_id, nome, telefone, email, cpf, convenio, criado_em, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (
                    CLIENTE_ID,
                    nome,
                    telefone,
                    f"{nome.lower().replace(' ', '.')}@email.com",
                    gerar_cpf(),
                    convenio
                ))
                paciente_id = cur.fetchone()[0]
                pacientes_criados += 1

            # Data/hora do agendamento
            hora, minuto = map(int, horario.split(':'))
            data_hora = data.replace(hour=hora, minute=minuto)

            # Status baseado se é passado ou futuro
            if data < hoje:
                status = random.choices(STATUS_PASSADO, weights=PESOS_STATUS_PASSADO)[0]
            else:
                status = random.choice(STATUS_FUTURO)

            # Motivo da consulta
            motivo = random.choice(MOTIVOS[medico['especialidade']])

            # Criar agendamento
            cur.execute("""
                INSERT INTO agendamentos (
                    paciente_id, medico_id, data_hora, status, tipo_atendimento,
                    valor_consulta, motivo_consulta, criado_em, atualizado_em
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                paciente_id,
                medico['id'],
                data_hora,
                status,
                convenio.lower().replace(' ', '_'),
                valor,
                motivo
            ))
            agendamentos_criados += 1

    conn.commit()

    print(f"\n=== Resumo ===")
    print(f"Pacientes criados: {pacientes_criados}")
    print(f"Agendamentos criados: {agendamentos_criados}")

    # Estatísticas
    cur.execute("""
        SELECT status, COUNT(*)
        FROM agendamentos a
        JOIN medicos m ON a.medico_id = m.id
        WHERE m.cliente_id = %s
        AND a.data_hora >= '2026-01-01' AND a.data_hora < '2026-02-01'
        GROUP BY status
    """, (CLIENTE_ID,))

    print(f"\n=== Status dos Agendamentos de Janeiro ===")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cur.execute("""
        SELECT tipo_atendimento, COUNT(*), SUM(CAST(valor_consulta AS DECIMAL))
        FROM agendamentos a
        JOIN medicos m ON a.medico_id = m.id
        WHERE m.cliente_id = %s
        AND a.data_hora >= '2026-01-01' AND a.data_hora < '2026-02-01'
        AND a.status = 'realizada'
        GROUP BY tipo_atendimento
    """, (CLIENTE_ID,))

    print(f"\n=== Faturamento por Convênio (Realizadas) ===")
    total = 0
    for row in cur.fetchall():
        valor = float(row[2] or 0)
        total += valor
        print(f"  {row[0]}: {row[1]} consultas - R$ {valor:,.2f}")
    print(f"  TOTAL: R$ {total:,.2f}")

    cur.close()
    conn.close()

    print("\n✓ Dados populados com sucesso!")


if __name__ == "__main__":
    main()
