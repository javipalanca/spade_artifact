import unittest
from unittest.mock import AsyncMock, MagicMock
from aioresponses import aioresponses

from spade_artifact.common.readers.apireader import APIReaderArtifact

class TestAPIReaderArtifact(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.mock_url = "http://mockapi.com/data"
        self.api_response_data = [{"key": "value1"}, {"key": "value2"}]

class TestAPIReaderArtifact(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_url = "http://mockapi.com/data"
        self.api_response_data = [{"key": "value1"}, {"key": "value2"}]

    @aioresponses()
    async def test_api_reading(self, mocked_responses):
        mocked_responses.get(self.mock_url, payload=self.api_response_data, status=200)

        artifact = APIReaderArtifact("jid@test.com", "password", self.mock_url, http_method="GET")
        artifact.publish = AsyncMock()
        artifact.presence = MagicMock()
        artifact.presence.set_available = AsyncMock()

        await artifact.run()

        artifact.publish.assert_awaited_once()
        actual_data = artifact.publish.call_args[0][0]
        self.assertEqual(actual_data, self.api_response_data)
