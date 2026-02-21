"""Tests for grocery export service — normalization, CSV, retailer links."""

from kitchen_pilot.services.grocery_export import (
    generate_csv,
    get_retailer_links,
    normalize_ingredient,
)


# ── Normalization ────────────────────────────────────────


class TestNormalizeIngredient:
    def test_basic_titlecase(self):
        assert normalize_ingredient("chicken breast") == "Chicken Breast"

    def test_strips_whitespace(self):
        assert normalize_ingredient("  garlic  ") == "Garlic"

    def test_empty_string(self):
        assert normalize_ingredient("") == ""

    def test_singularize_s(self):
        assert normalize_ingredient("onions") == "Onion"
        assert normalize_ingredient("carrots") == "Carrot"

    def test_singularize_oes(self):
        assert normalize_ingredient("tomatoes") == "Tomato"
        assert normalize_ingredient("potatoes") == "Potato"

    def test_singularize_ies(self):
        assert normalize_ingredient("berries") == "Berry"
        assert normalize_ingredient("cherries") == "Cherry"

    def test_singularize_ves(self):
        assert normalize_ingredient("halves") == "Half"

    def test_singularize_ses(self):
        assert normalize_ingredient("sauces") == "Sauce"

    def test_expand_abbreviation(self):
        assert normalize_ingredient("evoo") == "Extra Virgin Olive Oil"
        assert normalize_ingredient("oj") == "Orange Juice"
        assert normalize_ingredient("pb") == "Peanut Butter"

    def test_strip_article_a(self):
        assert normalize_ingredient("a lemon") == "Lemon"

    def test_strip_article_an(self):
        assert normalize_ingredient("an onion") == "Onion"

    def test_strip_article_the(self):
        assert normalize_ingredient("the chicken") == "Chicken"

    def test_strip_article_some(self):
        assert normalize_ingredient("some rice") == "Rice"


# ── CSV Generation ───────────────────────────────────────


class TestGenerateCsv:
    def test_header_row(self):
        csv_str = generate_csv([])
        assert csv_str.startswith("Category,Item,Quantity,Unit")

    def test_single_item(self):
        items = [{"name": "chicken breast", "quantity": 2, "unit": "lbs", "category": "Meat"}]
        csv_str = generate_csv(items)
        lines = csv_str.strip().split("\n")
        assert len(lines) == 2
        assert "Chicken Breast" in lines[1]
        assert "Meat" in lines[1]

    def test_sorted_by_category_then_name(self):
        items = [
            {"name": "banana", "quantity": 6, "unit": "pcs", "category": "Produce"},
            {"name": "milk", "quantity": 1, "unit": "gal", "category": "Dairy"},
            {"name": "apple", "quantity": 4, "unit": "pcs", "category": "Produce"},
        ]
        csv_str = generate_csv(items)
        lines = csv_str.strip().split("\n")
        # Dairy before Produce; Apple before Banana
        assert "Dairy" in lines[1]
        assert "Apple" in lines[2]
        assert "Banana" in lines[3]

    def test_missing_fields_use_defaults(self):
        items = [{"name": "salt"}]
        csv_str = generate_csv(items)
        lines = csv_str.strip().split("\n")
        assert len(lines) == 2
        assert "Other" in lines[1]  # default category
        assert "Salt" in lines[1]

    def test_normalizes_names(self):
        items = [{"name": "tomatoes", "quantity": 3, "unit": "pcs", "category": "Produce"}]
        csv_str = generate_csv(items)
        assert "Tomato" in csv_str


# ── Retailer Links ───────────────────────────────────────


class TestGetRetailerLinks:
    def test_returns_all_three_retailers(self):
        links = get_retailer_links("chicken breast")
        assert "walmart" in links
        assert "instacart" in links
        assert "google" in links

    def test_walmart_url(self):
        links = get_retailer_links("chicken breast")
        assert links["walmart"] == "https://www.walmart.com/search?q=chicken+breast"

    def test_instacart_url(self):
        links = get_retailer_links("chicken breast")
        assert links["instacart"] == "https://www.instacart.com/store/search/chicken+breast"

    def test_google_url(self):
        links = get_retailer_links("chicken breast")
        assert links["google"] == "https://www.google.com/search?tbm=shop&q=chicken+breast"

    def test_url_encodes_special_chars(self):
        links = get_retailer_links("jalapeño pepper")
        assert "jalape" in links["walmart"]
        # Ensure it doesn't contain raw spaces
        assert " " not in links["walmart"]
