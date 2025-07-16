import asyncio
import getpass

from spade.agent import Agent
from spade_artifact import ArtifactMixin
from loguru import logger
from spade_artifact.common.readers.mongodbreader import MongoDBQueryArtifact
import json

async def data_processor(data):
    """
    Processes data fetched from the in-memory MongoDB.
    """
    last_movie = data[-1]
    title = last_movie.get('title', 'Unknown Title')
    year = last_movie.get('year', 'Unknown Year')
    genres = ', '.join(last_movie.get('genres', ['Unknown Genres']))
    plot = last_movie.get('plot', 'No plot available.')

    messages = [f"Title: {title}\nYear: {year}\nGenres: {genres}\nPlot: {plot}"]
    return messages

class EventsAgent(ArtifactMixin, Agent):
    def __init__(self, *args, artifact_jid: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.artifact_jid = artifact_jid

    def artifact_callback(self, artifact, payload):
        """
        Callback function to handle the data processed by the artifact.
        """
        logger.info(f"Received from {artifact}: {payload}")

    async def setup(self):
        """
        Setup method for the agent.
        """
        await asyncio.sleep(2)
        self.presence.subscribe(self.artifact_jid)
        self.presence.set_available()
        await self.artifacts.focus(self.artifact_jid, self.artifact_callback)
        logger.info("Agent ready and listening to the artifact")

async def main():

    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    XMPP_SERVER = config["XMPP_SERVER"]
    artifact_name = config["artifact_name"]
    artifact_jid = f"{artifact_name}@{XMPP_SERVER}"
    artifact_passwd = getpass.getpass(prompt=f"Password for artifact {artifact_name}> ")

    agent_name = config["agent_name"]
    agent_jid = f"{agent_name}@{XMPP_SERVER}"
    agent_passwd = getpass.getpass(prompt=f"Password for Agent {agent_name}> ")

    time_request = config.get('time_request', None)

    artifact = MongoDBQueryArtifact(
        connection_uri=config["uri"],
        database_name=config["database_name"],
        collection_name=config["collection_name"],
        operation=config["operation"],
        query=config['query'],
        jid=artifact_jid,
        password=artifact_passwd,
        data_processor=data_processor,
        time_request=time_request
    )
    await artifact.start()

    agent = EventsAgent(jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid)
    await agent.start()

    await artifact.join()
    await artifact.stop()
    await agent.stop()

    print("Agents and Artifacts have been stopped")


if __name__ == "__main__":
    asyncio.run(main())
