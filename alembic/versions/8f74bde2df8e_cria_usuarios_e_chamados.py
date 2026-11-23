"""cria usuarios e chamados

Revision ID: 8f74bde2df8e
Revises:
Create Date: 2026-11-23 15:47:07.927104

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f74bde2df8e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum("funcionario", "tecnico", "administrador", name="perfilusuario"),
            nullable=False,
        ),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "chamados",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("id_tecnico", sa.Integer(), nullable=True),
        sa.Column("titulo", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("aberto_em", sa.DateTime(), nullable=False),
        sa.Column("concluido_em", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "aberto",
                "em_andamento",
                "aguardando_resposta",
                "resolvido",
                "fechado",
                name="statuschamado",
            ),
            nullable=False,
        ),
        sa.Column(
            "prioridade",
            sa.Enum(
                "nao_classificada",
                "baixa",
                "media",
                "alta",
                "critica",
                name="prioridadechamado",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id_tecnico"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("chamados")
    op.drop_table("usuarios")
