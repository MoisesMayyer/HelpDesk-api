"""Cria comentários internos e histórico de chamados."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | Sequence[str] | None = "d3f4e5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comentarios_internos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_chamado", sa.Integer(), sa.ForeignKey("chamados.id"), nullable=False),
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "historico_chamados",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_chamado", sa.Integer(), sa.ForeignKey("chamados.id"), nullable=False),
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("tipo", sa.String(100), nullable=False),
        sa.Column("anterior", sa.Text(), nullable=True),
        sa.Column("novo", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("historico_chamados")
    op.drop_table("comentarios_internos")
