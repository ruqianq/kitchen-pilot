from enum import StrEnum

from pydantic import BaseModel, Field


class AllergenSeverity(StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class PreferenceLevel(StrEnum):
    LIKE = "like"
    DISLIKE = "dislike"
    AVOID = "avoid"
    FAVORITE = "favorite"


class PersonSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=50, description="e.g. adult, child, partner")
    age_band: str | None = Field(
        default=None, description="e.g. toddler, child, teen, adult, senior"
    )


class AllergySchema(BaseModel):
    person_name: str
    allergen: str = Field(min_length=1, max_length=100)
    severity: AllergenSeverity
    notes: str | None = None


class DietaryRuleSchema(BaseModel):
    scope: str = Field(description="'household' or person name")
    rule: str = Field(min_length=1, max_length=255, description="e.g. vegetarian, halal, keto")
    notes: str | None = None


class FoodPreferenceSchema(BaseModel):
    scope: str = Field(description="'household' or person name")
    item: str = Field(min_length=1, max_length=255)
    preference: PreferenceLevel
    notes: str | None = None


class NutritionGoalSchema(BaseModel):
    scope: str = Field(description="'household' or person name")
    calories_min: int | None = Field(default=None, ge=0)
    calories_max: int | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)


class HouseholdContext(BaseModel):
    """Normalized household context passed to agents."""

    household_name: str
    timezone: str
    people: list[PersonSchema]
    allergies: list[AllergySchema]
    dietary_rules: list[DietaryRuleSchema]
    preferences: list[FoodPreferenceSchema]
    nutrition_goals: list[NutritionGoalSchema]
