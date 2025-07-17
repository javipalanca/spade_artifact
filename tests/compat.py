import sys

if sys.version_info >= (3, 10):
    from unittest.mock import AsyncMock, MagicMock, Mock, patch
    from unittest import IsolatedAsyncioTestCase as AsyncTestCase
else:
    from asynctest import Mock, CoroutineMock as AsyncMock, MagicMock, patch
    from asynctest import TestCase as AsyncTestCase

__all__ = ['AsyncMock', 'MagicMock', 'Mock', 'patch', 'AsyncTestCase']
