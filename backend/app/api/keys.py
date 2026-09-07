from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import ProviderKey, User
from app.core.encryption import encrypt_key
from app.api.deps import get_current_user

router = APIRouter()

class KeyCreate(BaseModel):
    provider_name: str
    key: str

@router.post("/", status_code=201)
async def add_provider_key(
    key_in: KeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if key for provider already exists for this user
    result = await db.execute(
        select(ProviderKey).where(
            ProviderKey.user_id == current_user.id,
            ProviderKey.provider_name == key_in.provider_name
        )
    )
    existing_key = result.scalars().first()
    
    encrypted = encrypt_key(key_in.key)
    
    if existing_key:
        existing_key.encrypted_key = encrypted
    else:
        new_key = ProviderKey(
            user_id=current_user.id,
            provider_name=key_in.provider_name,
            encrypted_key=encrypted
        )
        db.add(new_key)
        
    await db.commit()
    
    return {"success": True, "provider": key_in.provider_name, "message": "Key stored securely."}
