import factory
from unittest.mock import AsyncMock, Mock
from spade.presence import PresenceShow
from spade.agent import Agent
from spade_artifact import Artifact, ArtifactMixin


class MockedConnectedArtifact(Artifact):
    def __init__(
        self, available=None, show=PresenceShow.NONE, status=None, priority=0, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        if status is None:
            status = {}
        self._async_connect = AsyncMock()
        self._async_register = AsyncMock()

        self.client = Mock()
        self.client.send = Mock()

        self.available = available
        self.show = show
        self.status = status
        self.priority = priority

    async def _hook_plugin_after_connection(self, *args, **kwargs):
        """Mock pubsub after connection como en la versión anterior"""
        await super()._hook_plugin_after_connection(*args, **kwargs)

        if not hasattr(self.client, 'send'):
            self.client.send = AsyncMock()

        self.pubsub = Mock()
        self.pubsub.create = AsyncMock()

    def mock_presence(self):
        show = self.show if self.show is not None else PresenceShow.NONE
        status = self.status if self.status is not None else ""
        priority = self.priority if self.priority is not None else 0
        self.presence.set_presence(show=show, status=status, priority=priority)

    async def run(self):
        self.set("test_passed", True)
        self.kill()

    async def start(self, auto_register=True):
        """Override start to ensure proper event loop handling"""
        try:
            return await self._async_start(auto_register=auto_register)
        except Exception as e:
            self.kill()
            raise e


class MockedConnectedArtifactFactory(factory.Factory):
    class Meta:
        model = MockedConnectedArtifact

    jid = "fake@jid"
    password = "fake_password"
    available = None
    show = PresenceShow.NONE
    status = None
    priority = 0


class MockedConnectedArtifactAgent(ArtifactMixin, Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._async_connect = AsyncMock()
        self._async_register = AsyncMock()

    async def _hook_plugin_after_connection(self, *args, **kwargs):
        await super()._hook_plugin_after_connection(*args, **kwargs)
        self.pubsub = Mock()
        self.pubsub.subscribe = AsyncMock()
        self.pubsub.unsubscribe = AsyncMock()


class MockedConnectedArtifactAgentFactory(factory.Factory):
    class Meta:
        model = MockedConnectedArtifactAgent

    jid = "jid@fakeserver"
    password = "fake_password"
