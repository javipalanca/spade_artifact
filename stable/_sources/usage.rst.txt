=====
Usage
=====


.. note:: This is a plugin for the `SPADE <https://github.com/javipalanca/spade>`_ agent platform. Please visit the
          `SPADE's documentation <https://spade-mas.readthedocs.io>`_ to know more about this platform.

To use spade-artifact in a project you can follow the next example, which implements an artifact that periodically emits
random numbers only if any contact is online::

    import asyncio
    import random
    import getpass

    from loguru import logger
    from spade.agent import Agent

    from spade_artifact import Artifact, ArtifactMixin


    class RandomGeneratorArtifact(Artifact):
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


    if __name__ == "__main__":
        XMPP_SERVER = input("XMPP Server>")
        artifact_jid = f"{input('Artifact name> ')}@{XMPP_SERVER}"
        artifact_passwd = getpass.getpass()

        agent_jid = f"{input('Agent name> ')}@{XMPP_SERVER}"
        agent_passwd = getpass.getpass()

        agent = ConsumerAgent(
            jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid
        )
        agent.start()

        artifact = RandomGeneratorArtifact(artifact_jid, artifact_passwd)

        future = artifact.start()
        future.result()

        artifact.join()


The example below shows the main features required to build an artifact and to interact with artifacts as an agent.
As shown, an artifact MUST implement its ``run`` coroutine where its main functionality is presented (some initial configuration can still be done from the ``setup`` coroutine).

An artifact can publish observations by means of the ``publish`` coroutine as shown in the example.

Also, an artifact can handle presence messages using the same API as a SPADE agent.

On the other hand, an agent can interact with artifacts just by inheriting from the ArtifactMixin class. It provides the necessary stuff to be able to focus on an artifact and receive its observations.
As in the example below, an agent can use the ``self.artifacts.focus`` coroutine to focus on an artifact. The parameters are the jid of the artifact and the callback method that will receive the observations.
This callback method will receive as arguments the jid of the artifact publishing the observation and the payload of the observation.

.. warning:: Remember that, when inheriting from Mixins, they MUST be always before the base class (``Agent``).
             E.g. ``class MyAgent(PubSubMixin, ArtifactMixin, Agent):``


If an agent wants to stop focusing on an artifact it can use the ``self.artifacts.ignore`` coroutine with the jid of the artifact.