from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.db.models import User
from app.providers.registry import ProviderRegistry

router = APIRouter()


@router.get("/models")
async def list_models(current_user: User = Depends(get_current_user)):
    return {"providers": ProviderRegistry.catalog_payload()}
