"""
Adicionar campos para parceria estratégica de lançamento

Revision ID: h10_parceria_estrategica
Revises: h09_create_assinaturas
Create Date: 2024-12-22
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'h10_parceria_estrategica'
down_revision = 'h09_create_assinaturas'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar campos em parceiros_comerciais
    op.add_column('parceiros_comerciais',
        sa.Column('parceria_lancamento', sa.Boolean(), server_default='false')
    )
    op.add_column('parceiros_comerciais',
        sa.Column('limite_clientes_lancamento', sa.Integer(), server_default='40')
    )

    # Adicionar campos em clientes_parceiros para controle de parceria
    op.add_column('clientes_parceiros',
        sa.Column('tipo_parceria', sa.String(30), server_default='padrao')
    )  # 'padrao', 'lancamento'

    op.add_column('clientes_parceiros',
        sa.Column('ordem_cliente', sa.Integer())
    )  # Número sequencial do cliente (1-40 para parceria lançamento)

    op.add_column('clientes_parceiros',
        sa.Column('comissao_sobre', sa.String(20), server_default='receita')
    )  # 'receita', 'margem'

    # Atualizar tipo_comissao para suportar 'percentual_margem'
    # (o campo já existe com varchar(20), vamos só alterar para 30)
    op.alter_column('parceiros_comerciais', 'tipo_comissao',
        type_=sa.String(30),
        existing_type=sa.String(20)
    )


def downgrade():
    op.drop_column('clientes_parceiros', 'tipo_parceria')
    op.drop_column('clientes_parceiros', 'ordem_cliente')
    op.drop_column('clientes_parceiros', 'comissao_sobre')
    op.drop_column('parceiros_comerciais', 'parceria_lancamento')
    op.drop_column('parceiros_comerciais', 'limite_clientes_lancamento')
    op.alter_column('parceiros_comerciais', 'tipo_comissao',
        type_=sa.String(20),
        existing_type=sa.String(30)
    )
