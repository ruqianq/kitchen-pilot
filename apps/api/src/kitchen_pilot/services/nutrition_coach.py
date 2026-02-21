"""Nutrition coach — deterministic calculation engine.

Uses established equations (Mifflin-St Jeor for BMR, activity multipliers
for TDEE) and evidence-based dietary guidelines for health conditions.
No LLM calls — these are pure functions for testability and reliability.
"""

from __future__ import annotations

from datetime import date
from pydantic import BaseModel, Field


# ── Output Schemas ────────────────────────────────────────


class MacroSplit(BaseModel):
    protein_g: float
    protein_pct: float
    carbs_g: float
    carbs_pct: float
    fat_g: float
    fat_pct: float
    fiber_g: float


class MicronutrientLimits(BaseModel):
    sodium_mg_max: float = 2300.0
    cholesterol_mg_max: float = 300.0
    sugar_g_max: float = 50.0
    saturated_fat_g_max: float = 22.0
    potassium_mg_min: float | None = None


class NutritionRecommendation(BaseModel):
    person_name: str
    daily_calories: int
    calorie_rationale: str
    macro_split: MacroSplit
    micronutrient_limits: MicronutrientLimits
    dietary_guidelines: list[str] = Field(default_factory=list)
    foods_to_emphasize: list[str] = Field(default_factory=list)
    foods_to_limit: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ── Constants ─────────────────────────────────────────────


ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "active": 1.55,
    "very_active": 1.725,
}

# Age-band-based calorie defaults when precise data unavailable
AGE_BAND_CALORIES: dict[str, int] = {
    "toddler": 1200,
    "child": 1600,
    "teen": 2200,
    "adult": 2000,
    "senior": 1800,
}

# Condition-specific dietary guidelines (evidence-based)
CONDITION_GUIDELINES: dict[str, dict] = {
    "hypertension": {
        "sodium_mg_max": 1500,
        "dietary_guidelines": [
            "Follow DASH diet principles",
            "Emphasize potassium-rich foods",
            "Limit processed and high-sodium foods",
        ],
        "foods_to_emphasize": [
            "leafy greens", "bananas", "sweet potatoes", "beans",
            "berries", "oats", "fish", "nuts",
        ],
        "foods_to_limit": [
            "processed foods", "canned soups", "deli meats",
            "pickles", "soy sauce", "fast food",
        ],
    },
    "type_2_diabetes": {
        "sugar_g_max": 25,
        "carbs_pct_max": 45,
        "dietary_guidelines": [
            "Focus on low glycemic index foods",
            "Distribute carbs evenly across meals",
            "Pair carbs with protein or healthy fats",
        ],
        "foods_to_emphasize": [
            "whole grains", "non-starchy vegetables", "lean proteins",
            "legumes", "nuts", "seeds",
        ],
        "foods_to_limit": [
            "white bread", "sugary drinks", "candy",
            "fruit juice", "white rice", "pastries",
        ],
    },
    "heart_disease": {
        "sodium_mg_max": 2000,
        "saturated_fat_g_max": 13,
        "cholesterol_mg_max": 200,
        "dietary_guidelines": [
            "Limit saturated fat to <6% of calories",
            "Emphasize omega-3 fatty acids",
            "Eat plenty of fruits and vegetables",
        ],
        "foods_to_emphasize": [
            "salmon", "mackerel", "walnuts", "flaxseed",
            "olive oil", "avocado", "whole grains",
        ],
        "foods_to_limit": [
            "red meat", "butter", "fried foods",
            "full-fat dairy", "trans fats", "processed meats",
        ],
    },
    "high_cholesterol": {
        "cholesterol_mg_max": 200,
        "saturated_fat_g_max": 13,
        "dietary_guidelines": [
            "Increase soluble fiber intake",
            "Choose unsaturated fats over saturated",
            "Add plant sterols and stanols",
        ],
        "foods_to_emphasize": [
            "oats", "barley", "beans", "lentils",
            "nuts", "olive oil", "fatty fish",
        ],
        "foods_to_limit": [
            "organ meats", "full-fat dairy", "fried foods",
            "processed snacks", "coconut oil",
        ],
    },
    "kidney_disease": {
        "sodium_mg_max": 1500,
        "dietary_guidelines": [
            "Limit sodium, potassium, and phosphorus intake",
            "Monitor protein intake as advised by your doctor",
            "Stay hydrated within recommended limits",
        ],
        "foods_to_emphasize": [
            "cabbage", "cauliflower", "bell peppers",
            "apples", "cranberries", "egg whites",
        ],
        "foods_to_limit": [
            "bananas", "oranges", "tomatoes", "potatoes",
            "dairy", "processed meats", "whole grains",
        ],
        "potassium_mg_min": None,
    },
    "celiac": {
        "dietary_guidelines": [
            "Strictly avoid all gluten-containing grains",
            "Check labels for hidden gluten sources",
            "Choose certified gluten-free products",
        ],
        "foods_to_emphasize": [
            "rice", "quinoa", "corn", "potatoes",
            "fruits", "vegetables", "meat", "fish",
        ],
        "foods_to_limit": [
            "wheat", "barley", "rye", "malt",
            "beer", "most breads", "pasta (unless GF)",
        ],
    },
    "gerd": {
        "dietary_guidelines": [
            "Eat smaller, more frequent meals",
            "Avoid eating 2-3 hours before bedtime",
            "Elevate head of bed while sleeping",
        ],
        "foods_to_emphasize": [
            "oatmeal", "ginger", "lean meats",
            "non-citrus fruits", "green vegetables",
        ],
        "foods_to_limit": [
            "citrus fruits", "tomatoes", "chocolate",
            "coffee", "alcohol", "spicy foods", "fried foods",
        ],
    },
    "ibs": {
        "dietary_guidelines": [
            "Consider a low-FODMAP diet",
            "Eat slowly and at regular times",
            "Keep a food diary to identify triggers",
        ],
        "foods_to_emphasize": [
            "rice", "oats", "bananas", "blueberries",
            "carrots", "chicken", "eggs",
        ],
        "foods_to_limit": [
            "beans", "lentils", "onions", "garlic",
            "dairy (if lactose intolerant)", "artificial sweeteners",
        ],
    },
    "gout": {
        "dietary_guidelines": [
            "Limit purine-rich foods",
            "Stay well hydrated",
            "Avoid alcohol, especially beer",
        ],
        "foods_to_emphasize": [
            "cherries", "low-fat dairy", "vegetables",
            "whole grains", "nuts", "water",
        ],
        "foods_to_limit": [
            "organ meats", "shellfish", "red meat",
            "beer", "sugary drinks",
        ],
    },
}


