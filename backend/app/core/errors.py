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
