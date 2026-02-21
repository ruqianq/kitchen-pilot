"""Add vector extension and HNSW index on memory_documents.

Revision ID: b1a2c3d4e5f6
Revises: 068c0cc09a20
Create Date: 2026-02-21 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, None] = "068c0cc09a20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memory_documents_embedding_hnsw "
        "ON memory_documents USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
    op.create_index(
        "ix_memory_documents_household_id",
        "memory_documents",
        ["household_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_memory_documents_household_id", table_name="memory_documents")
    op.drop_index(
        "ix_memory_documents_embedding_hnsw", table_name="memory_documents"
    )
