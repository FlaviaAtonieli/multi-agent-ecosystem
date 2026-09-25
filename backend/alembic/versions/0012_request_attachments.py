"""Add request_attachments (document attached to a TechnicalRequest's context).

RFC UX suggestion from code review (PR #24): let a user attach a document as
extra context for an orchestration, instead of only a freeform text field.
Text-only for this iteration -- content is decoded UTF-8 text read at upload
time (app/core/config.py's ALLOWED_ATTACHMENT_EXTENSIONS names the accepted
plain-text/source-code formats); no binary blob is stored.

Revision ID: 0012_request_attachments
Revises: 0011_github_oauth
Create Date: 2026-09-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0012_request_attachments"
down_revision: str | None = "0011_github_oauth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "request_attachments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "technical_request_id",
            sa.String(length=36),
            sa.ForeignKey("technical_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_request_attachments_technical_request_id",
        "request_attachments",
        ["technical_request_id"],
    )
    op.create_index(
        "ix_request_attachments_uploaded_by_id", "request_attachments", ["uploaded_by_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_request_attachments_uploaded_by_id", table_name="request_attachments")
    op.drop_index("ix_request_attachments_technical_request_id", table_name="request_attachments")
    op.drop_table("request_attachments")
