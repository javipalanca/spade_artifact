import asynctest

from aioresponses import aioresponses
from spade_artifact.common.readers.apireader import APIReaderArtifact


class TestAPIReaderArtifact(asynctest.TestCase):

    async def setUp(self):
        self.mock_url = "http://mockapi.com/data"
        self.api_response_data = [{"key": "value1"}, {"key": "value2"}]

    @aioresponses()
    async def test_api_reading(self, mocked_responses):
        mocked_responses.get(self.mock_url, payload=self.api_response_data, status=200)

        artifact = APIReaderArtifact("jid@test.com", "password", self.mock_url, http_method="GET")

        artifact.publish = asynctest.CoroutineMock()
        artifact.presence = asynctest.MagicMock()
        artifact.presence.set_available = asynctest.CoroutineMock()

        await artifact.run()

        expected_data = self.api_response_data
        for call_arg in artifact.publish.call_args_list:
            actual_data = call_arg[0][0]
            self.assertEqual(actual_data, expected_data)
