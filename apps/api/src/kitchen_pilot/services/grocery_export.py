"""Grocery export service.

Handles ingredient normalization, CSV generation, and retailer search links.
"""

import csv
import io
import re
from urllib.parse import quote_plus

# Common plural→singular mappings for ingredients
PLURAL_RULES: list[tuple[str, str]] = [
    (r"ies$", "y"),       # berries→berry, cherries→cherry
    (r"ves$", "f"),       # halves→half, loaves→loaf
    (r"oes$", "o"),       # tomatoes→tomato, potatoes→potato
    (r"ses$", "s"),       # sauces→sauce (keep one s)
    (r"s$", ""),          # onions→onion, carrots→carrot
]

ABBREVIATIONS: dict[str, str] = {
    "evoo": "extra virgin olive oil",
    "oj": "orange juice",
    "pb": "peanut butter",
}

ARTICLES = {"a", "an", "the", "some"}


def normalize_ingredient(name: str) -> str:
    """Normalize an ingredient name for display and export."""
    name = name.strip().lower()
    if not name:
        return name

    # Expand abbreviations
    if name in ABBREVIATIONS:
        name = ABBREVIATIONS[name]

    # Strip leading articles
    words = name.split()
    if words and words[0] in ARTICLES:
        words = words[1:]
    name = " ".join(words)

    # Singularize (simple rule-based)
    for pattern, replacement in PLURAL_RULES:
        new_name = re.sub(pattern, replacement, name)
        if new_name != name:
            name = new_name
            break

    return name.strip().title()


def generate_csv(items: list[dict]) -> str:
    """Generate a CSV string from shopping list items.

    Columns: Category, Item, Quantity, Unit
    Sorted by category then item name.
    """
    sorted_items = sorted(items, key=lambda x: (x.get("category", "Other"), x.get("name", "")))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Item", "Quantity", "Unit"])

    for item in sorted_items:
        writer.writerow([
            item.get("category", "Other"),
            normalize_ingredient(item.get("name", "")),
            item.get("quantity", 0),
            item.get("unit", ""),
        ])

    return output.getvalue()


def get_retailer_links(item_name: str) -> dict[str, str]:
    """Generate retailer search URLs for an ingredient."""
    q = quote_plus(item_name)
    return {
        "walmart": f"https://www.walmart.com/search?q={q}",
        "instacart": f"https://www.instacart.com/store/search/{q}",
        "google": f"https://www.google.com/search?tbm=shop&q={q}",
    }
