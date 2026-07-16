from unittest.mock import MagicMock

from slixmpp.exceptions import IqError


class AsyncContextManagerMock:
    """Mock for async context managers with nested mocking capabilities."""

    def __init__(self, mock):
        self.mock = mock

    async def __aenter__(self):
        return self.mock

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def request(self, *args, **kwargs):
        return self.mock

    def get(self, *args, **kwargs):
        return self.mock


class MockException(IqError, MagicMock):
    pass
