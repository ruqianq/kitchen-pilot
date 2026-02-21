"""Add health profile fields.

Expand Person with gender, date_of_birth, ethnicity, activity_level.
Add HealthCondition table.
Expand Biometric with bmi, waist_cm.
Expand NutritionGoal with sodium, cholesterol, sugar, saturated_fat, potassium.

Revision ID: c3d4e5f6a7b8
Revises: b1a2c3d4e5f6
Create Date: 2026-02-21 22:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Person: add health profile columns
    op.add_column("person", sa.Column("gender", sa.String(20), nullable=True))
    op.add_column("person", sa.Column("date_of_birth", sa.String(10), nullable=True))
    op.add_column("person", sa.Column("ethnicity", sa.String(50), nullable=True))
    op.add_column("person", sa.Column("activity_level", sa.String(20), nullable=True))

    # Biometric: add bmi, waist_cm
    op.add_column("biometric", sa.Column("bmi", sa.Float(), nullable=True))
    op.add_column("biometric", sa.Column("waist_cm", sa.Float(), nullable=True))

    # NutritionGoal: add micronutrient targets
    op.add_column("nutrition_goal", sa.Column("sodium_mg", sa.Float(), nullable=True))
    op.add_column("nutrition_goal", sa.Column("cholesterol_mg", sa.Float(), nullable=True))
    op.add_column("nutrition_goal", sa.Column("sugar_g", sa.Float(), nullable=True))
    op.add_column("nutrition_goal", sa.Column("saturated_fat_g", sa.Float(), nullable=True))
    op.add_column("nutrition_goal", sa.Column("potassium_mg", sa.Float(), nullable=True))

    # HealthCondition: new table
    op.create_table(
        "health_condition",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("person.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("condition", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_health_condition_person_id", "health_condition", ["person_id"])


def downgrade() -> None:
    op.drop_index("ix_health_condition_person_id", table_name="health_condition")
    op.drop_table("health_condition")

    op.drop_column("nutrition_goal", "potassium_mg")
    op.drop_column("nutrition_goal", "saturated_fat_g")
    op.drop_column("nutrition_goal", "sugar_g")
    op.drop_column("nutrition_goal", "cholesterol_mg")
    op.drop_column("nutrition_goal", "sodium_mg")

    op.drop_column("biometric", "waist_cm")
    op.drop_column("biometric", "bmi")

    op.drop_column("person", "activity_level")
    op.drop_column("person", "ethnicity")
    op.drop_column("person", "date_of_birth")
    op.drop_column("person", "gender")
