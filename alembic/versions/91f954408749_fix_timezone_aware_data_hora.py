"""fix_timezone_aware_data_hora

Revision ID: 91f954408749
Revises: 11362647cedf
Create Date: 2025-12-01 14:46:21.544936

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91f954408749'
down_revision: Union[str, Sequence[str], None] = '11362647cedf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Converte a coluna data_hora de TIMESTAMP para TIMESTAMPTZ (timezone-aware).
    Assume que todos os dados existentes estão em horário de Brasília (America/Sao_Paulo).
    """
    # Passo 1: Criar coluna temporária com timezone
    op.execute("""
        ALTER TABLE agendamentos
        ADD COLUMN data_hora_tz TIMESTAMPTZ;
    """)

    # Passo 2: Copiar dados assumindo que são horário de Brasília (UTC-3)
    # Converte TIMESTAMP sem timezone para TIMESTAMPTZ em horário de Brasília
    op.execute("""
        UPDATE agendamentos
        SET data_hora_tz = timezone('America/Sao_Paulo', data_hora);
    """)

    # Passo 3: Dropar coluna antiga
    op.execute("""
        ALTER TABLE agendamentos
        DROP COLUMN data_hora;
    """)

    # Passo 4: Renomear coluna nova
    op.execute("""
        ALTER TABLE agendamentos
        RENAME COLUMN data_hora_tz TO data_hora;
    """)

    # Passo 5: Adicionar NOT NULL constraint
    op.execute("""
        ALTER TABLE agendamentos
        ALTER COLUMN data_hora SET NOT NULL;
    """)

    print("✅ Migration concluída: data_hora agora é timezone-aware (TIMESTAMPTZ)")


def downgrade() -> None:
    """
    Reverte a coluna data_hora de TIMESTAMPTZ para TIMESTAMP (sem timezone).
    ATENÇÃO: Isso pode causar perda de informação de timezone!
    """
    # Passo 1: Criar coluna temporária sem timezone
    op.execute("""
        ALTER TABLE agendamentos
        ADD COLUMN data_hora_naive TIMESTAMP;
    """)

    # Passo 2: Copiar dados convertendo para horário de Brasília (sem timezone)
    op.execute("""
        UPDATE agendamentos
        SET data_hora_naive = (data_hora AT TIME ZONE 'America/Sao_Paulo');
    """)

    # Passo 3: Dropar coluna com timezone
    op.execute("""
        ALTER TABLE agendamentos
        DROP COLUMN data_hora;
    """)

    # Passo 4: Renomear coluna
    op.execute("""
        ALTER TABLE agendamentos
        RENAME COLUMN data_hora_naive TO data_hora;
    """)

    # Passo 5: Adicionar NOT NULL constraint
    op.execute("""
        ALTER TABLE agendamentos
        ALTER COLUMN data_hora SET NOT NULL;
    """)

    print("⚠️ Downgrade concluído: data_hora voltou a ser TIMESTAMP (sem timezone)")
