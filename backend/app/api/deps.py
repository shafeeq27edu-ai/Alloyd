from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.config import settings
from app.db.database import get_db
from app.db.models import User

def get_token_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        # Fallback to Authorization header if present
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
    return token

async def get_current_user(token: str = Depends(get_token_from_cookie), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

import hmac

def verify_csrf(request: Request):
    # Origin validation
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if origin:
        if origin.startswith("http://") or origin.startswith("https://"):
            parts = origin.split("/")
            origin_base = f"{parts[0]}//{parts[2]}"
            if origin_base not in settings.cors_origins:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unexpected Origin")
    else:
        # Require Origin or Referer for state-changing requests
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing Origin or Referer")

    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_cookie or not csrf_header:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF token")
    
    if not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

