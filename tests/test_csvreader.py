import asynctest
import pandas as pd
import tempfile
import os

from spade_artifact.common.readers.csvreader import CSVReaderArtifact


class TestCSVReaderArtifact(asynctest.TestCase):

    async def setUp(self):
        self.temp_csv = tempfile.NamedTemporaryFile(delete=False, mode='w+', newline='', suffix='.csv')


        df = pd.DataFrame({'Time': ['2021-01-01 00:00:00', '2021-01-01 00:00:02'],
                           'Value': [100, 101]})
        df.to_csv(self.temp_csv, index=False, header=True)
        self.temp_csv.close()

    async def test_csv_reading(self):
        artifact = CSVReaderArtifact("jid@test.com", "password", self.temp_csv.name, columns=["Time", "Value"],
                                     time_column="Time")

        artifact.publish = asynctest.CoroutineMock()
        artifact.presence = asynctest.MagicMock()
        artifact.presence.set_available = asynctest.CoroutineMock()

        await artifact.run()


        self.assertEqual(artifact.publish.call_count, 2)





    async def tearDown(self):
        os.unlink(self.temp_csv.name)


if __name__ == "__main__":
    asynctest.main()
