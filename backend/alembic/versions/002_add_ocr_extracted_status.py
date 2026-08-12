"""add ocr_extracted to processing_status_enum

Revision ID: 002_add_ocr_extracted_status
Revises: 001_initial_schema
Create Date: 2026-08-12 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_add_ocr_extracted_status"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # See docs/decisions/0004-ocr-as-separate-labelled-pipeline.md - OCR'd
    # text is never conflated with real-extracted text_extracted orders.
    op.execute(
        "ALTER TYPE processing_status_enum ADD VALUE IF NOT EXISTS 'ocr_extracted'"
    )


def downgrade() -> None:
    # Postgres has no DROP VALUE for enums. A downgrade would require
    # rebuilding the type, which is destructive to any ocr_extracted rows -
    # out of scope for a no-op-safe downgrade.
    raise NotImplementedError(
        "Cannot drop an enum value in Postgres without rebuilding the type."
    )
