from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import engine, Base
from app.api import auth, keys, chat, conversations
import app.providers  # To register providers

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(keys.router, prefix="/api/keys", tags=["keys"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
