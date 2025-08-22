import collections
from unittest.mock import Mock
from xml.etree.ElementTree import Element

from slixmpp.stanza.message import Message as SlixmppMessage

from spade.behaviour import OneShotBehaviour
from spade_artifact.agent import ArtifactComponent
from .factories import MockedConnectedArtifactAgentFactory


def test_pubsub_server_not_set():
    agent = MockedConnectedArtifactAgentFactory()
    assert agent.pubsub_server == "pubsub.fakeserver"


def test_custom_pubsub_server():
    agent = MockedConnectedArtifactAgentFactory(pubsub_server="custom.pubsub.server")
    assert agent.pubsub_server == "custom.pubsub.server"


def test_artifacts_component(agent):
    assert isinstance(agent.artifacts, ArtifactComponent)
    assert agent.artifacts.focus_callbacks == {}


async def test_focus(agent):
    callback = Mock()

    class FocusBehaviour(OneShotBehaviour):
        async def run(self):
            await agent.artifacts.focus("artifact@server", callback)
            self.kill()

    behav = FocusBehaviour()
    agent.add_behaviour(behav)
    await behav.join()
    await agent.stop()
    agent.pubsub.subscribe.assert_called_with(agent.pubsub_server, "artifact@server")

    assert agent.artifacts.focus_callbacks["artifact@server"] == callback


async def test_ignore(agent):
    callback = Mock()

    class FocusBehaviour(OneShotBehaviour):
        async def run(self):
            await agent.artifacts.focus("artifact@server", callback)
            await agent.artifacts.ignore("artifact@server")

    behav = FocusBehaviour()
    agent.add_behaviour(behav)
    await behav.join()
    await agent.stop()
    agent.pubsub.unsubscribe.assert_called_with(agent.pubsub_server, "artifact@server")

    assert "artifact@server" not in agent.artifacts.focus_callbacks


async def test_set_on_item_published(agent):
    callback = Mock()

    class FocusBehaviour(OneShotBehaviour):
        async def run(self):
            await agent.artifacts.focus("artifact@server", callback)

    behav = FocusBehaviour()
    agent.add_behaviour(behav)
    await behav.join()

    class Item:
        def __init__(self, data):
            self.data = data
            _data = collections.namedtuple("data", "data")
            self.registered_payload = _data(data=self.data)

    msg = SlixmppMessage()
    msg['pubsub_event']['items']['node'] = "artifact@server"
    msg['pubsub_event']['items']['item']['publisher'] = "artifact@server"
    msg['pubsub_event']['items']['item']['payload'] = Element("{}",)
    msg['pubsub_event']['items']['item']['payload'].text = "payload"

    agent.artifacts.on_item_published(msg)

    callback.assert_called_with("artifact@server", "payload")
    await agent.stop()
