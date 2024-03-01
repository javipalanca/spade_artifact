import pandas as pd
import asyncio
import random
import getpass
import json
from loguru import logger
from spade.agent import Agent
import spade_artifact
from spade_artifact import ArtifactMixin


class CSVReaderArtifact(spade_artifact.Artifact):
    def __init__(self, jid, passwd, csv_file, columns, frequency,time_column):
        super().__init__(jid, passwd)
        self.csv_file = csv_file
        self.columns = columns
        self.frequency = frequency
        self.time_column = time_column

    async def setup(self):
        self.presence.set_available()

    async def run(self):
        self.presence.set_available()
        df = pd.read_csv(self.csv_file, usecols=self.columns)

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



class ConsumerAgent(ArtifactMixin, Agent):
    def __init__(self, *args, artifact_jid: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.artifact_jid = artifact_jid

    def artifact_callback(self, artifact, payload):
        logger.info(f"Received from {artifact}: {payload}")

    async def setup(self):
        await asyncio.sleep(2)  #
        self.presence.subscribe(self.artifact_jid)
        self.presence.set_available()
        await self.artifacts.focus(self.artifact_jid, self.artifact_callback)
        logger.info("Agent ready and listening to the artifact")



async def main():
    # Cargar configuración desde el archivo JSON
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)

    XMPP_SERVER = config["XMPP_SERVER"]
    artifact_name = config["artifact_name"]
    artifact_jid = f"{artifact_name}@{XMPP_SERVER}"
    artifact_passwd = getpass.getpass(prompt=f"Password for artifact {artifact_name}> ")

    agent_name = config["agent_name"]
    agent_jid = f"{agent_name}@{XMPP_SERVER}"
    agent_passwd = getpass.getpass(prompt=f"Password for Agent {artifact_name}> ")

    csv_file_path = config["csv_file_path"]
    columns_to_read = config["columns_to_read"]

    time_column = config.get("time_column", None)
    read_frequency = None if time_column else config.get("read_frequency", 1)


    artifact = CSVReaderArtifact(artifact_jid, artifact_passwd, csv_file_path, columns_to_read,
                                 read_frequency, time_column)
    await artifact.start()

    agent = ConsumerAgent(jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid)
    await agent.start()
    await artifact.join()
    await artifact.stop()
    await agent.stop()

    print("Agents and Artifacts have been stopped")


if __name__ == "__main__":
    asyncio.run(main())
