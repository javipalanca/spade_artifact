import pytest
from aioxmpp import JID


@pytest.fixture
def jid():
    return JID.fromstr("friend@localhost/home")
