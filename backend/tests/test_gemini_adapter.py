import httpx
from google.genai.errors import APIError

from app.core.errors import ErrorCode
from app.providers.gemini_adapter import GeminiAdapter


def api_error(code, message="request failed", reason=None):
    details = [{"reason": reason}] if reason else []
    return APIError(code, {
        "error": {"code": code, "message": message, "status": "ERROR", "details": details}
    })


def test_system_prompt_is_extracted_not_dropped():
    adapter = GeminiAdapter()
    messages = [
        {"role": "system", "content": "You are a code reviewer."},
        {"role": "user", "content": "Review this."},
        {"role": "assistant", "content": "Looks fine."},
    ]
    assert adapter._system_instruction(messages) == "You are a code reviewer."
    assert adapter._convert_messages(messages) == [
        {"role": "user", "parts": [{"text": "Review this."}]},
        {"role": "model", "parts": [{"text": "Looks fine."}]},
    ]


def test_multiple_system_messages_are_joined():
    adapter = GeminiAdapter()
    messages = [
        {"role": "system", "content": "One."},
        {"role": "system", "content": "Two."},
        {"role": "user", "content": "Hello"},
    ]
    assert adapter._system_instruction(messages) == "One.\n\nTwo."


def test_no_system_message_returns_none():
    adapter = GeminiAdapter()
    assert adapter._system_instruction([{"role": "user", "content": "Hi"}]) is None


def test_gemini_timeout_maps_to_timeout():
    adapter = GeminiAdapter()
    error = adapter._map_error(TimeoutError())
    assert error.code == ErrorCode.TIMEOUT
    assert error.retryable is True


def test_gemini_invalid_key_400_maps_to_invalid_key():
    adapter = GeminiAdapter()
    error = adapter._map_error(api_error(400, "API key not valid", reason="API_KEY_INVALID"))
    assert error.code == ErrorCode.INVALID_API_KEY
    assert error.retryable is False


def test_gemini_generic_400_maps_to_bad_request():
    adapter = GeminiAdapter()
    assert adapter._map_error(api_error(400)).code == ErrorCode.BAD_REQUEST


def test_gemini_404_maps_to_model_unavailable():
    adapter = GeminiAdapter()
    assert adapter._map_error(api_error(404)).code == ErrorCode.MODEL_UNAVAILABLE


def test_gemini_500_maps_to_retryable_unavailable():
    adapter = GeminiAdapter()
    error = adapter._map_error(api_error(500))
    assert error.code == ErrorCode.PROVIDER_UNAVAILABLE
    assert error.retryable is True


def test_gemini_connection_error_maps_to_retryable_unavailable():
    adapter = GeminiAdapter()
    error = adapter._map_error(httpx.ConnectError("boom"))
    assert error.code == ErrorCode.PROVIDER_UNAVAILABLE
    assert error.retryable is True
