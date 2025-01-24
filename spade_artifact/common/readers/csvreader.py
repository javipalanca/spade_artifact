import pandas as pd
import asyncio
import spade_artifact
from loguru import logger

class CSVReaderArtifact(spade_artifact.Artifact):
    """
    An artifact for asynchronously reading and processing data from CSV files.

    This artifact reads data from a CSV file and publishes each row at regular intervals or based on a time column.

    Attributes:
        csv_file (str): Path to the CSV file to be read.
        columns (list[str], optional): A list of column names to read from the CSV file. If None, all columns are read.
        frequency (int, optional): The frequency in seconds at which rows are published if no time_column is specified. Defaults to 1.
        time_column (str, optional): The name of the column that contains timestamp information. If specified, rows are published based on the time difference between rows instead of the fixed frequency.

    Args:
        jid (str): The JID (Jabber Identifier) of the artifact.
        passwd (str): The password for the artifact to authenticate with the XMPP server.
        csv_file (str): Path to the CSV file to be read.
        columns (list[str], optional): A list of column names to read from the CSV file. Defaults to None.
        frequency (int, optional): The frequency in seconds at which rows are published if no time_column is specified. Defaults to 1.
        time_column (str, optional): The name of the column that contains timestamp information.

    """
    def __init__(self, jid, passwd, csv_file, columns=None, frequency=1, time_column=None):
        super().__init__(jid, passwd)
        self.csv_file = csv_file
        self.columns = columns
        self.frequency = frequency
        self.time_column = time_column

    async def setup(self):
        """
        Sets up the artifact by marking its presence as available on the XMPP server.
        """
        self.presence.set_available()

    async def run(self):
        """
        Starts the artifact's main operation of reading from the CSV and publishing rows.

        This method reads the CSV file row by row, and if a time_column is specified, it waits for the time difference between the current and last row before publishing the next row. If no time_column is specified, it publishes rows at a fixed frequency defined by the `frequency` attribute.
        """
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
        logger.info("Finished reading CSV file")
        self.presence.set_unavailable()
