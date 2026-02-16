import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.config import settings
from kitchen_pilot.db.engine import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)) -> dict:  # noqa: B008
    checks: dict[str, str] = {}

    # Check database connectivity
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Check Ollama connectivity
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            resp = await http.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                checks["ollama"] = "ok"
            else:
                checks["ollama"] = f"error: status {resp.status_code}"
    except Exception as e:
        checks["ollama"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}
