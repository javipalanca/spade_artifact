from tests.compat import AsyncTestCase, AsyncMock, MagicMock
import pandas as pd
import tempfile
import os
from spade_artifact.common.readers.csvreader import CSVReaderArtifact

class TestCSVReaderArtifact(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.temp_csv = tempfile.NamedTemporaryFile(delete=False, mode='w+', newline='', suffix='.csv')
        df = pd.DataFrame({
            'Time': ['2021-01-01 00:00:00', '2021-01-01 00:00:02'],
            'Value': [100, 101]
        })
        df.to_csv(self.temp_csv, index=False, header=True)
        self.temp_csv.close()
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.temp_csv = tempfile.NamedTemporaryFile(delete=False, mode='w+', newline='', suffix='.csv')
        df = pd.DataFrame({
            'Time': ['2021-01-01 00:00:00', '2021-01-01 00:00:02'],
            'Value': [100, 101]
        })
        df.to_csv(self.temp_csv, index=False, header=True)
        self.temp_csv.close()

    async def test_csv_reading(self):
        artifact = CSVReaderArtifact("jid@test.com", "password", csv_file=self.temp_csv.name,
                                   columns=["Time", "Value"], time_column="Time")
        artifact.publish = AsyncMock()
        artifact.presence = MagicMock()
        artifact.presence.set_available = AsyncMock()

        await artifact.run()

        self.assertEqual(artifact.publish.call_count, 2)

        expected_data = [
            {"Time": "2021-01-01 00:00:00", "Value": 100},
            {"Time": "2021-01-01 00:00:02", "Value": 101}
        ]

        for call_arg, expected in zip(artifact.publish.call_args_list, expected_data):
            actual_data = call_arg[0][0]
            self.assertEqual(eval(actual_data), expected)

    def tearDown(self):
        if hasattr(self, 'temp_csv'):
            try:
                os.unlink(self.temp_csv.name)
            except:
                pass
        super().tearDown()

    async def asyncTearDown(self):
        if hasattr(self, 'temp_csv'):
            try:
                os.unlink(self.temp_csv.name)
            except:
                pass
        await super().asyncTearDown()
