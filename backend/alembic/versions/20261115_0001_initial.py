"""Initial client, audit, page, issue, and score tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261115_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("pages_crawled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("seo_score", sa.Float(), nullable=True),
        sa.Column("geo_score", sa.Float(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_table(
        "pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("html_storage_path", sa.Text(), nullable=True),
        sa.Column("extract", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("crawled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("check_id", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("affected_urls", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("quick_win", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_table(
        "scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_table("scores")
    op.drop_table("issues")
    op.drop_table("pages")
    op.drop_table("audits")
    op.drop_table("clients")
