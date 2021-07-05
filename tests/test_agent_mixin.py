import collections

from asynctest import Mock
from spade.behaviour import OneShotBehaviour

from spade_artifact.agent import ArtifactComponent
from tests.factories import MockedConnectedArtifactAgentFactory


def test_pubsub_server_not_set():
    agent = MockedConnectedArtifactAgentFactory()
    assert agent.pubsub_server == "pubsub.fakeserver"


def test_custom_pubsub_server():
    agent = MockedConnectedArtifactAgentFactory(pubsub_server="custom.pubsub.server")
    assert agent.pubsub_server == "custom.pubsub.server"


def test_artifacts_component(agent):
    assert isinstance(agent.artifacts, ArtifactComponent)
    assert agent.artifacts.focus_callbacks == {}


def test_focus(agent):
    callback = Mock()

    class FocusBehaviour(OneShotBehaviour):
        async def run(self):
            await agent.artifacts.focus("artifact@server", callback)
            self.kill()

    behav = FocusBehaviour()
    agent.add_behaviour(behav)
    behav.join()
    agent.stop()
    agent.pubsub.subscribe.assert_called_with(agent.pubsub_server, "artifact@server")

    assert agent.artifacts.focus_callbacks["artifact@server"] == callback


def test_ignore(agent):
    callback = Mock()

    class FocusBehaviour(OneShotBehaviour):
        async def run(self):
            await agent.artifacts.focus("artifact@server", callback)
            await agent.artifacts.ignore("artifact@server")

    behav = FocusBehaviour()
    agent.add_behaviour(behav)
    behav.join()
    agent.stop()
    agent.pubsub.unsubscribe.assert_called_with(agent.pubsub_server, "artifact@server")

    assert "artifact@server" not in agent.artifacts.focus_callbacks


def test_set_on_item_published(agent):
    callback = Mock()

    class FocusBehaviour(OneShotBehaviour):
        async def run(self):
            await agent.artifacts.focus("artifact@server", callback)

    behav = FocusBehaviour()
    agent.add_behaviour(behav)
    behav.join()

    class Item:
        def __init__(self, data):
            self.data = data
            _data = collections.namedtuple("data", "data")
            self.registered_payload = _data(data=self.data)

    agent.artifacts.on_item_published(
        jid="artifact@server",
        node="artifact@server",
        item=Item("payload"),
        message=None,
    )

    assert callback.called_with("artifact@server", "payload")
    agent.stop()
