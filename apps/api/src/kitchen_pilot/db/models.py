import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --- Enums ---


class PlanStatus(enum.StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Preference(enum.StrEnum):
    LIKE = "like"
    DISLIKE = "dislike"
    AVOID = "avoid"
    FAVORITE = "favorite"


class Severity(enum.StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


# --- Models ---


class Household(Base):
    __tablename__ = "household"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    people: Mapped[list["Person"]] = relationship(back_populates="household")
    plans: Mapped[list["WeeklyPlan"]] = relationship(back_populates="household")


class Person(Base):
    __tablename__ = "person"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50))
    age_band: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    household: Mapped["Household"] = relationship(back_populates="people")
    allergies: Mapped[list["Allergy"]] = relationship(back_populates="person")

    __table_args__ = (Index("ix_person_household_id", "household_id"),)


class Allergy(Base):
    __tablename__ = "allergy"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE")
    )
    allergen: Mapped[str] = mapped_column(String(100))
    severity: Mapped[Severity] = mapped_column(Enum(Severity))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    person: Mapped["Person"] = relationship(back_populates="allergies")

    __table_args__ = (Index("ix_allergy_person_id", "person_id"),)


class DietaryRule(Base):
    __tablename__ = "dietary_rule"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE")
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE")
    )
    rule: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "household_id IS NOT NULL OR person_id IS NOT NULL",
            name="ck_dietary_rule_scope",
        ),
        Index("ix_dietary_rule_household_id", "household_id"),
        Index("ix_dietary_rule_person_id", "person_id"),
    )


class FoodPreference(Base):
    __tablename__ = "food_preference"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE")
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE")
    )
    item: Mapped[str] = mapped_column(String(255))
    preference: Mapped[Preference] = mapped_column(Enum(Preference))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "household_id IS NOT NULL OR person_id IS NOT NULL",
            name="ck_food_preference_scope",
        ),
        Index("ix_food_preference_household_id", "household_id"),
        Index("ix_food_preference_person_id", "person_id"),
    )


class NutritionGoal(Base):
    __tablename__ = "nutrition_goal"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE")
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE")
    )
    calories_min: Mapped[int | None] = mapped_column(Integer)
    calories_max: Mapped[int | None] = mapped_column(Integer)
    protein_g: Mapped[float | None] = mapped_column()
    carbs_g: Mapped[float | None] = mapped_column()
    fat_g: Mapped[float | None] = mapped_column()
    fiber_g: Mapped[float | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "household_id IS NOT NULL OR person_id IS NOT NULL",
            name="ck_nutrition_goal_scope",
        ),
    )


class Biometric(Base):
    __tablename__ = "biometric"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE")
    )
    height_cm: Mapped[float | None] = mapped_column()
    weight_kg: Mapped[float | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WeeklyPlan(Base):
    __tablename__ = "weekly_plan"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE")
    )
    week_start_date: Mapped[str] = mapped_column(String(10))
    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus), default=PlanStatus.DRAFT
    )
    plan_json: Mapped[dict | None] = mapped_column(JSONB)
    summary_md: Mapped[str | None] = mapped_column(Text)
    model_info_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    household: Mapped["Household"] = relationship(back_populates="plans")
    meals: Mapped[list["Meal"]] = relationship(back_populates="weekly_plan")

    __table_args__ = (
        Index("ix_weekly_plan_household_week", "household_id", "week_start_date"),
    )


class Meal(Base):
    __tablename__ = "meal"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    weekly_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("weekly_plan.id", ondelete="CASCADE")
    )
    date: Mapped[str] = mapped_column(String(10))
    meal_type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255))
    recipe_source_url: Mapped[str | None] = mapped_column(Text)
    cook_time_min: Mapped[int | None] = mapped_column(Integer)
    servings: Mapped[int | None] = mapped_column(Integer)
    ingredients_json: Mapped[dict | None] = mapped_column(JSONB)
    nutrition_json: Mapped[dict | None] = mapped_column(JSONB)
    flags_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    weekly_plan: Mapped["WeeklyPlan"] = relationship(back_populates="meals")


class ShoppingList(Base):
    __tablename__ = "shopping_list"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    weekly_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("weekly_plan.id", ondelete="CASCADE"), unique=True
    )
    items_json: Mapped[dict | None] = mapped_column(JSONB)
    exports_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NutritionCache(Base):
    __tablename__ = "nutrition_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    query: Mapped[str] = mapped_column(Text)
    normalized_food: Mapped[str] = mapped_column(String(255))
    nutrition_json: Mapped[dict | None] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[str] = mapped_column(String(20))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_nutrition_cache_normalized_food", "normalized_food"),)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("household.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(100))
    payload_json: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE")
    )
    provider: Mapped[str] = mapped_column(String(50))
    encrypted_access_token: Mapped[bytes] = mapped_column(LargeBinary)
    encrypted_refresh_token: Mapped[bytes] = mapped_column(LargeBinary)
    token_expiry: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "ix_oauth_tokens_household_provider",
            "household_id",
            "provider",
            unique=True,
        ),
    )


class MemoryDocument(Base):
    __tablename__ = "memory_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE")
    )
    doc_type: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
