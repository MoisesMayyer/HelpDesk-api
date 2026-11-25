"""Associa chamados a categorias, preservando chamados anteriores."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "d3f4e5a6b7c8"
down_revision: str | Sequence[str] | None = "c2f3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("Esta migração requer conexão para verificar chamados existentes.")
    conexao = op.get_bind()
    op.add_column("chamados", sa.Column("id_categoria", sa.Integer(), nullable=True))
    if conexao.execute(sa.text("SELECT 1 FROM chamados LIMIT 1")).first():
        resultado = conexao.execute(
            sa.text("INSERT INTO categorias (nome, ativo) VALUES (:nome, :ativo)"),
            {"nome": "Geral", "ativo": True},
        )
        conexao.execute(
            sa.text("UPDATE chamados SET id_categoria = :categoria"),
            {"categoria": resultado.lastrowid},
        )
    op.alter_column(
        "chamados", "id_categoria", existing_type=sa.Integer(), nullable=False
    )
    op.create_foreign_key(
        "fk_chamados_categoria", "chamados", "categorias", ["id_categoria"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_chamados_categoria", "chamados", type_="foreignkey")
    op.drop_column("chamados", "id_categoria")
