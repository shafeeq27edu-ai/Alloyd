import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.db.database import check_database, engine, Base
from app.api import auth, keys, chat, conversations, catalog
import app.providers  # To register providers
from app.core.logging_setup import configure_logging, request_id_var
from app.core.router import RuleRouter

configure_logging()
logger = logging.getLogger("alloyd.api")

# Refuse to start if router_config references a provider/model outside the catalog.
RuleRouter.load_and_validate()


async def _wait_for_database() -> None:
    for attempt in range(1, settings.STARTUP_DB_CHECK_RETRIES + 1):
        try:
            await asyncio.wait_for(
                check_database(), timeout=settings.DB_CONNECT_TIMEOUT_SECONDS
            )
        except Exception as exc:
            logger.warning(
                "Database check failed (attempt %s/%s): %s",
                attempt,
                settings.STARTUP_DB_CHECK_RETRIES,
                type(exc).__name__,
            )
            if attempt >= settings.STARTUP_DB_CHECK_RETRIES:
                raise RuntimeError(
                    "Database is not reachable. Check DATABASE_URL."
                ) from exc
            await asyncio.sleep(settings.STARTUP_DB_CHECK_DELAY_SECONDS)
        else:
            logger.info("Database connection verified.")
            return


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _wait_for_database()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def limit_request_size(request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            length = int(content_length)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})
        if length > settings.MAX_REQUEST_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Request body too large."})
    return await call_next(request)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(keys.router, prefix="/api/keys", tags=["keys"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
app.include_router(catalog.router, prefix="/api", tags=["models"])


def _safe_request_id(value: str | None) -> str:
    if value and len(value) <= 64 and value.isascii():
        cleaned = value.replace("-", "").replace("_", "")
        if cleaned.isalnum():
            return value
    return uuid.uuid4().hex


@app.middleware("http")
async def request_context(request, call_next):
    request_id = _safe_request_id(request.headers.get("X-Request-ID"))
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.log(
            logging.ERROR if response is None else logging.INFO,
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code if response is not None else 500,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
        request_id_var.reset(token)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/ready")
async def readiness_check():
    try:
        await asyncio.wait_for(
            check_database(), timeout=settings.DB_CONNECT_TIMEOUT_SECONDS
        )
    except Exception:
        logger.warning("Readiness check failed: database is not reachable.")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ready"}
