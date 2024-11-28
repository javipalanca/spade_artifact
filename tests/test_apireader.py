from tests.compat import AsyncTestCase, AsyncMock, MagicMock
from aioresponses import aioresponses
from spade_artifact.common.readers.apireader import APIReaderArtifact

class TestAPIReaderArtifact(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.mock_url = "http://mockapi.com/data"
        self.api_response_data = [{"key": "value1"}, {"key": "value2"}]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.mock_url = "http://mockapi.com/data"
        self.api_response_data = [{"key": "value1"}, {"key": "value2"}]

    @aioresponses()
    async def test_api_reading(self, mocked_responses):
        mocked_responses.get(self.mock_url, payload=self.api_response_data, status=200)

        artifact = APIReaderArtifact("jid@test.com", "password", api_url=self.mock_url, http_method="GET")

        artifact.publish = AsyncMock()
        artifact.presence = MagicMock()
        artifact.presence.set_available = AsyncMock()

        await artifact.run()

        expected_data = self.api_response_data
        for call_arg in artifact.publish.call_args_list:
            actual_data = call_arg[0][0]
            self.assertEqual(actual_data, expected_data)
