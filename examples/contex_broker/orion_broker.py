import json
import asyncio
import getpass
import spade_artifact
from loguru import logger
from spade_artifact.common.readers.context_broker_inserter import InserterArtifact

class PublisherArtifact(spade_artifact.Artifact):
    def __init__(self, jid, passwd, payload):
        super().__init__(jid, passwd)
        self.payload = payload

    async def setup(self):
        self.presence.set_available()
        await asyncio.sleep(2)

    async def run(self):
        while True:
            if self.presence.is_available():
                payload_json = json.dumps(self.payload)
                logger.info(f"Publishing data: {payload_json}")
                await self.publish(str(payload_json))
            await asyncio.sleep(360)


async def main():
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)

    XMPP_SERVER = config["XMPP_SERVER"]
    publisher_name = config["publisher_artifact_name"]
    publisher_jid = f"{publisher_name}@{XMPP_SERVER}"
    publisher_passwd = getpass.getpass(prompt="Password for publisher artifact> ")

    with open('payload.json', 'r') as payload_file:
        payload = json.load(payload_file)

    with open('json_template.json', 'r') as json_template_file:
        json_template = json.load(json_template_file)

    publisher = PublisherArtifact(publisher_jid, publisher_passwd, payload)

    subscriber_name = config["subscriber_artifact_name"]
    subscriber_jid = f"{subscriber_name}@{XMPP_SERVER}"
    subscriber_passwd = getpass.getpass(prompt="Password for subscriber artifact> ")

    host = config["host"]
    project_name = config["project_name"]


    subscriber = InserterArtifact(subscriber_jid, subscriber_passwd, publisher_jid, host,
                                  project_name, json_template=json_template,columns_update=['location'])

    await publisher.start()
    await subscriber.start()

    await asyncio.gather(publisher.join(), subscriber.join())

    await publisher.stop()
    await subscriber.stop()

    print("Agents and Artifacts have been stopped")


if __name__ == "__main__":
    asyncio.run(main())
