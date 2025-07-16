import asyncio
import random
import getpass
import spade
from loguru import logger
from spade.agent import Agent

import spade_artifact
from spade_artifact import ArtifactMixin


class RandomGeneratorArtifact(spade_artifact.Artifact):
    def on_available(self, jid, stanza):
        logger.success(
            "[{}] Agent {} is available.".format(self.name, jid.split("@")[0])
        )

    def on_subscribed(self, jid):
        logger.success(
            "[{}] Agent {} has accepted the subscription.".format(
                self.name, jid.split("@")[0]
            )
        )
        logger.success(
            "[{}] Contacts List: {}".format(self.name, self.presence.get_contacts())
        )

    def on_subscribe(self, jid):
        logger.success(
            "[{}] Agent {} asked for subscription. Let's aprove it.".format(
                self.name, jid.split("@")[0]
            )
        )
        self.presence.approve(jid)
        self.presence.subscribe(jid)

    async def setup(self):
        # Approve all contact requests
        self.presence.set_available()
        self.presence.on_subscribe = self.on_subscribe
        self.presence.on_subscribed = self.on_subscribed
        self.presence.on_available = self.on_available

    async def run(self):

        while True:
            # Publish only if my friends are online
            if len(self.presence.get_contacts()) >= 1:
                random_num = random.randint(0, 100)
                await self.publish(f"{random_num}")
                logger.info(f"Publishing {random_num}")
            await asyncio.sleep(1)


class ConsumerAgent(ArtifactMixin, Agent):
    def __init__(self, *args, artifact_jid: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.artifact_jid = artifact_jid

    def artifact_callback(self, artifact, payload):
        logger.info(f"Received: [{artifact}] -> {payload}")

    async def setup(self):
        await asyncio.sleep(2)
        self.presence.approve_all = True
        self.presence.subscribe(self.artifact_jid)
        self.presence.set_available()
        await self.artifacts.focus(self.artifact_jid, self.artifact_callback)
        logger.info("Agent ready")


async def main():

        XMPP_SERVER = input("XMPP Server> ")
        artifact_jid = f"{input('Artifact name> ')}@{XMPP_SERVER}"
        artifact_passwd = getpass.getpass()

        agent_jid = f"{input('Agent name> ')}@{XMPP_SERVER}"
        agent_passwd = getpass.getpass()

        artifact = RandomGeneratorArtifact(artifact_jid, artifact_passwd)
        await artifact.start()

        agent = ConsumerAgent(jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid)
        await agent.start()

        await artifact.join()

        await artifact.stop()
        await agent.stop()

if __name__ == "__main__":
    spade.run(main())
