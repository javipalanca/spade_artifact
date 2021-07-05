import factory
from aioxmpp import PresenceShow, PresenceState
from asynctest import CoroutineMock, Mock
from spade.agent import Agent

from spade_artifact import Artifact, ArtifactMixin


class MockedConnectedArtifact(Artifact):
    def __init__(
        self, available=None, show=None, status=None, priority=0, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        if status is None:
            status = {}
        self._async_connect = CoroutineMock()
        self._async_register = CoroutineMock()
        self.conn_coro = Mock()
        self.conn_coro.__aexit__ = CoroutineMock()

        self.available = available
        self.show = show
        self.status = status
        self.priority = priority

    async def _hook_plugin_after_connection(self, *args, **kwargs):
        await super()._hook_plugin_after_connection(*args, **kwargs)
        self.pubsub = Mock()
        self.pubsub.create = CoroutineMock()

    def mock_presence(self):
        show = self.show if self.show is not None else PresenceShow.NONE
        available = self.available if self.available is not None else False
        state = PresenceState(available, show)
        self.presence.presenceserver.set_presence(state, self.status, self.priority)

    async def run(self):
        self.set("test_passed", True)
        self.kill()


class MockedConnectedArtifactFactory(factory.Factory):
    class Meta:
        model = MockedConnectedArtifact

    jid = "fake@jid"
    password = "fake_password"
    available = None
    show = None
    status = {}
    priority = 0


class MockedConnectedArtifactAgent(ArtifactMixin, Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._async_connect = CoroutineMock()
        self._async_register = CoroutineMock()
        self.conn_coro = Mock()
        self.conn_coro.__aexit__ = CoroutineMock()
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
