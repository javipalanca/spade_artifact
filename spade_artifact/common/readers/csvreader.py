import pandas as pd
import asyncio
import spade_artifact

class CSVReaderArtifact(spade_artifact.Artifact):
    def __init__(self, jid, passwd, csv_file, columns=None, frequency=1, time_column=None):
        super().__init__(jid, passwd)
        self.csv_file = csv_file
        self.columns = columns
        self.time_column = time_column
        self.frequency = frequency

    async def setup(self):
        self.presence.set_available()


    async def run(self):
        self.presence.set_available()
        df = pd.read_csv(self.csv_file, usecols=self.columns if self.columns else None)

        last_time = None
        for index, row in df.iterrows():
            if self.time_column and self.time_column in row:
                current_time = pd.to_datetime(row[self.time_column])
                if last_time is not None:
                    wait_time = (current_time - last_time).total_seconds()
                    await asyncio.sleep(wait_time)
                last_time = current_time
            else:
                await asyncio.sleep(self.frequency)

            await self.publish(f"{row.to_dict()}")

        self.presence.set_unavailable()
