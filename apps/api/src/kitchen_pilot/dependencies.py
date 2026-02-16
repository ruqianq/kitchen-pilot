"""Shared FastAPI dependencies."""

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.db.engine import get_session
from kitchen_pilot.db.models import Household
from kitchen_pilot.services.household import get_or_create_household


async def get_current_household(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Household:
    """Return the single default household, auto-creating on first request."""
    return await get_or_create_household(session)


async def get_household_id(
    household: Household = Depends(get_current_household),  # noqa: B008
) -> uuid.UUID:
    """Convenience dependency returning just the household UUID."""
    return household.id
