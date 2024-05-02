import asyncio
import getpass
import random

from loguru import logger

from spade_artifact import Artifact


class PublisherArtifact(Artifact):
    async def setup(self):
        self.presence.set_available()
        await asyncio.sleep(2)

    async def run(self):
        while True:
            if self.presence.is_available():
                random_number = random.randint(1, 100)
                await self.publish(str(random_number))
            await asyncio.sleep(5)


class SubscriberArtifact(Artifact):
    def __init__(self, jid, password, publisher_jid, **kwargs):
        super().__init__(jid, password, **kwargs)
        self.publisher_jid = publisher_jid

    def artifact_callback(self, artifact, payload):
        logger.info(f"Received: [{artifact}] -> {payload}")

    async def setup(self):
        self.presence.set_available()
        await asyncio.sleep(2)
        await self.link(self.publisher_jid, self.artifact_callback)

async def main():
    XMPP_SERVER = input("XMPP Server> ")
    publisher_jid = f"{input('Artifact name> ')}@{XMPP_SERVER}"
    publisher_passwd = getpass.getpass()
    publisher = PublisherArtifact(publisher_jid, publisher_passwd)

    subscriber_jid = f"{input('Artifact name> ')}@{XMPP_SERVER}"
    subscriber_passwd = getpass.getpass()
    subscriber = SubscriberArtifact(subscriber_jid, subscriber_passwd, publisher_jid=publisher_jid)

    await publisher.start()
    await subscriber.start()
    await publisher.join()


    await publisher.stop()
    await subscriber.stop()


if __name__ == "__main__":
    asyncio.run(main())
