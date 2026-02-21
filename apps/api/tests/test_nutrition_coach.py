"""Tests for the nutrition coach deterministic calculation engine."""

import pytest

from kitchen_pilot.services.nutrition_coach import (
    AGE_BAND_CALORIES,
    CONDITION_GUIDELINES,
    MacroSplit,
    MicronutrientLimits,
    NutritionRecommendation,
    compute_age,
    compute_bmr,
    compute_macro_split,
    compute_micronutrient_limits,
    compute_tdee,
    generate_recommendation,
)


# ── compute_age ───────────────────────────────────────────


def test_compute_age_valid_dob():
    # Use a date that will always be in the past
    age = compute_age("1990-01-15")
    assert age is not None
    assert age >= 35  # Test written in 2026


def test_compute_age_invalid_string():
    assert compute_age("not-a-date") is None


def test_compute_age_none():
    assert compute_age(None) is None


def test_compute_age_future_birthday_this_year():
    """If birthday hasn't occurred yet this year, age should be one less."""
    age = compute_age("1990-12-31")
    assert age is not None
    # In Feb 2026, birthday hasn't happened yet
    assert age >= 35


# ── compute_bmr ───────────────────────────────────────────


def test_bmr_male():
    """Male: 10*80 + 6.25*180 - 5*30 + 5 = 800+1125-150+5 = 1780"""
    bmr = compute_bmr("male", 30, 180.0, 80.0)
    assert bmr == pytest.approx(1780.0)


def test_bmr_female():
    """Female: 10*60 + 6.25*165 - 5*25 - 161 = 600+1031.25-125-161 = 1345.25"""
    bmr = compute_bmr("female", 25, 165.0, 60.0)
    assert bmr == pytest.approx(1345.25)


def test_bmr_nonbinary_uses_female():
    """Non-binary/other defaults to the female equation."""
    bmr_other = compute_bmr("other", 30, 170.0, 70.0)
    bmr_female = compute_bmr("female", 30, 170.0, 70.0)
    assert bmr_other == bmr_female


# ── compute_tdee ──────────────────────────────────────────


def test_tdee_sedentary():
    tdee = compute_tdee(1500.0, "sedentary")
    assert tdee == pytest.approx(1800.0)


def test_tdee_active():
    tdee = compute_tdee(1500.0, "active")
    assert tdee == pytest.approx(1500.0 * 1.55)


def test_tdee_very_active():
    tdee = compute_tdee(1500.0, "very_active")
    assert tdee == pytest.approx(1500.0 * 1.725)


def test_tdee_none_defaults_sedentary():
    tdee = compute_tdee(1500.0, None)
    assert tdee == pytest.approx(1800.0)


def test_tdee_unknown_defaults_sedentary():
    tdee = compute_tdee(1500.0, "unknown_level")
    assert tdee == pytest.approx(1800.0)


# ── compute_macro_split ──────────────────────────────────


def test_default_macro_split():
    macros = compute_macro_split(2000)
    assert macros.protein_pct == 30.0
    assert macros.carbs_pct == 40.0
    assert macros.fat_pct == 30.0
    # 2000 * 0.30 / 4 = 150g protein
    assert macros.protein_g == pytest.approx(150.0)
    # 2000 * 0.40 / 4 = 200g carbs
    assert macros.carbs_g == pytest.approx(200.0)
    # 2000 * 0.30 / 9 ≈ 66.7g fat
    assert macros.fat_g == pytest.approx(66.7, abs=0.1)
    # 14g per 1000 cal = 28g fiber
    assert macros.fiber_g == pytest.approx(28.0)


def test_diabetes_does_not_increase_carbs():
    """Diabetes carbs_pct_max=45 is > default 40%, so no change."""
    macros = compute_macro_split(2000, conditions=["type_2_diabetes"])
    assert macros.carbs_pct == 40.0  # default 40% already below 45% cap
    assert macros.protein_pct + macros.carbs_pct + macros.fat_pct == pytest.approx(100.0)


def test_no_conditions_keeps_default():
    macros = compute_macro_split(2000, conditions=[])
    assert macros.carbs_pct == 40.0


def test_unknown_condition_keeps_default():
    macros = compute_macro_split(2000, conditions=["nonexistent"])
    assert macros.carbs_pct == 40.0


# ── compute_micronutrient_limits ─────────────────────────


