=====
Usage
=====


.. note:: This is a plugin for the `SPADE <https://github.com/javipalanca/spade>`_ agent platform. Please visit the
          `SPADE's documentation <https://spade-mas.readthedocs.io>`_ to know more about this platform.

To use spade-artifact in a project you can follow the next example, which implements an artifact that periodically emits
random numbers only if any contact is online::

    import random
    import spade_artifact

    XMPP_SERVER = "REPLACE_THIS_WITH_YOUR_XMPP_SERVER"

    class RandomGeneratorArtifact(spade_artifact.Artifact):

        async def setup(self):
            # Approve all contact requests
            self.presence.approve_all = True

            # Create PubSub node
            self.PUBSUB_JID = f"pubsub.{XMPP_SERVER}"
            await self.pubsub.create(self.PUBSUB_JID, "RANDOM_NUM_NODE")


        async def run(self):
            while True:
                # Publish only if my friends are online
                if len(self.presence.get_contacts()) >= 1:
                    random_num = random.randint(0,100)
                    await self.pubsub.publish(self.PUBSUB_JID, "RANDOM_NUM_NODE", f"{random_num}")
