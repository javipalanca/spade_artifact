import collections
from unittest.mock import MagicMock

import pytest
from tests.compat import Mock
from spade.behaviour import OneShotBehaviour
import asyncio
from slixmpp.stanza.message import Message as SlixmppMessage

from spade_artifact.agent import ArtifactComponent
from tests.factories import MockedConnectedArtifactAgentFactory

def test_pubsub_server_not_set():
    agent = MockedConnectedArtifactAgentFactory()
    assert agent.pubsub_server == "pubsub.fakeserver"

def test_custom_pubsub_server():
    agent = MockedConnectedArtifactAgentFactory(pubsub_server="custom.pubsub.server")
    assert agent.pubsub_server == "custom.pubsub.server"

@pytest.mark.asyncio
async def test_artifacts_component():
    agent = MockedConnectedArtifactAgentFactory()
    agent.loop = asyncio.get_running_loop()
    await agent.start()

    try:
        assert isinstance(agent.artifacts, ArtifactComponent)
        assert agent.artifacts.focus_callbacks == {}
    finally:
        await agent.stop()

@pytest.mark.asyncio
async def test_focus():
    agent = MockedConnectedArtifactAgentFactory()
    agent.loop = asyncio.get_running_loop()
    await agent.start()

    try:
        callback = Mock()

        class FocusBehaviour(OneShotBehaviour):
            async def run(self):
                await agent.artifacts.focus("artifact@server", callback)
                self.kill()

        behav = FocusBehaviour()
        agent.add_behaviour(behav)
        await behav.join()

        agent.pubsub.subscribe.assert_called_with(agent.pubsub_server, "artifact@server")
        assert agent.artifacts.focus_callbacks["artifact@server"] == callback
    finally:
        await agent.stop()

@pytest.mark.asyncio
async def test_ignore():
    agent = MockedConnectedArtifactAgentFactory()
    agent.loop = asyncio.get_running_loop()
    await agent.start()

    try:
        callback = Mock()

        class FocusBehaviour(OneShotBehaviour):
            async def run(self):
                await agent.artifacts.focus("artifact@server", callback)
                await agent.artifacts.ignore("artifact@server")
                self.kill()

        behav = FocusBehaviour()
        agent.add_behaviour(behav)
        await behav.join()

        agent.pubsub.unsubscribe.assert_called_with(agent.pubsub_server, "artifact@server")
        assert "artifact@server" not in agent.artifacts.focus_callbacks
    finally:
        await agent.stop()

@pytest.mark.asyncio
async def test_set_on_item_published():
    agent = MockedConnectedArtifactAgentFactory()
    agent.loop = asyncio.get_running_loop()
    await agent.start()

    try:
        callback = Mock()

        class FocusBehaviour(OneShotBehaviour):
            async def run(self):
                await agent.artifacts.focus("artifact@server", callback)
                self.kill()

        behav = FocusBehaviour()
        agent.add_behaviour(behav)
        await behav.join()

        msg = MagicMock(spec=SlixmppMessage)
        msg.__getitem__.side_effect = lambda key: {
            'pubsub_event': {
                'items': {
                    'node': "artifact@server",
                    'item': {
                        'payload': MagicMock(text="payload"),
                        'publisher': "artifact@server",
                    }
                }
            }
        }.get(key, MagicMock())

        agent.artifacts.on_item_published(msg)

        callback.assert_called_with("artifact@server", "payload")
    finally:
        await agent.stop()
