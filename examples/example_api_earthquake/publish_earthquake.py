import asyncio
import getpass
from datetime import datetime, timedelta
from urllib.parse import urlencode
import json
from spade.agent import Agent
from spade_artifact.common.readers.apireader import APIReaderArtifact
from spade_artifact import ArtifactMixin
from loguru import logger

class EarthquakeReaderArtifact(APIReaderArtifact):
    def __init__(self, jid, passwd, api_url, data_processor=None, http_method='GET', params=None, headers=None,
                 time_request=None):
        super().__init__(jid, passwd, api_url, data_processor, http_method, params, headers, time_request)

    async def update_url(self):
        start_time = (datetime.utcnow() - timedelta(minutes=3)).strftime('%Y-%m-%dT%H:%M:%S')
        end_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        parameters = {
            'format': 'geojson',
            'starttime': start_time,
            'endtime': end_time,
            'minmagnitude': '4'
        }
        self.api_url = f"{self.url_template}?{urlencode(parameters)}"
        print(f"la url actualizada : {self.api_url}")


async def earthquake_data_processor(data):
    if not data['features']:
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return [f"No hay datos registrados para el tiempo: {current_time}"]

    messages = []
    for earthquake in data['features']:
        place = earthquake['properties']['place']
        magnitude = earthquake['properties']['mag']
        time = datetime.utcfromtimestamp(earthquake['properties']['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        messages.append(f"Lugar: {place}, Magnitud: {magnitude}, Hora: {time}")
    return messages

class EarthquakeAgent(ArtifactMixin, Agent):
    def __init__(self, *args, artifact_jid: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.artifact_jid = artifact_jid

    def artifact_callback(self, artifact, payload):
        logger.info(f"Received from {artifact}: {payload}")

    async def setup(self):
        await asyncio.sleep(2)
        self.presence.subscribe(self.artifact_jid)
        self.presence.set_available()
        await self.artifacts.focus(self.artifact_jid, self.artifact_callback)
        logger.info("Agent ready and listening to the artifact")

async def main():
    with open('config_earthquake.json', 'r') as config_file:
        config = json.load(config_file)

    XMPP_SERVER = config["XMPP_SERVER"]
    artifact_name = config["artifact_name"]
    artifact_jid = f"{artifact_name}@{XMPP_SERVER}"
    artifact_passwd = getpass.getpass(prompt=f"Password for artifact {artifact_name}> ")

    agent_name = config["agent_name"]
    agent_jid = f"{agent_name}@{XMPP_SERVER}"
    agent_passwd = getpass.getpass(prompt=f"Password for Agent {agent_name}> ")

    api_url = config.get('api_url')
    time_request = config.get('time_request', None)

    artifact = EarthquakeReaderArtifact(
        jid=artifact_jid, passwd=artifact_passwd, api_url=api_url,
        data_processor=earthquake_data_processor, time_request=time_request
    )
    await artifact.start()

    agent = EarthquakeAgent(jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid)
    await agent.start()
    await artifact.join()
    await artifact.stop()
    await agent.stop()

    print("Agents and Artifacts have been stopped")

if __name__ == "__main__":
    asyncio.run(main())
