"""Smoke-test real provider credentials and catalog model IDs.

Run this yourself, from a terminal where the provider keys are exported:
    GROQ_API_KEY=... ANTHROPIC_API_KEY=... GEMINI_API_KEY=... \
        python backend/scripts/smoke_providers.py

The script never prints or logs key values. It validates each configured key,
lists the provider's currently available models, warns if a catalog ID is
missing, and sends one tiny message per catalog model.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Adapters import Settings; provide harmless placeholders when only smoke-testing.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "smoke-script-placeholder-secret-key-1234")
if not os.environ.get("ENCRYPTION_KEY"):
    from cryptography.fernet import Fernet
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from app.config import settings
from app.core.errors import ProviderError
from app.providers.registry import ProviderRegistry
import app.providers  # noqa: F401 - registers adapters

ENV_KEYS = {
    "groq": ("GROQ_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}


def configured_key(provider: str) -> str | None:
    for name in ENV_KEYS[provider]:
        value = os.environ.get(name)
        if value:
            return value
    return None


async def list_remote_models(provider: str, api_key: str) -> list[str]:
    if provider == "groq":
        import groq
        client = groq.AsyncGroq(api_key=api_key, timeout=settings.PROVIDER_TIMEOUT_SECONDS)
        page = await client.models.list()
        return [m.id for m in page.data]

    if provider == "anthropic":
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key, timeout=settings.PROVIDER_TIMEOUT_SECONDS)
        page = await client.models.list(limit=100)
        return [m.id for m in page.data]

    if provider == "gemini":
        from google import genai
        from google.genai import types
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(settings.PROVIDER_TIMEOUT_SECONDS * 1000)),
        )
        names = []
        async for model in await client.aio.models.list():
            names.append(model.name.removeprefix("models/"))
        return names

    return []


async def smoke_provider(provider: str, api_key: str) -> bool:
    adapter = ProviderRegistry.get_adapter(provider)
    models = adapter.get_models()
    all_ok = True

    print(f"\n[{provider}] validating key...")
    started = time.perf_counter()
    try:
        await adapter.validate_key(api_key)
        elapsed = int((time.perf_counter() - started) * 1000)
        print(f"[{provider}/key] PASS ({elapsed} ms)")
    except ProviderError as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        print(f"[{provider}/key] FAIL ({exc.code.value}) {elapsed} ms")
        return False
    except Exception as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        print(f"[{provider}/key] FAIL ({type(exc).__name__}) {elapsed} ms")
        return False

    try:
        remote = await list_remote_models(provider, api_key)
        print(f"[{provider}/models] {len(remote)} available")
        missing = [m.id for m in models if m.id not in remote]
        if missing:
            print(f"[{provider}/models] WARNING catalog IDs missing remotely: {', '.join(missing)}")
    except ProviderError as exc:
        print(f"[{provider}/models] WARNING could not list models ({exc.code.value})")
    except Exception as exc:
        print(f"[{provider}/models] WARNING could not list models ({type(exc).__name__})")

    for model in models:
        started = time.perf_counter()
        try:
            reply = await asyncio.wait_for(
                adapter.send_message(
                    api_key,
                    model.id,
                    [{"role": "user", "content": "Reply with exactly: OK"}],
                ),
                timeout=settings.PROVIDER_TIMEOUT_SECONDS + 5,
            )
            elapsed = int((time.perf_counter() - started) * 1000)
            print(f"{provider}/{model.id}: PASS ({elapsed} ms) reply={reply.strip()[:20]!r}")
        except ProviderError as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            print(f"{provider}/{model.id}: FAIL ({exc.code.value}) {elapsed} ms")
            all_ok = False
        except Exception as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            print(f"{provider}/{model.id}: FAIL ({type(exc).__name__}) {elapsed} ms")
            all_ok = False

    return all_ok


async def main() -> int:
    providers = [name for name in ENV_KEYS if configured_key(name)]
    if not providers:
        print("No provider keys found in the environment.")
        print("Set GROQ_API_KEY, ANTHROPIC_API_KEY, and/or GEMINI_API_KEY, then rerun.")
        return 2

    results = {}
    for provider in providers:
        results[provider] = await smoke_provider(provider, configured_key(provider))

    skipped = [name for name in ENV_KEYS if name not in providers]
    if skipped:
        print(f"\nSkipped (no key in environment): {', '.join(skipped)}")

    failed = [name for name, ok in results.items() if not ok]
    if failed:
        print(f"\nFAILED providers: {', '.join(failed)}")
        return 1

    print("\nAll configured providers passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
