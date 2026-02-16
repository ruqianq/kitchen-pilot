from pydantic import BaseModel, Field

from kitchen_pilot.schemas.plan import NutritionConfidence, NutritionInfo


class NutritionLookupRequest(BaseModel):
    food: str = Field(min_length=1, description="Food item to look up")
    quantity: float = Field(gt=0, default=1.0)
    unit: str = Field(default="serving")


class NutritionLookupResponse(BaseModel):
    food: str
    normalized_food: str
    nutrition: NutritionInfo
    confidence: NutritionConfidence
    source: str = Field(description="e.g. usda, estimated")


class RecipeNutritionRequest(BaseModel):
    ingredients: list[NutritionLookupRequest]
    servings: int = Field(ge=1, default=1)


class RecipeNutritionResponse(BaseModel):
    per_serving: NutritionInfo
    total: NutritionInfo
    ingredient_details: list[NutritionLookupResponse]
