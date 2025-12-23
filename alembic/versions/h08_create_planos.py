"""
Criar tabela de planos de assinatura

Revision ID: h08_create_planos
Revises: h07_add_periodicidade_despesas
Create Date: 2025-12-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h08_create_planos'
down_revision = 'h07_add_periodicidade_despesas'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'planos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('codigo', sa.String(50), unique=True, nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('valor_mensal', sa.Numeric(10, 2), nullable=False),
        sa.Column('profissionais_inclusos', sa.Integer(), server_default='1'),
        sa.Column('valor_profissional_adicional', sa.Numeric(10, 2), server_default='50.00'),
        sa.Column('taxa_ativacao', sa.Numeric(10, 2), server_default='150.00'),
        sa.Column('ativo', sa.Boolean(), server_default='true'),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), onupdate=sa.func.now())
    )

    # Inserir planos iniciais conforme Plano de Negócios v1.1
    op.execute("""
        INSERT INTO planos (codigo, nome, descricao, valor_mensal, profissionais_inclusos, valor_profissional_adicional, taxa_ativacao)
        VALUES
        ('individual', 'Individual', 'Ideal para profissionais autônomos - 1 profissional incluso', 150.00, 1, 50.00, 150.00),
        ('clinica', 'Clínica', 'Para clínicas com múltiplos profissionais - 2 profissionais inclusos', 200.00, 2, 50.00, 200.00)
    """)


def downgrade():
    op.drop_table('planos')
