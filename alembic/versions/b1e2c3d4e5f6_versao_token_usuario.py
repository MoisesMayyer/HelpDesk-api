"""Adiciona versão dos tokens do usuário."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1e2c3d4e5f6"
down_revision: str | Sequence[str] | None = "8f74bde2df8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("versao_token", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "versao_token")
