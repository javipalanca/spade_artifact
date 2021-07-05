from loguru import logger
from spade_pubsub import PubSubMixin


class ArtifactMixin(PubSubMixin):
    def __init__(self, *args, pubsub_server=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pubsub_server = (
            pubsub_server if pubsub_server else f"pubsub.{self.jid.domain}"
        )

    async def _hook_plugin_after_connection(self, *args, **kwargs):
        try:
            await super()._hook_plugin_after_connection(*args, **kwargs)
        except AttributeError:
            logger.debug("_hook_plugin_after_connection is undefined")

        self.artifacts = ArtifactComponent(self)
        self.pubsub.set_on_item_published(self.artifacts.on_item_published)


class ArtifactComponent:
    def __init__(self, agent):
        self.agent = agent
        self.focus_callbacks = {}

    def on_item_published(self, jid, node, item, message=None):
        if node in self.focus_callbacks:
            self.focus_callbacks[node](node, item.registered_payload.data)

    async def focus(self, artifact_jid, callback):
        await self.agent.pubsub.subscribe(self.agent.pubsub_server, str(artifact_jid))
        self.focus_callbacks[artifact_jid] = callback

    async def ignore(self, artifact_jid):
        await self.agent.pubsub.unsubscribe(self.agent.pubsub_server, str(artifact_jid))
        if artifact_jid in self.focus_callbacks:
            del self.focus_callbacks[artifact_jid]
