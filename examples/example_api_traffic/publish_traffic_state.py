import asyncio
import getpass
import json

from spade.agent import Agent
from spade_artifact.common.readers.apireader import APIReaderArtifact
from spade_artifact import ArtifactMixin
from loguru import logger



# Example data processor function that now returns processed data

async def traffic_data_processor(data):
    traffic_state_names = {
        0: "Fluido",
        1: "Denso",
        2: "Congestionado",
        3: "Cortado",
        4: "Sin datos",
        5: "Paso inferior fluido",
        6: "Paso inferior denso",
        7: "Paso inferior congestionado",
        8: "Paso inferior cortado",
        9: "Sin datos (paso inferior)"
    }

    records = data.get("records", [])

    filtered_records = [record for record in records if record['record']['fields']['estado'] not in [0, 5]]

    messages = []



    for record in filtered_records:

        estado_code = record['record']['fields']['estado']

        estado_descriptive = traffic_state_names.get(estado_code, "Estado desconocido")

        denominacion = record['record']['fields']['denominacion']

        message = f"Calle: {denominacion}, Estado: {estado_descriptive}"

        messages.append(message)



    return messages



class ConsumerAgent(ArtifactMixin, Agent):
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
    with open('config_traffic.json', 'r') as config_file:
        config = json.load(config_file)

    XMPP_SERVER = config["XMPP_SERVER"]
    artifact_name = config["artifact_name"]
    artifact_jid = f"{artifact_name}@{XMPP_SERVER}"
    artifact_passwd = getpass.getpass(prompt=f"Password for artifact {artifact_name}> ")

    agent_name = config["agent_name"]
    agent_jid = f"{agent_name}@{XMPP_SERVER}"
    agent_passwd = getpass.getpass(prompt=f"Password for Agent {agent_name}> ")

    api_url = config.get('api_url')

    artifact = APIReaderArtifact(artifact_jid, artifact_passwd, api_url, traffic_data_processor)
    await artifact.start()

    agent = ConsumerAgent(jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid)
    await agent.start()
    await artifact.join()
    await artifact.stop()
    await agent.stop()

    print("Agents and Artifacts have been stopped")



if __name__ == "__main__":
     asyncio.run(main())
