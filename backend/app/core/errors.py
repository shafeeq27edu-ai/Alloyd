from enum import Enum

class ErrorCode(str, Enum):
    INVALID_API_KEY = "INVALID_API_KEY"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    CAPABILITY_NOT_SUPPORTED = "CAPABILITY_NOT_SUPPORTED"
    BAD_REQUEST = "BAD_REQUEST"
    UNKNOWN = "UNKNOWN"

class ProviderError(Exception):
    def __init__(self, code: ErrorCode, provider: str, message: str, retryable: bool):
        self.code = code
        self.provider = provider
        self.message = message
        self.retryable = retryable
        super().__init__(self.message)

    def to_dict(self):
        return {
            "code": self.code.value,
            "provider": self.provider,
            "message": self.message,
            "retryable": self.retryable
        }


def provider_error_from_status(provider: str, status_code: int) -> ProviderError:
    """Map an HTTP status from a provider API to a safe, normalized error."""
    if status_code in (401, 403):
        return ProviderError(
            ErrorCode.INVALID_API_KEY, provider,
            f"The {provider} API key appears to be invalid.", False
        )
    if status_code == 404:
        return ProviderError(
            ErrorCode.MODEL_UNAVAILABLE, provider,
            "The selected model is not available from this provider.", False
        )
    if status_code == 429:
        return ProviderError(
            ErrorCode.RATE_LIMIT, provider,
            f"{provider} is rate limiting requests. Try again shortly.", True
        )
    if status_code in (400, 422):
        return ProviderError(
            ErrorCode.BAD_REQUEST, provider,
            f"{provider} rejected the request.", False
        )
    if 500 <= status_code < 600:
        return ProviderError(
            ErrorCode.PROVIDER_UNAVAILABLE, provider,
            f"{provider} is temporarily unavailable.", True
        )
    return ProviderError(
        ErrorCode.UNKNOWN, provider, f"{provider} request failed.", False
    )


def timeout_error(provider: str) -> ProviderError:
    return ProviderError(
        ErrorCode.TIMEOUT, provider,
        f"{provider} took too long to respond.", True
    )
