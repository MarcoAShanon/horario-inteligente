"""
Criar tabela de assinaturas (vínculo cliente-plano)

Revision ID: h09_create_assinaturas
Revises: h08_create_planos
Create Date: 2025-12-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h09_create_assinaturas'
down_revision = 'h08_create_planos'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'assinaturas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=False),
        sa.Column('plano_id', sa.Integer(), sa.ForeignKey('planos.id'), nullable=False),

        # Valores da assinatura (podem ter desconto)
        sa.Column('valor_mensal', sa.Numeric(10, 2), nullable=False),
        sa.Column('valor_profissional_adicional', sa.Numeric(10, 2), server_default='50.00'),
        sa.Column('profissionais_contratados', sa.Integer(), server_default='1'),

        # Taxa de ativação
        sa.Column('taxa_ativacao', sa.Numeric(10, 2), server_default='150.00'),
        sa.Column('taxa_ativacao_paga', sa.Boolean(), server_default='false'),
        sa.Column('desconto_ativacao_percentual', sa.Numeric(5, 2), server_default='0'),
        sa.Column('motivo_desconto_ativacao', sa.String(100)),

        # Serviços adicionais
        sa.Column('numero_virtual_salvy', sa.Boolean(), server_default='false'),
        sa.Column('valor_numero_virtual', sa.Numeric(10, 2), server_default='40.00'),

        # Datas
        sa.Column('data_inicio', sa.Date(), nullable=False),
        sa.Column('data_fim', sa.Date()),  # NULL = ativa
        sa.Column('dia_vencimento', sa.Integer(), server_default='10'),

        # Status
        sa.Column('status', sa.String(20), server_default="'ativa'"),  # ativa, suspensa, cancelada
        sa.Column('motivo_cancelamento', sa.Text()),

        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), onupdate=sa.func.now())
    )

    op.create_index('ix_assinaturas_cliente', 'assinaturas', ['cliente_id'])
    op.create_index('ix_assinaturas_status', 'assinaturas', ['status'])


def downgrade():
    op.drop_index('ix_assinaturas_status')
    op.drop_index('ix_assinaturas_cliente')
    op.drop_table('assinaturas')
