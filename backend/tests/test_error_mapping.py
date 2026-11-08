import pytest

from app.core.errors import ErrorCode, provider_error_from_status, timeout_error


@pytest.mark.parametrize("status,code,retryable", [
    (401, ErrorCode.INVALID_API_KEY, False),
    (403, ErrorCode.INVALID_API_KEY, False),
    (404, ErrorCode.MODEL_UNAVAILABLE, False),
    (429, ErrorCode.RATE_LIMIT, True),
    (400, ErrorCode.BAD_REQUEST, False),
    (422, ErrorCode.BAD_REQUEST, False),
    (500, ErrorCode.PROVIDER_UNAVAILABLE, True),
    (502, ErrorCode.PROVIDER_UNAVAILABLE, True),
    (503, ErrorCode.PROVIDER_UNAVAILABLE, True),
    (418, ErrorCode.UNKNOWN, False),
])
def test_status_mapping(status, code, retryable):
    error = provider_error_from_status("groq", status)
    assert error.code == code
    assert error.retryable is retryable
    assert error.provider == "groq"


def test_timeout_error_is_retryable():
    error = timeout_error("anthropic")
    assert error.code == ErrorCode.TIMEOUT
    assert error.retryable is True
    assert "anthropic" in error.message


def test_error_dict_has_no_raw_detail():
    error = provider_error_from_status("gemini", 500)
    payload = error.to_dict()
    assert payload["code"] == "PROVIDER_UNAVAILABLE"
    assert payload["retryable"] is True
