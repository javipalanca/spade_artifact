import factory
from spade.presence import PresenceShow, PresenceType
from spade.agent import Agent
import sys
if sys.version_info >= (3, 8):
    from unittest.mock import AsyncMock as CoroutineMock, Mock, AsyncMock
else:
    from asynctest import CoroutineMock, Mock, AsyncMock

from spade_artifact import Artifact, ArtifactMixin

class MockedConnectedArtifact(Artifact):
    def __init__(
        self, available=None, show=PresenceShow.NONE, status=None, priority=0, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        if status is None:
            status = {}
        self._async_connect = CoroutineMock()
        self._async_register = CoroutineMock()

        self.pubsub = Mock()
        self.pubsub.create = AsyncMock()
        self.pubsub.set_on_item_published = Mock()

        self.available = available
        self.show = show
        self.status = status
        self.priority = priority

    async def _hook_plugin_after_connection(self, *args, **kwargs):
        await super()._hook_plugin_after_connection(*args, **kwargs)

        pass

    def mock_presence(self):
        show = self.show if self.show is not None else PresenceShow.NONE
        self.presence.set_presence(PresenceType.AVAILABLE, show, self.status, self.priority)

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
        self._async_connect = CoroutineMock()
        self._async_register = CoroutineMock()
        self.stream = Mock()

    async def _hook_plugin_after_connection(self, *args, **kwargs):
        await super()._hook_plugin_after_connection(*args, **kwargs)
        self.pubsub = Mock()
        self.pubsub.subscribe = CoroutineMock()
        self.pubsub.unsubscribe = CoroutineMock()


class MockedConnectedArtifactAgentFactory(factory.Factory):
    class Meta:
        model = MockedConnectedArtifactAgent

    jid = "jid@fakeserver"
    password = "fake_password"
