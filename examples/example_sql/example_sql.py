import asyncio
import getpass
import json
import os
from spade.agent import Agent
import sqlite3
from spade_artifact import ArtifactMixin
from loguru import logger
from spade_artifact.common.readers.sqlreader import DatabaseQueryArtifact


def create_in_memory_database():
    """
    Creates an in-memory SQLite database and populates it with sample data.
    """
    conn = sqlite3.connect("mydatabase.db")
    cur = conn.cursor()

    cur.execute('''CREATE TABLE events (name TEXT, date TEXT, location TEXT)''')

    sample_data = [
        ('Event 1', '2024-04-15', 'Location A'),
        ('Event 2', '2024-05-20', 'Location B'),
        ('Event 3', '2024-06-25', 'Location C')
    ]
    cur.executemany('INSERT INTO events VALUES (?,?,?)', sample_data)

    conn.commit()
    return conn


async def events_data_processor(data):
    """
    Processes data fetched from the database.
    """
    messages = []
    event = data[-1]
    event_name, event_date, event_location = event
    messages.append(f"Event: {event_name}, Date: {event_date}, Location: {event_location}")
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
    in_memory_db = create_in_memory_database()

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

    artifact = DatabaseQueryArtifact(
        jid=artifact_jid,
        password=artifact_passwd,
        db_type=config["db_type"],
        connection_params=config["connection_params"],
        query=config["query"],
        data_processor=events_data_processor,
        time_request=time_request
    )
    await artifact.start()

    agent = EventsAgent(jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid)
    await agent.start()

    await artifact.join()

    await artifact.stop()
    await agent.stop()

    print("Agents and Artifacts have been stopped")

    cur = in_memory_db.cursor()
    cur.execute("DROP TABLE IF EXISTS events")
    in_memory_db.commit()
    in_memory_db.close()

    os.remove("mydatabase.db")


if __name__ == "__main__":
    asyncio.run(main())
