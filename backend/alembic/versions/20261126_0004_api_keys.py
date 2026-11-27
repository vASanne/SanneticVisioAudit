"""API users, agent keys, usage events, and idempotency records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261126_0004"
down_revision: str | None = "20261115_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(length=320), nullable=True)
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=True)
    op.add_column(
        "users",
        sa.Column("is_api_user", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key_id", sa.String(80), nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("key_id", name="uq_api_keys_key_id"),
    )
    op.create_index("ix_api_keys_key_id", "api_keys", ["key_id"])
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_client_id", "api_keys", ["client_id"])
    op.create_table(
        "api_key_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("key_id", sa.String(80), nullable=False, server_default=""),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("method", sa.String(8), nullable=False, server_default=""),
        sa.Column("path", sa.String(200), nullable=False, server_default=""),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_api_key_events_api_key_id", "api_key_events", ["api_key_id"])
    op.create_index("ix_api_key_events_created_at", "api_key_events", ["created_at"])
    op.create_table(
        "api_idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_body", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("api_key_id", "idempotency_key", name="uq_api_idempotency_key"),
    )
    op.create_index("ix_api_idempotency_keys_api_key_id", "api_idempotency_keys", ["api_key_id"])


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE is_api_user IS TRUE")
    op.drop_index("ix_api_idempotency_keys_api_key_id", table_name="api_idempotency_keys")
    op.drop_table("api_idempotency_keys")
    op.drop_index("ix_api_key_events_created_at", table_name="api_key_events")
    op.drop_index("ix_api_key_events_api_key_id", table_name="api_key_events")
    op.drop_table("api_key_events")
    op.drop_index("ix_api_keys_client_id", table_name="api_keys")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_index("ix_api_keys_key_id", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_column("users", "is_api_user")
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(length=320), nullable=False)
