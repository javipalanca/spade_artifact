import pytest
from slixmpp import JID, Iq
from tests.factories import MockedConnectedArtifactAgentFactory


@pytest.fixture
def jid():
    return JID("friend@localhost/home")


@pytest.fixture
async def agent():
    agent = MockedConnectedArtifactAgentFactory()
    await agent.start()
    return agent


@pytest.fixture
def iq():
    iq = Iq()
    iq['type'] = 'result'
    iq['id'] = '123'
    iq["to"] = "friend@localhost/home"
    iq['from'] = 'localhost'
    #set namespace to roster
    iq['roster']['xmlns'] = 'jabber:iq:roster'
    iq['type'] = 'result'
    iq['roster']['items'] = {
        'friend@localhost': {
            'name': 'My Friend',
            'subscription': 'both',
            'groups': ['Friends']
        },
        'friend2@localhost': {
            'name': 'User Two',
            'subscription': 'to',
            'groups': ['Work']
        }
    }
    return iq
