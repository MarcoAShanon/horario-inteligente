"""Create custos_operacionais table

Revision ID: h04_custos
Revises: h03_cli_parceiros
Create Date: 2025-12-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h04_custos'
down_revision: Union[str, None] = 'h03_cli_parceiros'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'custos_operacionais',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),

        # Dados do lançamento
        sa.Column('data_lancamento', sa.Date(), nullable=False),
        sa.Column('data_vencimento', sa.Date(), nullable=True),
        sa.Column('data_pagamento', sa.Date(), nullable=True),

        # Categorização
        sa.Column('categoria', sa.String(100), nullable=False),
        # Categorias sugeridas: 'infraestrutura', 'apis', 'comunicacao', 'servicos',
        # 'marketing', 'pessoal', 'impostos', 'outros'
        sa.Column('subcategoria', sa.String(100), nullable=True),
        sa.Column('centro_custo', sa.String(100), nullable=True),

        # Descrição e valores
        sa.Column('descricao', sa.Text(), nullable=False),
        sa.Column('valor', sa.Numeric(10, 2), nullable=False),
        sa.Column('valor_pago', sa.Numeric(10, 2), nullable=True),

        # Fornecedor
        sa.Column('fornecedor', sa.String(255), nullable=True),
        sa.Column('fornecedor_cnpj', sa.String(18), nullable=True),
        sa.Column('numero_documento', sa.String(100), nullable=True),  # NF, boleto, etc.

        # Comprovante
        sa.Column('comprovante_url', sa.String(500), nullable=True),

        # Recorrência
        sa.Column('recorrencia', sa.String(20), server_default='unico'),
        # 'unico', 'mensal', 'bimestral', 'trimestral', 'semestral', 'anual'
        sa.Column('parcela_atual', sa.Integer(), nullable=True),
        sa.Column('total_parcelas', sa.Integer(), nullable=True),
        sa.Column('lancamento_pai_id', sa.Integer(), sa.ForeignKey('custos_operacionais.id'), nullable=True),

        # Status
        sa.Column('status', sa.String(20), server_default='pendente'),
        # 'pendente', 'pago', 'cancelado', 'atrasado'

        # Auditoria
        sa.Column('criado_por', sa.Integer(), sa.ForeignKey('usuarios_internos.id'), nullable=True),
        sa.Column('atualizado_por', sa.Integer(), sa.ForeignKey('usuarios_internos.id'), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Índices para buscas comuns
    op.create_index('ix_custos_data_lancamento', 'custos_operacionais', ['data_lancamento'])
    op.create_index('ix_custos_categoria', 'custos_operacionais', ['categoria'])
    op.create_index('ix_custos_status', 'custos_operacionais', ['status'])
    op.create_index('ix_custos_fornecedor', 'custos_operacionais', ['fornecedor'])
    op.create_index('ix_custos_recorrencia', 'custos_operacionais', ['recorrencia'])

    # Índice composto para relatórios por período e categoria
    op.create_index('ix_custos_periodo_categoria', 'custos_operacionais', ['data_lancamento', 'categoria'])


def downgrade() -> None:
    op.drop_index('ix_custos_periodo_categoria', table_name='custos_operacionais')
    op.drop_index('ix_custos_recorrencia', table_name='custos_operacionais')
    op.drop_index('ix_custos_fornecedor', table_name='custos_operacionais')
    op.drop_index('ix_custos_status', table_name='custos_operacionais')
    op.drop_index('ix_custos_categoria', table_name='custos_operacionais')
    op.drop_index('ix_custos_data_lancamento', table_name='custos_operacionais')
    op.drop_table('custos_operacionais')
