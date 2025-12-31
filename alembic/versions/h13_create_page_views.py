"""Create page_views table for analytics

Revision ID: h13_create_page_views
Revises: h09_create_assinaturas
Create Date: 2025-12-30

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h13_create_page_views'
down_revision = 'h12_horarios_por_dia'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'page_views',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),

        # Identificação do visitante
        sa.Column('visitor_id', sa.String(64), nullable=False, index=True),
        sa.Column('session_id', sa.String(64), nullable=False, index=True),

        # Página visitada
        sa.Column('pagina', sa.String(50), nullable=False),
        sa.Column('url_path', sa.String(500), nullable=True),

        # Origem do tráfego
        sa.Column('referrer', sa.Text(), nullable=True),
        sa.Column('utm_source', sa.String(100), nullable=True),
        sa.Column('utm_medium', sa.String(100), nullable=True),
        sa.Column('utm_campaign', sa.String(100), nullable=True),

        # Informações do dispositivo
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('dispositivo', sa.String(20), nullable=True),
        sa.Column('navegador', sa.String(50), nullable=True),
        sa.Column('sistema_operacional', sa.String(50), nullable=True),

        # Localização
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('pais', sa.String(100), nullable=True),
        sa.Column('estado', sa.String(100), nullable=True),
        sa.Column('cidade', sa.String(100), nullable=True),

        # Eventos e interações
        sa.Column('evento', sa.String(50), nullable=True),
        sa.Column('evento_dados', sa.Text(), nullable=True),

        # Métricas de engajamento
        sa.Column('tempo_na_pagina', sa.Integer(), nullable=True),
        sa.Column('scroll_depth', sa.Integer(), nullable=True),

        # Timestamp
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # Índices compostos para consultas de analytics
    op.create_index('ix_page_views_pagina_criado', 'page_views', ['pagina', 'criado_em'])
    op.create_index('ix_page_views_visitor_pagina', 'page_views', ['visitor_id', 'pagina'])
    op.create_index('ix_page_views_evento', 'page_views', ['evento'])


def downgrade():
    op.drop_index('ix_page_views_evento', table_name='page_views')
    op.drop_index('ix_page_views_visitor_pagina', table_name='page_views')
    op.drop_index('ix_page_views_pagina_criado', table_name='page_views')
    op.drop_table('page_views')
