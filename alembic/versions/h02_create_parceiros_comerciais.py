"""Create parceiros_comerciais table

Revision ID: h02_parceiros
Revises: h01_usuarios_int
Create Date: 2025-12-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'h02_parceiros'
down_revision: Union[str, None] = 'h01_usuarios_int'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'parceiros_comerciais',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('tipo_pessoa', sa.String(2), server_default='PJ'),  # PF ou PJ
        sa.Column('cpf_cnpj', sa.String(18), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('telefone', sa.String(20), nullable=True),
        sa.Column('endereco', sa.Text(), nullable=True),

        # Dados de comissão
        sa.Column('percentual_comissao', sa.Numeric(5, 2), server_default='0'),
        sa.Column('valor_fixo_comissao', sa.Numeric(10, 2), nullable=True),  # Alternativa ao percentual
        sa.Column('tipo_comissao', sa.String(20), server_default='percentual'),  # 'percentual' ou 'fixo'

        # Dados bancários para pagamento
        sa.Column('dados_bancarios', JSONB, nullable=True),
        # Estrutura esperada:
        # {
        #   "banco": "341",
        #   "agencia": "1234",
        #   "conta": "12345-6",
        #   "tipo_conta": "corrente",
        #   "titular": "Nome do Titular",
        #   "cpf_cnpj_titular": "12345678901",
        #   "pix": "email@example.com"
        # }

        # Observações e controle
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true'),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Índice para busca por CPF/CNPJ
    op.create_index('ix_parceiros_cpf_cnpj', 'parceiros_comerciais', ['cpf_cnpj'])

    # Índice para busca por status
    op.create_index('ix_parceiros_ativo', 'parceiros_comerciais', ['ativo'])


def downgrade() -> None:
    op.drop_index('ix_parceiros_ativo', table_name='parceiros_comerciais')
    op.drop_index('ix_parceiros_cpf_cnpj', table_name='parceiros_comerciais')
    op.drop_table('parceiros_comerciais')
