class Error(Exception):
    pass


class TransportAPIError(Error):
    """Raised when a request to TransportAPI fails with status >=500"""
    pass


class OpenLDBWSError(Error):
    """Raised when a request to OpenLDBWS fails due to upstream causes"""
    pass


class DynamoDBError(Error):
    """Raised when a request to DynamoDB fails with status >=500"""
    pass


class ApplicationError(Error):
    """Raised when an unknown error occurs."""
    pass


class EntityResolutionError(Error):
    """Raised when both Alexa and RailUK fail to resolve a requested station"""
    pass


class AmbiguousERError(Error):
    """Raised Entity Resolution provided ambiguous results"""
    pass
