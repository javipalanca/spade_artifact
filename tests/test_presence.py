#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `spade_artifact` presence."""
import asyncio
from unittest.mock import Mock, MagicMock

import pytest
import spade.presence
from slixmpp import JID
from slixmpp.stanza import Iq
from slixmpp.stanza.roster import Roster
from spade.presence import PresenceShow, PresenceType, Presence
from spade.presence import ContactNotFound, Contact

from .factories import MockedConnectedArtifactFactory


async def test_set_available():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.mock_presence()

    artifact.presence.set_available()
    assert artifact.presence.is_available()


async def test_set_available_with_show():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.mock_presence()

    artifact.presence.set_available()
    assert artifact.presence.is_available()
    assert artifact.presence.current_presence.show == PresenceShow.CHAT


async def test_set_unavailable():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.presence.set_unavailable()

    assert not artifact.presence.is_available()


async def test_get_state_show():
    artifact = MockedConnectedArtifactFactory(available=True, show=PresenceShow.AWAY)
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.mock_presence()

    assert artifact.presence.current_presence.show == PresenceShow.AWAY


async def test_get_status_empty():
    artifact = MockedConnectedArtifactFactory(status="")
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.mock_presence()

    assert artifact.presence.current_presence.status == ""


async def test_get_status_string():
    artifact = MockedConnectedArtifactFactory(status="Working")
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.mock_presence()

    assert artifact.presence.current_presence.status == "Working"


async def test_get_status_dict():
    artifact = MockedConnectedArtifactFactory(status="Working")
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.mock_presence()

    assert artifact.presence.current_presence.status == "Working"


async def test_get_priority_default():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.mock_presence()

    assert artifact.presence.current_presence.priority == 0


async def test_get_priority():
    artifact = MockedConnectedArtifactFactory(priority=10)
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.mock_presence()

    assert artifact.presence.current_presence.priority == 10


async def test_set_presence_status():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.presence.set_presence(status="Lunch")

    assert artifact.presence.current_presence.status == "Lunch"


async def test_set_presence_priority():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.presence.set_presence(priority=5)

    assert artifact.presence.current_presence.priority == 5


async def test_set_presence():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.presence.set_presence(
        show=PresenceShow.NONE, status="Lunch", priority=2
    )

    assert artifact.presence.current_presence.is_available()
    assert artifact.presence.current_presence.show == PresenceShow.NONE
    assert artifact.presence.current_presence.status == "Lunch"
    assert artifact.presence.current_presence.priority == 2


async def test_get_contacts_empty():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    assert artifact.presence.get_contacts() == {}


