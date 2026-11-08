from app.core.errors import ErrorCode
from app.providers.gemini_adapter import GeminiAdapter


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
