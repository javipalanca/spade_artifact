import pytest
from slixmpp import JID
from tests.factories import MockedConnectedArtifactAgentFactory


@pytest.fixture
def jid():
    return JID("friend@localhost/home")


@pytest.fixture
async def agent():
    agent = MockedConnectedArtifactAgentFactory()
    await agent.start()
    return agent
