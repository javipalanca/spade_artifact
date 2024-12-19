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

    def on_item_published(self, jid, node, payload):
        """
        Handle published items from pubsub
        """

        if node in self.focus_callbacks:
            try:
                full_jid = f"{node}@{jid.split('.', 1)[1]}"
                self.focus_callbacks[node](full_jid, payload)
            except Exception as e:
                logger.error(f"Error in callback execution: {e}", exc_info=True)
        else:
            matching_keys = [k for k in self.focus_callbacks.keys() if k.startswith(node + '@')]
            for key in matching_keys:
                try:
                    self.focus_callbacks[key](key, payload)
                except Exception as e:
                    logger.error(f"Error in callback execution for {key}: {e}", exc_info=True)

    async def focus(self, artifact_jid, callback):
        """
        Focus on an artifact
        """
        node = artifact_jid.split('@')[0] if '@' in artifact_jid else artifact_jid

        await self.agent.pubsub.subscribe(self.agent.pubsub_server, node)
        self.focus_callbacks[node] = callback
        self.focus_callbacks[artifact_jid] = callback

    async def ignore(self, artifact_jid):
        node = artifact_jid.split('@')[0] if '@' in artifact_jid else artifact_jid

        await self.agent.pubsub.unsubscribe(self.agent.pubsub_server, node)

        if node in self.focus_callbacks:
            del self.focus_callbacks[node]
        if artifact_jid in self.focus_callbacks:
            del self.focus_callbacks[artifact_jid]
