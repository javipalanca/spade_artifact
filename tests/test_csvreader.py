import unittest
from unittest.mock import AsyncMock, MagicMock
import pandas as pd
import tempfile
import os
from spade_artifact.common.readers.csvreader import CSVReaderArtifact


class TestCSVReaderArtifact(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_csv = tempfile.NamedTemporaryFile(delete=False, mode='w+', newline='', suffix='.csv')
        df = pd.DataFrame({
            'Time': ['2021-01-01 00:00:00', '2021-01-01 00:00:02'],
            'Value': [100, 101]
        })
        df.to_csv(self.temp_csv, index=False, header=True)
        self.temp_csv.close()

    async def test_csv_reading(self):
        artifact = CSVReaderArtifact(
            "jid@test.com", "password", self.temp_csv.name,
            columns=["Time", "Value"], time_column="Time"
        )

        artifact.publish = AsyncMock()
        artifact.presence = MagicMock()
        artifact.presence.set_available = MagicMock()

        await artifact.run()

        self.assertEqual(artifact.publish.call_count, 2)

        expected_data = [
            {"Time": "2021-01-01 00:00:00", "Value": 100},
            {"Time": "2021-01-01 00:00:02", "Value": 101}
        ]

        for call_arg, expected in zip(artifact.publish.call_args_list, expected_data):
            actual_data = call_arg[0][0]
            self.assertEqual(eval(actual_data), expected)

    async def asyncTearDown(self):
        os.unlink(self.temp_csv.name)
