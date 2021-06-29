import asyncio
import random

from aioxmpp import XMPPCancelError
from loguru import logger

import spade_artifact


class RandomGeneratorArtifact(spade_artifact.Artifact):

    async def setup(self):
        # Approve all contact requests
        self.presence.approve_all = True

    async def run(self):

        while True:
            # Publish only if my friends are online
            if len(self.presence.get_contacts()) >= 1:
                random_num = random.randint(0, 100)
                await self.publish(f"{random_num}")
                logger.info(f"Publishing {random_num}")
            print(".", end="")
            await asyncio.sleep(1)


if __name__ == "__main__":
    XMPP_SERVER = "gtirouter.dsic.upv.es"  # input("XMPP Server>")
    artifact_jid = "a1"  # input("Artifact name> ")
    artifact_passwd = "secret"  # getpass.getpass()

    agent_jid = "ag1"  # input("Agent name> ")
    agent_passwd = "secret"  # getpass.getpass()

    artifact = RandomGeneratorArtifact(f"{artifact_jid}@{XMPP_SERVER}", artifact_passwd)

    artifact.start()
