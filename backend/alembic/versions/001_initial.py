"""initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-10-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Teams table
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
    )

    # Team memberships table
    op.create_table(
        "team_memberships",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.Enum("member", "approver", "lead", name="team_role"), nullable=False, server_default="member"),
    )

    # Request types table
    op.create_table(
        "request_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("approval_mode", sa.Enum("none", "before", "after", "both", name="approval_mode"), nullable=False, server_default="none"),
        sa.Column("sla_hours", sa.Integer(), nullable=True),
    )
    op.create_index("ix_request_types_team_id", "request_types", ["team_id"])

    # Requests table
    op.create_table(
        "requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("request_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Enum("new", "triage", "awaiting_start_approval", "in_progress", "awaiting_completion_approval", "done", "cancelled", name="request_status"), nullable=False, server_default="new"),
        sa.Column("priority", sa.Enum("low", "medium", "high", "urgent", name="request_priority"), nullable=False, server_default="medium"),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("search_tsv", postgresql.TSVECTOR(), sa.Computed("to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))", persisted=True), nullable=True),
    )

    op.create_index("ix_requests_team_id", "requests", ["team_id"])
    op.create_index("ix_requests_type_id", "requests", ["type_id"])
    op.create_index("ix_requests_status", "requests", ["status"])
    op.create_index("ix_requests_priority", "requests", ["priority"])
    op.create_index("ix_requests_owner_id", "requests", ["owner_id"])
    op.create_index("ix_requests_created_by", "requests", ["created_by"])
    op.create_index("ix_requests_team_status_activity_id", "requests", ["team_id", "status", sa.text("last_activity_at DESC"), sa.text("id DESC")])
    op.create_index("ix_requests_owner_status", "requests", ["owner_id", "status"])
    op.create_index(
        "ix_requests_unowned_inbox",
        "requests",
        ["team_id", "created_at"],
        postgresql_where=sa.text("owner_id IS NULL AND status IN ('new', 'triage')"),
    )
    op.create_index(
        "ix_requests_active_stale",
        "requests",
        ["team_id", "last_activity_at"],
        postgresql_where=sa.text("status NOT IN ('done', 'cancelled')"),
    )
    op.create_index("ix_requests_search_tsv", "requests", ["search_tsv"], postgresql_using="gin")

    # Request events table
    op.create_table(
        "request_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("from_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("to_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_request_events_request_id_id", "request_events", ["request_id", sa.text("id DESC")])

    # Comments table
    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_comments_request_id", "comments", ["request_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])

    # Idempotency keys table
    op.create_table(
        "idempotency_keys",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Outbox table
    op.create_table(
        "outbox",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("request_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("topic", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Enum("pending", "processing", "done", "dead", name="outbox_status"), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_outbox_status", "outbox", ["status"])
    op.create_index("ix_outbox_pending_attempt", "outbox", ["next_attempt_at"], postgresql_where=sa.text("status = 'pending'"))

    # Notifications table
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(255), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_created_id", "notifications", ["user_id", sa.text("created_at DESC"), sa.text("id DESC")])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("outbox")
    op.drop_table("idempotency_keys")
    op.drop_table("comments")
    op.drop_table("request_events")
    op.drop_table("requests")
    op.drop_table("request_types")
    op.drop_table("team_memberships")
    op.drop_table("teams")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS outbox_status")
    op.execute("DROP TYPE IF EXISTS request_priority")
    op.execute("DROP TYPE IF EXISTS request_status")
    op.execute("DROP TYPE IF EXISTS approval_mode")
    op.execute("DROP TYPE IF EXISTS team_role")
