from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr, field_validator
from app.db.database import get_db
from app.db.models import User
from app.core.security import verify_password, get_password_hash, create_access_token
from datetime import timedelta
from app.config import settings
import uuid
from app.api.deps import get_current_user, verify_csrf
from app.core.rate_limit import check_rate_limit, get_client_ip
from fastapi import Request

router = APIRouter()


def _auth_cookie_settings() -> dict:
    return {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
        "domain": settings.cookie_domain,
    }


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")
        if len(v.encode('utf-8')) > 72:
            raise ValueError("Password is too long (maximum 72 bytes)")
        return v

@router.get("/csrf")
async def get_csrf_token(response: Response):
    token = str(uuid.uuid4())
    response.set_cookie(
        key="csrf_token",
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_auth_cookie_settings(),
    )
    return {"csrf_token": token}

@router.post("/register", dependencies=[Depends(verify_csrf)])
async def register(request: Request, user_in: UserCreate, response: Response, db: AsyncSession = Depends(get_db)):
    await check_rate_limit(
        f"register:{get_client_ip(request)}",
        settings.REGISTRATION_RATE_LIMIT,
        settings.REGISTRATION_RATE_WINDOW
    )
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_pw = get_password_hash(user_in.password)
    user = User(email=user_in.email, hashed_password=hashed_pw)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_auth_cookie_settings(),
    )
    return {"success": True}

@router.post("/token", dependencies=[Depends(verify_csrf)])
async def login_for_access_token(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    await check_rate_limit(
        f"login:{get_client_ip(request)}:{form_data.username}",
        settings.LOGIN_RATE_LIMIT,
        settings.LOGIN_RATE_WINDOW
    )
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_auth_cookie_settings(),
    )
    return {"success": True}

@router.post("/logout", dependencies=[Depends(verify_csrf)])
async def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        **_auth_cookie_settings(),
    )
    response.delete_cookie(
        key="csrf_token",
        **_auth_cookie_settings(),
    )
    return {"success": True}

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}
