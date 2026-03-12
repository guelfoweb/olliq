"""Custom exceptions raised by ``olliq``."""


class OlliqError(Exception):
    """Base exception for all package-specific errors."""


class ConfigError(OlliqError):
    """Raised when configuration or input validation fails."""


class AuthError(OlliqError):
    """Raised when cloud authentication data is missing or invalid."""


class GenerationError(OlliqError):
    """Raised when an Ollama request cannot be completed successfully."""
