class ApiFrameworkError(Exception):
    """Base exception for the API framework."""


class ApiConfigurationError(ApiFrameworkError):
    """Raised when required API configuration is missing."""


class ApiRequestError(ApiFrameworkError):
    """Raised when an API request cannot be completed."""


class ApiResponseError(ApiFrameworkError):
    """Raised when an API response does not match expectations."""