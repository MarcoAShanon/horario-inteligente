"""add parceiro ativacao fields

Revision ID: k01_parceiro_ativacao
Revises: j06_add_credenciais_enviadas_em
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k01_parceiro_ativacao'
down_revision: Union[str, None] = 'j06_add_credenciais_enviadas_em'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table, column):
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column)"
    ), {"table": table, "column": column})
    return result.scalar()


def upgrade() -> None:
    conn = op.get_bind()

    # Recorrência de comissão
    if not _column_exists(conn, 'parceiros_comerciais', 'recorrencia_comissao_meses'):
        op.add_column('parceiros_comerciais', sa.Column(
            'recorrencia_comissao_meses', sa.Integer(), nullable=True,
            comment='Null = permanente'
        ))

    if not _column_exists(conn, 'parceiros_comerciais', 'recorrencia_renovavel'):
        op.add_column('parceiros_comerciais', sa.Column(
            'recorrencia_renovavel', sa.Boolean(), server_default='true', nullable=False
        ))

    # Status do parceiro
    if not _column_exists(conn, 'parceiros_comerciais', 'status'):
        op.add_column('parceiros_comerciais', sa.Column(
            'status', sa.String(30), server_default='ativo', nullable=False
        ))

    # Token de ativação
    if not _column_exists(conn, 'parceiros_comerciais', 'token_ativacao'):
        op.add_column('parceiros_comerciais', sa.Column(
            'token_ativacao', sa.String(100), nullable=True, unique=True
        ))

    if not _column_exists(conn, 'parceiros_comerciais', 'token_expira_em'):
        op.add_column('parceiros_comerciais', sa.Column(
            'token_expira_em', sa.DateTime(timezone=True), nullable=True
        ))

    # Campos de aceite do termo
    if not _column_exists(conn, 'parceiros_comerciais', 'aceite_termo_em'):
        op.add_column('parceiros_comerciais', sa.Column(
            'aceite_termo_em', sa.DateTime(timezone=True), nullable=True
        ))

    if not _column_exists(conn, 'parceiros_comerciais', 'aceite_termo_ip'):
        op.add_column('parceiros_comerciais', sa.Column(
            'aceite_termo_ip', sa.String(45), nullable=True
        ))

    if not _column_exists(conn, 'parceiros_comerciais', 'aceite_termo_user_agent'):
        op.add_column('parceiros_comerciais', sa.Column(
            'aceite_termo_user_agent', sa.Text(), nullable=True
        ))

    if not _column_exists(conn, 'parceiros_comerciais', 'aceite_termo_versao'):
        op.add_column('parceiros_comerciais', sa.Column(
            'aceite_termo_versao', sa.String(20), nullable=True
        ))

    # Retrocompatibilidade: parceiros existentes com senha ficam 'ativo',
    # sem senha ficam 'pendente_aceite'
    conn.execute(sa.text(
        "UPDATE parceiros_comerciais SET status = 'ativo' "
        "WHERE ativo = true AND senha_hash IS NOT NULL AND status = 'ativo'"
    ))
    conn.execute(sa.text(
        "UPDATE parceiros_comerciais SET status = 'pendente_aceite' "
        "WHERE senha_hash IS NULL AND status = 'ativo' AND ativo = true"
    ))
    conn.execute(sa.text(
        "UPDATE parceiros_comerciais SET status = 'inativo' "
        "WHERE ativo = false"
    ))


def downgrade() -> None:
    op.drop_column('parceiros_comerciais', 'aceite_termo_versao')
    op.drop_column('parceiros_comerciais', 'aceite_termo_user_agent')
    op.drop_column('parceiros_comerciais', 'aceite_termo_ip')
    op.drop_column('parceiros_comerciais', 'aceite_termo_em')
    op.drop_column('parceiros_comerciais', 'token_expira_em')
    op.drop_column('parceiros_comerciais', 'token_ativacao')
    op.drop_column('parceiros_comerciais', 'status')
    op.drop_column('parceiros_comerciais', 'recorrencia_renovavel')
    op.drop_column('parceiros_comerciais', 'recorrencia_comissao_meses')
