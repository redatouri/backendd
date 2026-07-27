from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/status", tags=["status"])
async def api_status() -> dict[str, str]:
    """Confirms the versioned API route is available during Phase 1."""
    return {"status": "ok"}
