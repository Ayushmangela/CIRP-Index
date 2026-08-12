"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-08-12 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pg_trgm extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # Enums
    outcome_enum = postgresql.ENUM(
        "admitted",
        "cirp_ongoing",
        "resolution_approved",
        "liquidation",
        "dissolved",
        "withdrawn",
        "unclassified",
        name="outcome_enum",
    )
    outcome_enum.create(op.get_bind(), checkfirst=True)

    processing_status_enum = postgresql.ENUM(
        "discovered",
        "downloaded",
        "text_extracted",
        "scanned_skipped",
        "extracted",
        "failed",
        name="processing_status_enum",
    )
    processing_status_enum.create(op.get_bind(), checkfirst=True)

    link_review_status_enum = postgresql.ENUM(
        "pending",
        "approved",
        "rejected",
        name="link_review_status_enum",
    )
    link_review_status_enum.create(op.get_bind(), checkfirst=True)

    # Orders table
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_date", sa.Date(), nullable=True),
        sa.Column("subject_raw", sa.Text(), nullable=False),
        sa.Column("case_number", sa.String(length=255), nullable=True),
        sa.Column("bench", sa.String(length=255), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=False),
        sa.Column("pdf_sha256", sa.String(length=64), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("remarks_raw", sa.Text(), nullable=True),
        sa.Column("outcome", outcome_enum, nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("is_scanned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("processing_status", processing_status_enum, nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_listing_page", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pdf_url"),
    )
    op.create_index("orders_order_date_idx", "orders", ["order_date"])
    op.create_index("orders_outcome_idx", "orders", ["outcome"])
    op.create_index("orders_bench_idx", "orders", ["bench"])

    # Order Pages table
    op.create_table(
        "order_pages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Cases table
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("canonical_case_number", sa.String(length=255), nullable=True),
        sa.Column("corporate_debtor_name", sa.String(length=512), nullable=False),
        sa.Column("bench", sa.String(length=255), nullable=True),
        sa.Column("first_order_date", sa.Date(), nullable=True),
        sa.Column("latest_order_date", sa.Date(), nullable=True),
        sa.Column("current_outcome", outcome_enum, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "CREATE INDEX cases_corporate_debtor_name_trgm_idx ON cases "
        "USING gin (corporate_debtor_name gin_trgm_ops);"
    )

    # Case Aliases table
    op.create_table(
        "case_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("alias_text", sa.String(length=512), nullable=False),
        sa.Column("alias_type", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Link Review Queue table
    op.create_table(
        "link_review_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("candidate_case_id", sa.Integer(), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=False),
        sa.Column("status", link_review_status_enum, nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["candidate_case_id"], ["cases.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Extracted Fields table
    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_numeric", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("confidence_source", sa.String(length=100), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extraction_method", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "extracted_fields_case_id_field_name_idx",
        "extracted_fields",
        ["case_id", "field_name"],
    )

    # Evidence table
    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("extracted_field_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["extracted_field_id"], ["extracted_fields.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Gold Labels table
    op.create_table(
        "gold_labels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=False),
        sa.Column("labelled_by", sa.String(length=100), nullable=False),
        sa.Column("labelled_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Ingestion Runs table
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pages_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("orders_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("orders_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("orders_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("orders_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("watermark", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_table("gold_labels")
    op.drop_table("evidence")
    op.drop_index(
        "extracted_fields_case_id_field_name_idx", table_name="extracted_fields"
    )
    op.drop_table("extracted_fields")
    op.drop_table("link_review_queue")
    op.drop_table("case_aliases")
    op.execute("DROP INDEX IF EXISTS cases_corporate_debtor_name_trgm_idx;")
    op.drop_table("cases")
    op.drop_table("order_pages")
    op.drop_index("orders_bench_idx", table_name="orders")
    op.drop_index("orders_outcome_idx", table_name="orders")
    op.drop_index("orders_order_date_idx", table_name="orders")
    op.drop_table("orders")

    op.execute("DROP TYPE IF EXISTS link_review_status_enum;")
    op.execute("DROP TYPE IF EXISTS processing_status_enum;")
    op.execute("DROP TYPE IF EXISTS outcome_enum;")