# ── Core Calculations ─────────────────────────────────────


def compute_age(date_of_birth: str) -> int | None:
    """Compute age in years from ISO date string."""
    try:
        dob = date.fromisoformat(date_of_birth)
        today = date.today()
        age = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            age -= 1
        return age
    except (ValueError, TypeError):
        return None


def compute_bmr(
    gender: str, age: int, height_cm: float, weight_kg: float
) -> float:
    """Mifflin-St Jeor equation for Basal Metabolic Rate."""
    if gender == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def compute_tdee(bmr: float, activity_level: str | None) -> float:
    """Total Daily Energy Expenditure = BMR * activity multiplier."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level or "", 1.2)
    return bmr * multiplier


def compute_macro_split(
    daily_calories: int,
    conditions: list[str] | None = None,
) -> MacroSplit:
    """Compute macro split based on calories and health conditions.

    Default split: 30% protein, 40% carbs, 30% fat.
    Adjusted for conditions (e.g., diabetes → lower carbs).
    """
    protein_pct = 0.30
    carbs_pct = 0.40
    fat_pct = 0.30

    if conditions:
        for c in conditions:
            guideline = CONDITION_GUIDELINES.get(c, {})
            max_carbs = guideline.get("carbs_pct_max")
            if max_carbs and max_carbs / 100 < carbs_pct:
                carbs_pct = max_carbs / 100
                protein_pct = (1.0 - carbs_pct) * 0.5
                fat_pct = (1.0 - carbs_pct) * 0.5

    protein_g = round((daily_calories * protein_pct) / 4, 1)
    carbs_g = round((daily_calories * carbs_pct) / 4, 1)
    fat_g = round((daily_calories * fat_pct) / 9, 1)
    fiber_g = round(daily_calories / 1000 * 14, 1)  # 14g per 1000 cal

    return MacroSplit(
        protein_g=protein_g,
        protein_pct=round(protein_pct * 100, 1),
        carbs_g=carbs_g,
        carbs_pct=round(carbs_pct * 100, 1),
        fat_g=fat_g,
        fat_pct=round(fat_pct * 100, 1),
        fiber_g=fiber_g,
    )


def compute_micronutrient_limits(
    daily_calories: int,
    conditions: list[str] | None = None,
) -> MicronutrientLimits:
    """Compute micronutrient limits based on conditions."""
    limits = MicronutrientLimits(
        saturated_fat_g_max=round(daily_calories * 0.10 / 9, 1),
    )

    if conditions:
        for c in conditions:
            guideline = CONDITION_GUIDELINES.get(c, {})
            if "sodium_mg_max" in guideline:
                limits.sodium_mg_max = min(
                    limits.sodium_mg_max, guideline["sodium_mg_max"]
                )
            if "cholesterol_mg_max" in guideline:
                limits.cholesterol_mg_max = min(
                    limits.cholesterol_mg_max, guideline["cholesterol_mg_max"]
                )
            if "sugar_g_max" in guideline:
                limits.sugar_g_max = min(
                    limits.sugar_g_max, guideline["sugar_g_max"]
                )
            if "saturated_fat_g_max" in guideline:
                limits.saturated_fat_g_max = min(
                    limits.saturated_fat_g_max, guideline["saturated_fat_g_max"]
                )
            if "potassium_mg_min" in guideline:
                limits.potassium_mg_min = guideline["potassium_mg_min"]

    return limits


# ── Public API ────────────────────────────────────────────


def generate_recommendation(
    person_name: str,
    gender: str | None = None,
    age_years: int | None = None,
    date_of_birth: str | None = None,
    height_cm: float | None = None,
    weight_kg: float | None = None,
    activity_level: str | None = None,
    age_band: str | None = None,
    health_conditions: list[str] | None = None,
) -> NutritionRecommendation:
    """Generate a personalized nutrition recommendation.

    Works with whatever data is available — from minimal (age_band only)
    to comprehensive (full health profile).
    """
    conditions = health_conditions or []
    warnings: list[str] = []

    # Resolve age
    if age_years is None and date_of_birth:
        age_years = compute_age(date_of_birth)

    # Compute daily calories
    if gender and age_years and height_cm and weight_kg:
        bmr = compute_bmr(gender, age_years, height_cm, weight_kg)
        tdee = compute_tdee(bmr, activity_level)
        daily_calories = round(tdee)
        rationale = (
            f"Based on Mifflin-St Jeor equation for "
            f"{age_years}yo {activity_level or 'sedentary'} {gender} "
            f"({height_cm}cm, {weight_kg}kg): "
            f"BMR={round(bmr)} × {ACTIVITY_MULTIPLIERS.get(activity_level or '', 1.2)} "
            f"= {daily_calories} kcal/day"
        )
    elif age_band:
        daily_calories = AGE_BAND_CALORIES.get(age_band, 2000)
        rationale = f"Estimated from age band '{age_band}' (generic recommendation)"
        warnings.append(
            "Add height, weight, and gender to your profile for a precise calculation."
        )
    else:
        daily_calories = 2000
        rationale = "Default recommendation (no health profile data available)"
        warnings.append(
            "Add your health profile data for personalized recommendations."
        )

    # Compute macros and micronutrient limits
    macro_split = compute_macro_split(daily_calories, conditions)
    micro_limits = compute_micronutrient_limits(daily_calories, conditions)

    # Gather condition-specific guidelines
    dietary_guidelines: list[str] = []
    foods_to_emphasize: list[str] = []
    foods_to_limit: list[str] = []

    for c in conditions:
        guideline = CONDITION_GUIDELINES.get(c, {})
        dietary_guidelines.extend(guideline.get("dietary_guidelines", []))
        foods_to_emphasize.extend(guideline.get("foods_to_emphasize", []))
        foods_to_limit.extend(guideline.get("foods_to_limit", []))

    # Add standard warnings for health conditions
    if conditions:
        warnings.append(
            "These are general dietary guidelines, not medical advice. "
            "Consult your healthcare provider for personalized recommendations."
        )

    # Deduplicate
    foods_to_emphasize = list(dict.fromkeys(foods_to_emphasize))
    foods_to_limit = list(dict.fromkeys(foods_to_limit))

    return NutritionRecommendation(
        person_name=person_name,
        daily_calories=daily_calories,
        calorie_rationale=rationale,
        macro_split=macro_split,
        micronutrient_limits=micro_limits,
        dietary_guidelines=dietary_guidelines,
        foods_to_emphasize=foods_to_emphasize,
        foods_to_limit=foods_to_limit,
        warnings=warnings,
    )
