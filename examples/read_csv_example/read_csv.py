
import asyncio

import getpass
import json
from loguru import logger
from spade.agent import Agent

from spade_artifact import ArtifactMixin


from spade_artifact.common.readers.csvreader import CSVReaderArtifact



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
    agent_passwd = getpass.getpass(prompt=f"Password for Agent {agent_name}> ")

    csv_file_path = config["csv_file_path"]
    columns_to_read = config["columns_to_read"]

    time_column = config.get("time_column", None)
    read_frequency = config.get("read_frequency", 1)


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
