from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr
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

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.get("/csrf")
async def get_csrf_token(response: Response):
    token = str(uuid.uuid4())
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax"
    )
    return {"csrf_token": token}

@router.post("/register", response_model=Token)
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
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
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
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout", dependencies=[Depends(verify_csrf)])
async def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax"
    )
    response.delete_cookie(
        key="csrf_token",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax"
    )
    return {"success": True}

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}
