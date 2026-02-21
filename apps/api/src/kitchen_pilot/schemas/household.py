import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    gender: str | None = None
    date_of_birth: str | None = None
    ethnicity: str | None = None
    activity_level: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    health_conditions: list[str] = Field(default_factory=list)


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
    sodium_mg: float | None = Field(default=None, ge=0)
    cholesterol_mg: float | None = Field(default=None, ge=0)
    sugar_g: float | None = Field(default=None, ge=0)
    saturated_fat_g: float | None = Field(default=None, ge=0)
    potassium_mg: float | None = Field(default=None, ge=0)


class HouseholdContext(BaseModel):
    """Normalized household context passed to agents."""

    household_name: str
    timezone: str
    people: list[PersonSchema]
    allergies: list[AllergySchema]
    dietary_rules: list[DietaryRuleSchema]
    preferences: list[FoodPreferenceSchema]
    nutrition_goals: list[NutritionGoalSchema]


# --- CRUD Schemas ---


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    timezone: str = Field(default="UTC", max_length=50)


class HouseholdUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    timezone: str | None = Field(default=None, max_length=50)


class HouseholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=50)
    age_band: str | None = Field(default=None, max_length=20)
    gender: str | None = Field(default=None, max_length=20)
    date_of_birth: str | None = Field(default=None, max_length=10)
    ethnicity: str | None = Field(default=None, max_length=50)
    activity_level: str | None = Field(default=None, max_length=20)


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, min_length=1, max_length=50)
    age_band: str | None = None
    gender: str | None = None
    date_of_birth: str | None = None
    ethnicity: str | None = None
    activity_level: str | None = None


class PersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    household_id: uuid.UUID
    name: str
    role: str
    age_band: str | None
    gender: str | None
    date_of_birth: str | None
    ethnicity: str | None
    activity_level: str | None
    created_at: datetime
    updated_at: datetime


class AllergyCreate(BaseModel):
    person_id: uuid.UUID
    allergen: str = Field(min_length=1, max_length=100)
    severity: AllergenSeverity
    notes: str | None = None


class AllergyUpdate(BaseModel):
    allergen: str | None = Field(default=None, min_length=1, max_length=100)
    severity: AllergenSeverity | None = None
    notes: str | None = None


class AllergyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    person_id: uuid.UUID
    allergen: str
    severity: AllergenSeverity
    notes: str | None
    created_at: datetime


class DietaryRuleCreate(BaseModel):
    household_id: uuid.UUID | None = None
    person_id: uuid.UUID | None = None
    rule: str = Field(min_length=1, max_length=255)
    notes: str | None = None

    @model_validator(mode="after")
    def check_scope(self) -> "DietaryRuleCreate":
        if self.household_id is None and self.person_id is None:
            msg = "At least one of household_id or person_id must be set"
            raise ValueError(msg)
        return self


class DietaryRuleUpdate(BaseModel):
    rule: str | None = Field(default=None, min_length=1, max_length=255)
    notes: str | None = None


class DietaryRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    household_id: uuid.UUID | None
    person_id: uuid.UUID | None
    rule: str
    notes: str | None
    created_at: datetime


class FoodPreferenceCreate(BaseModel):
    household_id: uuid.UUID | None = None
    person_id: uuid.UUID | None = None
    item: str = Field(min_length=1, max_length=255)
    preference: PreferenceLevel
    notes: str | None = None

    @model_validator(mode="after")
    def check_scope(self) -> "FoodPreferenceCreate":
        if self.household_id is None and self.person_id is None:
            msg = "At least one of household_id or person_id must be set"
            raise ValueError(msg)
        return self


class FoodPreferenceUpdate(BaseModel):
    item: str | None = Field(default=None, min_length=1, max_length=255)
    preference: PreferenceLevel | None = None
    notes: str | None = None


class FoodPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    household_id: uuid.UUID | None
    person_id: uuid.UUID | None
    item: str
    preference: PreferenceLevel
    notes: str | None
    created_at: datetime


class NutritionGoalCreate(BaseModel):
    household_id: uuid.UUID | None = None
    person_id: uuid.UUID | None = None
    calories_min: int | None = Field(default=None, ge=0)
    calories_max: int | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)
    sodium_mg: float | None = Field(default=None, ge=0)
    cholesterol_mg: float | None = Field(default=None, ge=0)
    sugar_g: float | None = Field(default=None, ge=0)
    saturated_fat_g: float | None = Field(default=None, ge=0)
    potassium_mg: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_scope(self) -> "NutritionGoalCreate":
        if self.household_id is None and self.person_id is None:
            msg = "At least one of household_id or person_id must be set"
            raise ValueError(msg)
        return self


class NutritionGoalUpdate(BaseModel):
    calories_min: int | None = Field(default=None, ge=0)
    calories_max: int | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)
    sodium_mg: float | None = Field(default=None, ge=0)
    cholesterol_mg: float | None = Field(default=None, ge=0)
    sugar_g: float | None = Field(default=None, ge=0)
    saturated_fat_g: float | None = Field(default=None, ge=0)
    potassium_mg: float | None = Field(default=None, ge=0)


class NutritionGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    household_id: uuid.UUID | None
    person_id: uuid.UUID | None
    calories_min: int | None
    calories_max: int | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    fiber_g: float | None
    sodium_mg: float | None
    cholesterol_mg: float | None
    sugar_g: float | None
    saturated_fat_g: float | None
    potassium_mg: float | None
    created_at: datetime
    updated_at: datetime


# --- Biometric Schemas ---


class BiometricCreate(BaseModel):
    person_id: uuid.UUID
    height_cm: float | None = Field(default=None, ge=0)
    weight_kg: float | None = Field(default=None, ge=0)
    waist_cm: float | None = Field(default=None, ge=0)


class BiometricUpdate(BaseModel):
    height_cm: float | None = Field(default=None, ge=0)
    weight_kg: float | None = Field(default=None, ge=0)
    waist_cm: float | None = Field(default=None, ge=0)


class BiometricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    person_id: uuid.UUID
    height_cm: float | None
    weight_kg: float | None
    bmi: float | None
    waist_cm: float | None
    created_at: datetime
    updated_at: datetime


# --- Health Condition Schemas ---


class HealthConditionCreate(BaseModel):
    person_id: uuid.UUID
    condition: str = Field(min_length=1, max_length=100)
    severity: str | None = Field(default=None, max_length=20)
    notes: str | None = None


class HealthConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    person_id: uuid.UUID
    condition: str
    severity: str | None
    notes: str | None
    created_at: datetime
