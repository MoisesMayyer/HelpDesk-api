"""Cria categorias de chamados."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2f3d4e5f6a7"
down_revision: str | Sequence[str] | None = "b1e2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_table("categorias")
