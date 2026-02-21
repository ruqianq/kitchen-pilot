"""Tests for web search service and endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from kitchen_pilot.routers.chat import _extract_search_query, _should_search
from kitchen_pilot.routers.search import router
from kitchen_pilot.schemas.search import RecipeSearchResult
from kitchen_pilot.services.web_search import (
    WebSearchError,
    _extract_domain,
)

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ── Utility tests ────────────────────────────────────────


class TestExtractDomain:
    def test_simple_url(self):
        assert _extract_domain("https://allrecipes.com/recipe/123") == "allrecipes.com"

    def test_www_prefix(self):
        assert _extract_domain("https://www.food.com/recipe/123") == "food.com"

    def test_invalid_url(self):
        assert _extract_domain("not a url") == ""


class TestShouldSearch:
    def test_find_recipe(self):
        assert _should_search("find me a chicken recipe")

    def test_search_for_recipe(self):
        assert _should_search("search for pasta dinner")

    def test_look_up_recipe(self):
        assert _should_search("look up a salmon recipe")

    def test_suggest_meal(self):
        assert _should_search("suggest a healthy dinner")

    def test_recipe_for(self):
        assert _should_search("recipe for chocolate cake")

    def test_normal_question(self):
        assert not _should_search("what should I cook tonight?")

    def test_greeting(self):
        assert not _should_search("hello how are you")

    def test_plan_question(self):
        assert not _should_search("when is my meal plan ready?")

    def test_find_diet(self):
        assert _should_search("find me a diet for weight loss")

    def test_diet_for(self):
        assert _should_search("diet for diabetes")

    def test_search_food(self):
        assert _should_search("search for healthy food")


class TestExtractSearchQuery:
    def test_strips_find_me(self):
        q = _extract_search_query("find me a chicken recipe")
        assert "find" not in q.lower()
        assert "chicken" in q.lower()

    def test_strips_search_for(self):
        q = _extract_search_query("search for pasta dinner")
        assert "search" not in q.lower()
        assert "pasta" in q.lower()

    def test_preserves_content(self):
        q = _extract_search_query("recipe for chocolate cake")
        assert "chocolate" in q.lower()


# ── Schema tests ─────────────────────────────────────────


class TestSearchSchemas:
    def test_recipe_search_result(self):
        r = RecipeSearchResult(
            title="Test Recipe",
            url="https://example.com/recipe",
            snippet="A tasty recipe",
            source="example.com",
            score=0.95,
        )
        assert r.title == "Test Recipe"
        assert r.score == 0.95

    def test_result_default_score(self):
        r = RecipeSearchResult(
            title="Test",
            url="https://example.com",
            snippet="test",
            source="example.com",
        )
        assert r.score == 0.0


# ── Endpoint tests ───────────────────────────────────────


class TestSearchEndpoint:
    @patch("kitchen_pilot.routers.search.web_search.search_recipes", new_callable=AsyncMock)
    def test_search_recipes(self, mock_search):
        mock_search.return_value = (
            [
                RecipeSearchResult(
                    title="Chicken Parmesan",
                    url="https://example.com/chicken-parm",
                    snippet="A classic Italian dish",
                    source="example.com",
                    score=0.9,
                ),
            ],
            "tavily",
        )

        response = client.get("/search/recipes?q=chicken+parmesan")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "chicken parmesan"
        assert data["provider"] == "tavily"
        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "Chicken Parmesan"

    @patch("kitchen_pilot.routers.search.web_search.search_recipes", new_callable=AsyncMock)
    def test_search_no_key(self, mock_search):
        mock_search.side_effect = WebSearchError("No search API key configured")
        response = client.get("/search/recipes?q=test")
        assert response.status_code == 400
        assert "No search API key" in response.json()["detail"]

    def test_search_empty_query(self):
        response = client.get("/search/recipes?q=")
        assert response.status_code == 422

    @patch("kitchen_pilot.routers.search.web_search.extract_recipe", new_callable=AsyncMock)
    def test_extract_recipe(self, mock_extract):
        mock_extract.return_value = "Ingredients:\n- 1 cup flour\n- 2 eggs"
        response = client.post(
            "/search/recipes/extract",
            json={"url": "https://example.com/recipe"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://example.com/recipe"
        assert "flour" in data["content"]

    @patch("kitchen_pilot.routers.search.web_search.extract_recipe", new_callable=AsyncMock)
    def test_extract_no_tavily(self, mock_extract):
        mock_extract.return_value = None
        response = client.post(
            "/search/recipes/extract",
            json={"url": "https://example.com/recipe"},
        )
        assert response.status_code == 400
        assert "Tavily" in response.json()["detail"]
