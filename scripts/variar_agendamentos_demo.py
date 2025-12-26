#!/usr/bin/env python3
"""
Script para redistribuir agendamentos do demo com variação visual interessante
- Alguns dias com muitos agendamentos (8-12)
- Alguns dias com poucos (1-3)
- Dias com quantidade média (4-6)
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


def main():
    print("=" * 60)
    print("REDISTRIBUIR AGENDAMENTOS - VARIAÇÃO VISUAL")
    print("=" * 60)

    with engine.connect() as conn:
        # Buscar cliente demo
        result = conn.execute(text("SELECT id FROM clientes WHERE subdomain = 'demo'"))
        cliente = result.fetchone()
        if not cliente:
            print("Cliente demo não encontrado!")
            return
        cliente_id = cliente[0]
        print(f"\nCliente Demo ID: {cliente_id}")

        # Buscar agendamentos do demo no mês atual
        result = conn.execute(text("""
            SELECT a.id
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE p.cliente_id = :cid
            AND EXTRACT(MONTH FROM a.data_hora) = 12
            AND EXTRACT(YEAR FROM a.data_hora) = 2025
            ORDER BY a.id
        """), {'cid': cliente_id})

        agendamentos = [row[0] for row in result]
        print(f"Agendamentos encontrados em Dezembro 2025: {len(agendamentos)}")

        if len(agendamentos) == 0:
            print("Nenhum agendamento encontrado!")
            return

        # Dias úteis de dezembro 2025 (sem incluir feriados de Natal/Ano Novo)
        dias_uteis = []
        for d in range(1, 24):  # Até dia 23 (antes do Natal)
            data = datetime(2025, 12, d)
            if data.weekday() < 5:  # Segunda a Sexta
                dias_uteis.append(d)

        print(f"Dias úteis disponíveis: {len(dias_uteis)}")

        # Definir padrão de variação para cada dia
        # Criar variação mais interessante:
        # - 20% dos dias: muitos agendamentos (8-12)
        # - 30% dos dias: quantidade média (4-7)
        # - 50% dos dias: poucos agendamentos (1-3)
        padroes = []
        num_dias = len(dias_uteis)

        # Dias de pico (segunda e terça geralmente são mais cheios)
        dias_pico = [d for d in dias_uteis if datetime(2025, 12, d).weekday() in [0, 1]]  # Seg, Ter
        dias_medios = [d for d in dias_uteis if datetime(2025, 12, d).weekday() in [2, 3]]  # Qua, Qui
        dias_leves = [d for d in dias_uteis if datetime(2025, 12, d).weekday() == 4]  # Sex

        # Redistribuir agendamentos
        distribuicao = {}

        # Dias de pico: 7-12 agendamentos cada
        for dia in dias_pico:
            distribuicao[dia] = random.randint(7, 12)

        # Dias médios: 4-7 agendamentos
        for dia in dias_medios:
            distribuicao[dia] = random.randint(4, 7)

        # Dias leves (sexta): 2-4 agendamentos
        for dia in dias_leves:
            distribuicao[dia] = random.randint(2, 4)

        # Ajustar para caber todos os agendamentos
        total_slots = sum(distribuicao.values())
        total_agendamentos = len(agendamentos)

        print(f"\nDistribuição inicial: {total_slots} slots")
        print(f"Agendamentos a distribuir: {total_agendamentos}")

        # Se temos mais agendamentos que slots, aumentar os dias de pico
        while total_slots < total_agendamentos:
            dia_aleatorio = random.choice(dias_pico)
            distribuicao[dia_aleatorio] += 1
            total_slots += 1

        # Se temos menos agendamentos que slots, reduzir dias leves
        while total_slots > total_agendamentos:
            dia_aleatorio = random.choice(dias_leves + dias_medios)
            if distribuicao[dia_aleatorio] > 1:
                distribuicao[dia_aleatorio] -= 1
                total_slots -= 1

        print("\nDistribuição planejada por dia:")
        for dia in sorted(distribuicao.keys()):
            data = datetime(2025, 12, dia)
            dia_semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'][data.weekday()]
            qtd = distribuicao[dia]
            barra = '█' * qtd
            print(f"  {dia:02d}/12 ({dia_semana}): {barra} ({qtd})")

        # Criar lista de datas com horários
        novas_datas = []
        horarios = [8, 9, 10, 11, 14, 15, 16, 17]  # Horários disponíveis

        for dia, qtd in distribuicao.items():
            horarios_disponiveis = horarios.copy()
            random.shuffle(horarios_disponiveis)

            for i in range(qtd):
                hora = horarios_disponiveis[i % len(horarios)]
                # Adicionar variação nos minutos
                minuto = random.choice([0, 15, 30, 45])
                data_hora = datetime(2025, 12, dia, hora, minuto, tzinfo=TZ)
                novas_datas.append(data_hora)

        # Embaralhar para distribuir status de forma aleatória
        random.shuffle(novas_datas)

        # Atualizar agendamentos
        print("\nAtualizando agendamentos no banco...")
        for i, agend_id in enumerate(agendamentos):
            if i < len(novas_datas):
                nova_data = novas_datas[i]
                conn.execute(
                    text("UPDATE agendamentos SET data_hora = :data WHERE id = :id"),
                    {'data': nova_data, 'id': agend_id}
                )

        conn.commit()

        # Verificar resultado
        print("\nResultado final por dia:")
        result = conn.execute(text("""
            SELECT
                DATE(a.data_hora) as dia,
                COUNT(*) as qtd
            FROM agendamentos a
            JOIN pacientes p ON a.paciente_id = p.id
            WHERE p.cliente_id = :cid
            AND EXTRACT(MONTH FROM a.data_hora) = 12
            AND EXTRACT(YEAR FROM a.data_hora) = 2025
            GROUP BY DATE(a.data_hora)
            ORDER BY dia
        """), {'cid': cliente_id})

        for row in result:
            dia = row[0]
            qtd = row[1]
            dia_semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'][dia.weekday()]
            barra = '█' * qtd
            print(f"  {dia.strftime('%d/%m')} ({dia_semana}): {barra} ({qtd})")

        print("\n" + "=" * 60)
        print("REDISTRIBUIÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        print("\nO gráfico de agendamentos por dia agora mostrará")
        print("variação visual mais interessante com picos e vales.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