async def test_get_contacts(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    iq = Iq()
    roster = Roster()
    roster.set_items({
        jid.bare: {
            "name": "My Friend",
            "subscription": "both"
        }
    })
    iq.set_payload(roster)

    artifact.presence.handle_roster_update(iq)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare
    assert bare_jid in contacts
    assert type(contacts[bare_jid]) is spade.presence.Contact
    assert contacts[bare_jid].name == "My Friend"
    assert contacts[bare_jid].subscription == "both"
    assert contacts[bare_jid].ask is 'none'
    assert contacts[bare_jid].groups == []


async def test_get_contacts_with_presence(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    iq = Iq()
    roster = Roster()
    roster.set_items({
        jid.bare: {
            "name": "My Available Friend",
            "subscription": "both"
        }
    })
    iq.set_payload(roster)

    artifact.presence.handle_roster_update(iq)

    presence = Presence()
    presence['from'] = jid
    presence.set_type('available')

    artifact.presence.handle_presence(presence)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare
    assert bare_jid in contacts
    assert contacts[bare_jid].name == "My Available Friend"

    assert contacts[bare_jid].current_presence.type == PresenceType.AVAILABLE


async def test_get_contacts_with_presence_on_and_off(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    iq = Iq()
    roster = Roster()
    roster.set_items({
        jid.bare: {
            "name": "My Friend",
            "subscription": "both"
        }
    })
    iq.set_payload(roster)

    artifact.presence.handle_roster_update(iq)

    presence = Presence()
    presence['from'] = jid
    presence.set_type('available')

    artifact.presence.handle_presence(presence)
    presence.set_type('unavailable')
    artifact.presence.handle_presence(presence)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare
    assert bare_jid in contacts
    assert contacts[bare_jid].name == "My Friend"

    assert contacts[bare_jid].current_presence.type == PresenceType.UNAVAILABLE


async def test_get_contacts_with_presence_unavailable(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    iq = Iq()
    roster = Roster()
    roster.set_items({
        jid.bare: {
            "name": "My UnAvailable Friend",
            "subscription": "both"
        }
    })
    iq.set_payload(roster)

    artifact.presence.handle_roster_update(iq)

    presence = Presence()
    presence['from'] = jid
    presence.set_type('unavailable')

    artifact.presence.handle_presence(presence)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare
    assert bare_jid in contacts
    assert contacts[bare_jid].name == "My UnAvailable Friend"
    assert contacts[bare_jid].current_presence.type == PresenceType.UNAVAILABLE


async def test_get_contact(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    iq = Iq()
    roster = Roster()
    roster.set_items({
        jid.bare: {
            "name": "My Friend",
            "subscription": "both"
        }
    })
    iq.set_payload(roster)

    artifact.presence.handle_roster_update(iq)

    contact = artifact.presence.get_contact(jid)

    assert type(contact) is spade.presence.Contact
    assert contact.name == "My Friend"
    assert contact.subscription == "both"
    assert contact.is_subscribed()
    assert contact.ask is 'none'
    assert contact.groups == []


async def test_get_invalid_jid_contact():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    with pytest.raises(ContactNotFound):
        artifact.presence.get_contact(JID("invalid@contact"))


async def test_get_invalid_str_contact():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    with pytest.raises(ContactNotFound):
        artifact.presence.get_contact("invalid@contact")


async def test_subscribe(jid):
    peer_jid = str(jid)
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.client = MagicMock()

    artifact.presence.subscribe(peer_jid)

    artifact.client.send_presence.assert_called_with(pto=peer_jid, ptype="subscribe")
    assert "friend@localhost/home" in artifact.presence.contacts
    assert artifact.presence.contacts["friend@localhost/home"].subscription == "to"
    assert artifact.presence.contacts["friend@localhost/home"].ask == "subscribe"
    assert artifact.presence.contacts["friend@localhost/home"].name == peer_jid


async def test_unsubscribe(jid):
    peer_jid = str(jid)
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.client = MagicMock()

    artifact.presence.contacts[peer_jid] = Contact(
        jid=JID(peer_jid), name=peer_jid, subscription="both", ask="", groups=[]
    )

    artifact.presence.unsubscribe(peer_jid)

    artifact.client.send_presence.assert_called_with(pto=peer_jid, ptype="unsubscribe")
    assert "friend@localhost/home" in artifact.presence.contacts
    assert artifact.presence.contacts["friend@localhost/home"].subscription == "from"
    assert artifact.presence.contacts["friend@localhost/home"].ask == ""
    assert artifact.presence.contacts["friend@localhost/home"].name == peer_jid


async def test_approve(jid):
    peer_jid = str(jid)
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.client = MagicMock()

    artifact.presence.contacts[peer_jid] = Contact(
        jid=JID(peer_jid), name=peer_jid, subscription="none", ask="", groups=[]
    )

    artifact.presence.approve_subscription(peer_jid)

    artifact.client.send_presence.assert_called_with(pto=peer_jid, ptype="subscribed")
    assert "friend@localhost/home" in artifact.presence.contacts
    assert artifact.presence.contacts["friend@localhost/home"].subscription == "from"
    assert artifact.presence.contacts["friend@localhost/home"].ask == ""
    assert artifact.presence.contacts["friend@localhost/home"].name == peer_jid


async def test_on_available(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    presence = Presence()
    presence['from'] = jid
    presence.set_type('available')

    artifact.presence.on_available = Mock()

    artifact.presence.handle_presence(presence)

    jid_arg, presence_arg, last_pres_arg = artifact.presence.on_available.call_args[0]

    assert jid_arg == str(jid)
    assert presence_arg.type == PresenceType.AVAILABLE


async def test_on_unavailable(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    presence = Presence()
    presence['from'] = jid
    presence.set_type('unavailable')

    artifact.presence.on_unavailable = Mock()

    artifact.presence.handle_presence(presence)

    jid_arg, presence_arg, last_pres_arg = artifact.presence.on_unavailable.call_args[0]

    assert jid_arg == str(jid)
    assert presence_arg.type == PresenceType.UNAVAILABLE


async def test_on_subscribe(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    presence = Presence()
    presence['from'] = jid
    presence.set_type(PresenceType.SUBSCRIBE.value)

    artifact.presence.on_subscribe = Mock()

    artifact.presence.handle_subscription(presence)

    jid_arg = artifact.presence.on_subscribe.call_args[0][0]

    assert jid_arg == jid.bare


async def test_on_subscribe_approve_all(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.presence.approve_all = True
    artifact.client = MagicMock()

    presence = Presence()
    presence['from'] = jid
    presence.set_type(PresenceType.SUBSCRIBE.value)

    artifact.presence.handle_subscription(presence)

    assert artifact.client.send_presence.called
    artifact.client.send_presence.assert_called_with(pto=jid.bare, ptype=PresenceType.SUBSCRIBED.value)


async def test_on_subscribed(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    presence = Presence()
    presence['from'] = jid
    presence.set_type(PresenceType.SUBSCRIBED.value)

    artifact.presence.contacts[jid.bare] = Contact(
        jid=jid.bare, name=jid.bare, subscription="none", ask="subscribe", groups=[]
    )

    artifact.presence.handle_subscription(presence)

    assert len(artifact.presence.contacts) == 1
    assert jid.bare in artifact.presence.contacts
    stored_contact = artifact.presence.contacts[jid.bare]
    assert stored_contact.jid == jid.bare
    assert stored_contact.name == jid.bare
    assert stored_contact.subscription == "to"
    assert stored_contact.ask == ""
    assert stored_contact.groups == []


async def test_on_unsubscribe(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    artifact.presence.on_unsubscribe = Mock()

    presence = Presence()
    presence['from'] = jid
    presence.set_type(PresenceType.UNSUBSCRIBE.value)

    artifact.presence.handle_subscription(presence)

    jid_arg = artifact.presence.on_unsubscribe.call_args[0][0]

    assert jid_arg == jid.bare


async def test_on_unsubscribed(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    presence = Presence()
    presence['from'] = jid
    presence.set_type(PresenceType.UNSUBSCRIBED.value)

    artifact.presence.contacts[jid.bare] = Contact(
        jid=jid.bare, name=jid.bare, subscription="both", ask="none", groups=[]
    )

    artifact.presence.handle_subscription(presence)

    assert len(artifact.presence.contacts) == 1
    assert jid.bare in artifact.presence.contacts
    stored_contact = artifact.presence.contacts[jid.bare]
    assert stored_contact.jid == jid.bare
    assert stored_contact.name == jid.bare
    assert stored_contact.subscription == "to"
    assert stored_contact.ask == ""
    assert stored_contact.groups == []


async def test_on_changed(jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    iq = Iq()
    roster = Roster()
    roster.set_items({
        jid.bare: {
            "name": "My Friend",
            "subscription": "both"
        }
    })
    iq.set_payload(roster)

    artifact.presence.handle_roster_update(iq)

    presence = Presence()
    presence['from'] = jid
    presence.set_type(PresenceType.AVAILABLE.value)
    presence.set_show(PresenceShow.CHAT.value)

    artifact.presence.handle_presence(presence)

    contact = artifact.presence.get_contact(jid)
    assert contact.name == "My Friend"
    assert contact.current_presence.show == PresenceShow.CHAT

    presence.set_show(PresenceShow.AWAY.value)

    artifact.presence.handle_presence(presence)

    contact = artifact.presence.get_contact(jid)

    assert contact.name == "My Friend"
    assert contact.current_presence.show == PresenceShow.AWAY
    assert contact.last_presence.show == PresenceShow.CHAT


async def test_ignore_self_presence():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start(auto_register=False)

    jid = artifact.jid

    presence = Presence()
    presence['from'] = jid
    presence.set_type(PresenceType.AVAILABLE.value)
    presence.set_show(PresenceShow.CHAT.value)

    artifact.presence.handle_presence(presence)

    with pytest.raises(ContactNotFound):
        artifact.presence.get_contact(jid)

    assert len(artifact.presence.get_contacts()) == 0