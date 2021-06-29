import pytest
from aioxmpp import JID

from tests.factories import MockedConnectedArtifactAgentFactory


@pytest.fixture
def jid():
    return JID.fromstr("friend@localhost/home")


@pytest.fixture
def agent():
    agent = MockedConnectedArtifactAgentFactory()
    future = agent.start()
    future.result()
    return agent