def test_default_micronutrient_limits():
    limits = compute_micronutrient_limits(2000)
    assert limits.sodium_mg_max == 2300.0
    assert limits.cholesterol_mg_max == 300.0
    assert limits.sugar_g_max == 50.0
    # 2000 * 0.10 / 9 ≈ 22.2
    assert limits.saturated_fat_g_max == pytest.approx(22.2, abs=0.1)


def test_hypertension_sodium_limit():
    limits = compute_micronutrient_limits(2000, conditions=["hypertension"])
    assert limits.sodium_mg_max == 1500.0


def test_heart_disease_limits():
    limits = compute_micronutrient_limits(2000, conditions=["heart_disease"])
    assert limits.sodium_mg_max == 2000.0
    assert limits.cholesterol_mg_max == 200.0
    assert limits.saturated_fat_g_max == 13.0


def test_diabetes_sugar_limit():
    limits = compute_micronutrient_limits(2000, conditions=["type_2_diabetes"])
    assert limits.sugar_g_max == 25.0


def test_multiple_conditions_uses_strictest():
    """When multiple conditions apply, the strictest limits win."""
    limits = compute_micronutrient_limits(
        2000, conditions=["hypertension", "heart_disease"]
    )
    assert limits.sodium_mg_max == 1500.0  # hypertension is stricter
    assert limits.cholesterol_mg_max == 200.0  # heart_disease limit


# ── generate_recommendation ──────────────────────────────


def test_full_profile_recommendation():
    rec = generate_recommendation(
        person_name="Alice",
        gender="female",
        age_years=30,
        height_cm=165.0,
        weight_kg=60.0,
        activity_level="active",
        health_conditions=["hypertension"],
    )
    assert rec.person_name == "Alice"
    assert rec.daily_calories > 0
    assert "Mifflin-St Jeor" in rec.calorie_rationale
    assert rec.micronutrient_limits.sodium_mg_max == 1500.0
    assert len(rec.dietary_guidelines) > 0
    assert len(rec.foods_to_emphasize) > 0
    assert len(rec.warnings) > 0  # health condition warning


def test_age_band_only_recommendation():
    rec = generate_recommendation(
        person_name="Child",
        age_band="child",
    )
    assert rec.daily_calories == AGE_BAND_CALORIES["child"]
    assert "age band" in rec.calorie_rationale
    assert any("profile" in w.lower() for w in rec.warnings)


def test_minimal_recommendation():
    rec = generate_recommendation(person_name="Unknown")
    assert rec.daily_calories == 2000
    assert "Default" in rec.calorie_rationale


def test_dob_resolves_age():
    rec = generate_recommendation(
        person_name="Bob",
        gender="male",
        date_of_birth="1990-01-15",
        height_cm=180.0,
        weight_kg=80.0,
        activity_level="sedentary",
    )
    assert rec.daily_calories > 0
    assert "Mifflin-St Jeor" in rec.calorie_rationale


def test_condition_guidelines_populated():
    rec = generate_recommendation(
        person_name="Alice",
        gender="female",
        age_years=50,
        height_cm=160.0,
        weight_kg=70.0,
        health_conditions=["type_2_diabetes", "hypertension"],
    )
    assert len(rec.dietary_guidelines) > 3  # Both conditions contribute
    assert rec.micronutrient_limits.sodium_mg_max == 1500.0
    assert rec.micronutrient_limits.sugar_g_max == 25.0


def test_foods_deduplicated():
    """When multiple conditions share food recommendations, they are deduplicated."""
    rec = generate_recommendation(
        person_name="Test",
        health_conditions=["heart_disease", "high_cholesterol"],
    )
    # Check no duplicates in food lists
    assert len(rec.foods_to_emphasize) == len(set(rec.foods_to_emphasize))
    assert len(rec.foods_to_limit) == len(set(rec.foods_to_limit))


# ── CONDITION_GUIDELINES coverage ────────────────────────


def test_all_conditions_have_guidelines():
    """Every condition in CONDITION_GUIDELINES should have dietary_guidelines."""
    for condition, guidelines in CONDITION_GUIDELINES.items():
        assert "dietary_guidelines" in guidelines, f"{condition} missing dietary_guidelines"
        assert "foods_to_emphasize" in guidelines, f"{condition} missing foods_to_emphasize"
        assert "foods_to_limit" in guidelines, f"{condition} missing foods_to_limit"
