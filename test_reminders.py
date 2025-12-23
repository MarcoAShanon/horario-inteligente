#!/usr/bin/env python3
"""
Testes para o Sistema de Lembretes
Sistema ProSaude
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from app.database import SessionLocal
from app.models.agendamento import Agendamento
from app.models.paciente import Paciente
from app.models.medico import Medico
from app.services.reminder_service import reminder_service


def test_1_pending_stats():
    """Teste 1: Obter estatísticas de lembretes pendentes"""
    print("\n" + "=" * 60)
    print("TESTE 1: Estatísticas de Lembretes Pendentes")
    print("=" * 60)

    try:
        stats = reminder_service.get_pending_reminders_stats()

        print(f"✅ Estatísticas obtidas com sucesso:")
        print(f"   📅 Lembretes 24h pendentes: {stats.get('pending_24h', 0)}")
        print(f"   🔔 Lembretes 3h pendentes: {stats.get('pending_3h', 0)}")
        print(f"   ⏰ Lembretes 1h pendentes: {stats.get('pending_1h', 0)}")
        print(f"   📊 Total pendentes: {stats.get('total_pending', 0)}")
        print(f"   🕐 Timestamp: {stats.get('timestamp', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {str(e)}")
        return False


def test_2_create_test_appointment():
    """Teste 2: Criar agendamento de teste para lembretes"""
    print("\n" + "=" * 60)
    print("TESTE 2: Criar Agendamento de Teste")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Buscar médico e paciente existentes
        medico = db.query(Medico).filter(Medico.ativo == True).first()
        paciente = db.query(Paciente).first()

        if not medico or not paciente:
            print("❌ Médico ou paciente não encontrado no banco")
            return False

        # Criar agendamento para 2 horas no futuro
        data_hora_futura = datetime.now() + timedelta(hours=2, minutes=55)

        agendamento = Agendamento(
            paciente_id=paciente.id,
            medico_id=medico.id,
            data_hora=data_hora_futura,
            status="agendado",
            tipo_atendimento="convenio",
            lembrete_24h_enviado=False,
            lembrete_3h_enviado=False,
            lembrete_1h_enviado=False
        )

        db.add(agendamento)
        db.commit()
        db.refresh(agendamento)

        print(f"✅ Agendamento de teste criado:")
        print(f"   ID: {agendamento.id}")
        print(f"   Paciente: {paciente.nome}")
        print(f"   Médico: {medico.nome}")
        print(f"   Data/Hora: {data_hora_futura.strftime('%d/%m/%Y às %H:%M')}")
        print(f"   Status: {agendamento.status}")

        return agendamento.id

    except Exception as e:
        print(f"❌ Erro ao criar agendamento: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


async def test_3_send_immediate_reminder(agendamento_id: int):
    """Teste 3: Enviar lembrete imediato"""
    print("\n" + "=" * 60)
    print("TESTE 3: Enviar Lembrete Imediato (Teste)")
    print("=" * 60)

    try:
        # Testar envio de lembrete de 3h
        resultado = await reminder_service.send_immediate_reminder(
            agendamento_id=agendamento_id,
            reminder_type="3h"
        )

        if resultado.get("success"):
            print(f"✅ Lembrete 3h enviado com sucesso")
            print(f"   Agendamento ID: {resultado.get('agendamento_id')}")
            print(f"   Tipo: {resultado.get('reminder_type')}")
        else:
            print(f"❌ Falha ao enviar lembrete: {resultado.get('error')}")
            return False

        return True

    except Exception as e:
        print(f"❌ Erro ao enviar lembrete: {str(e)}")
        return False


async def test_4_process_all_reminders():
    """Teste 4: Processar todos os lembretes"""
    print("\n" + "=" * 60)
    print("TESTE 4: Processar Todos os Lembretes")
    print("=" * 60)

    try:
        stats = await reminder_service.process_all_reminders()

        print(f"✅ Processamento concluído:")
        print(f"   📅 Lembretes 24h enviados: {stats.get('lembretes_24h', 0)}")
        print(f"   🔔 Lembretes 3h enviados: {stats.get('lembretes_3h', 0)}")
        print(f"   ⏰ Lembretes 1h enviados: {stats.get('lembretes_1h', 0)}")
        print(f"   ❌ Erros: {stats.get('erros', 0)}")
        print(f"   🕐 Timestamp: {stats.get('timestamp', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Erro ao processar lembretes: {str(e)}")
        return False


def test_5_check_database():
    """Teste 5: Verificar registros no banco de dados"""
    print("\n" + "=" * 60)
    print("TESTE 5: Verificar Registros no Banco")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Buscar agendamentos próximos
        now = datetime.now()
        future_date = now + timedelta(hours=5)

        agendamentos = db.query(Agendamento).filter(
            Agendamento.data_hora >= now,
            Agendamento.data_hora <= future_date,
            Agendamento.status.in_(["agendado", "confirmado"])
        ).all()

        print(f"✅ Agendamentos encontrados: {len(agendamentos)}")

        for agendamento in agendamentos[:5]:  # Mostrar apenas os 5 primeiros
            paciente = db.query(Paciente).filter(Paciente.id == agendamento.paciente_id).first()
            medico = db.query(Medico).filter(Medico.id == agendamento.medico_id).first()

            print(f"\n   Agendamento ID: {agendamento.id}")
            print(f"   Paciente: {paciente.nome if paciente else 'N/A'}")
            print(f"   Médico: {medico.nome if medico else 'N/A'}")
            print(f"   Data/Hora: {agendamento.data_hora.strftime('%d/%m/%Y às %H:%M')}")
            print(f"   Status: {agendamento.status}")
            print(f"   Lembrete 24h enviado: {'✅' if agendamento.lembrete_24h_enviado else '❌'}")
            print(f"   Lembrete 3h enviado: {'✅' if agendamento.lembrete_3h_enviado else '❌'}")
            print(f"   Lembrete 1h enviado: {'✅' if agendamento.lembrete_1h_enviado else '❌'}")

        return True

    except Exception as e:
        print(f"❌ Erro ao verificar banco: {str(e)}")
        return False
    finally:
        db.close()


async def main():
    """Função principal de testes"""
    print("\n" + "=" * 60)
    print("🧪 TESTES DO SISTEMA DE LEMBRETES")
    print("=" * 60)

    resultados = []

    # Teste 1: Estatísticas
    resultados.append(("Estatísticas", test_1_pending_stats()))

    # Teste 2: Criar agendamento de teste
    agendamento_id = test_2_create_test_appointment()
    resultados.append(("Criar Agendamento", bool(agendamento_id)))

    # Teste 3: Enviar lembrete imediato (só se criou agendamento)
    if agendamento_id:
        resultado_envio = await test_3_send_immediate_reminder(agendamento_id)
        resultados.append(("Enviar Lembrete", resultado_envio))

    # Teste 4: Processar todos os lembretes
    resultado_processar = await test_4_process_all_reminders()
    resultados.append(("Processar Lembretes", resultado_processar))

    # Teste 5: Verificar banco
    resultados.append(("Verificar Banco", test_5_check_database()))

    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)

    sucessos = sum(1 for _, sucesso in resultados if sucesso)
    total = len(resultados)

    for nome, sucesso in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{nome:30} {status}")

    print("=" * 60)
    print(f"Total: {sucessos}/{total} testes passaram")
    print("=" * 60)

    return sucessos == total


if __name__ == "__main__":
    # Executar testes
    sucesso = asyncio.run(main())

    # Retornar código de saída
    sys.exit(0 if sucesso else 1)
