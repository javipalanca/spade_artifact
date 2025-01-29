#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `spade_artifact` presence."""
import asyncio
from unittest.mock import Mock

from slixmpp.stanza import Presence, Iq
from slixmpp import JID
import pytest
import slixmpp.roster
from spade.presence import ContactNotFound, PresenceShow, PresenceType, Contact
from spade.presence import ContactNotFound

from tests.factories import MockedConnectedArtifactFactory

@pytest.mark.asyncio
async def test_set_available():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()

    await artifact.start(auto_register=False)
    artifact.mock_presence()
    artifact.presence.set_available()
    assert artifact.presence.is_available() is True
    await artifact.stop()


@pytest.mark.asyncio
async def test_set_available_with_show():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()

    await artifact.start(auto_register=False)
    artifact.mock_presence()
    artifact.presence.set_presence(PresenceType.AVAILABLE, show=PresenceShow.CHAT)
    assert artifact.presence.is_available()
    assert artifact.presence.get_show() == PresenceShow.CHAT
    await artifact.stop()


@pytest.mark.asyncio
async def test_set_unavailable():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()

    await artifact.start(auto_register=False)
    artifact.mock_presence()
    artifact.presence.set_unavailable()
    assert not artifact.presence.is_available()
    await artifact.stop()


@pytest.mark.asyncio
async def test_get_state_show():
    artifact = MockedConnectedArtifactFactory(available=True, show=PresenceShow.AWAY)
    artifact.loop = asyncio.get_running_loop()

    await artifact.start(auto_register=False)
    artifact.mock_presence()
    assert artifact.presence.get_show() == PresenceShow.AWAY
    await artifact.stop()


@pytest.mark.asyncio
async def test_get_status_empty():
    artifact = MockedConnectedArtifactFactory(status={})
    artifact.loop = asyncio.get_running_loop()

    await artifact.start(auto_register=False)
    artifact.mock_presence()
    assert artifact.presence.get_status( ) == {}
    await artifact.stop()


@pytest.mark.asyncio
async def test_get_status_string():
    artifact = MockedConnectedArtifactFactory(status={None: "Working"})
    artifact.loop = asyncio.get_running_loop()

    await artifact.start(auto_register=False)
    artifact.mock_presence()
    assert artifact.presence.get_status() == {None: "Working"}
    await artifact.stop()


@pytest.mark.asyncio
async def test_get_status_dict():
    artifact = MockedConnectedArtifactFactory(status={"en": "Working"})
    artifact.loop = asyncio.get_running_loop()

    await artifact.start(auto_register=False)
    artifact.mock_presence()
    assert artifact.presence.get_status() == {"en": "Working"}
    await artifact.stop()


@pytest.mark.asyncio
async def test_get_priority_default():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)
    artifact.mock_presence()

    assert artifact.presence.get_priority() == 0
    await artifact.stop()


@pytest.mark.asyncio
async def test_get_priority():
    artifact = MockedConnectedArtifactFactory(priority=10)
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)
    artifact.mock_presence()

    assert artifact.presence.get_priority() == 10
    await artifact.stop()


@pytest.mark.asyncio
async def test_set_presence_available():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)
    artifact.presence.set_available()

    assert artifact.presence.is_available()
    await artifact.stop()


@pytest.mark.asyncio
async def test_set_presence_unavailable():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)
    artifact.presence.set_unavailable()

    assert not artifact.presence.is_available()
    await artifact.stop()


@pytest.mark.asyncio
async def test_set_presence_status():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)
    artifact.presence.set_presence(status="Lunch")

    assert artifact.presence.get_status() == "Lunch"
    await artifact.stop()


@pytest.mark.asyncio
async def test_set_presence_status_dict():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)
    artifact.presence.set_presence(status={"en": "Lunch"})

    assert artifact.presence.get_status() == {"en": "Lunch"}
    await artifact.stop()


@pytest.mark.asyncio
async def test_set_presence_priority():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)
    artifact.presence.set_presence(priority=5)

    assert artifact.presence.get_priority() == 5
    await artifact.stop()


@pytest.mark.asyncio
async def test_set_presence():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)
    artifact.presence.set_presence(
        show= PresenceShow.AWAY,
        status="Lunch",
        priority=2
    )

    assert artifact.presence.is_available()
    assert artifact.presence.get_show()== PresenceShow.AWAY
    assert artifact.presence.get_status() == "Lunch"
    assert artifact.presence.get_priority() == 2
    await artifact.stop()


@pytest.mark.asyncio
async def test_get_contacts_empty():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)
    assert artifact.presence.get_contacts() == {}
    await artifact.stop()


@pytest.mark.asyncio
async def test_get_contacts(jid: JID, iq: Iq):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)

    artifact.presence.handle_roster_update(iq)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare
    assert bare_jid in contacts
    assert type(contacts[bare_jid]) == Contact
    assert contacts[bare_jid].name == "My Friend"
    assert contacts[bare_jid].subscription == "both"
    assert contacts[bare_jid].groups == ["Friends"]
    assert contacts[bare_jid].ask == "none"
    assert hasattr(contacts[bare_jid], "resources")
    assert isinstance(contacts[bare_jid].resources, dict)

    await artifact.stop()


@pytest.mark.asyncio
async def test_get_contacts_with_update(jid: JID, iq: Iq):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)

    artifact.presence.handle_roster_update(iq)

    stanza = Presence()
    stanza["from"] = jid
    stanza.set_show(PresenceShow.CHAT.value)
    stanza["status"] = "Just Chatting"
    stanza.set_priority(2)

    artifact.presence.handle_presence(stanza)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare
    assert bare_jid in contacts
    assert type(contacts[bare_jid]) == Contact
    assert contacts[bare_jid].name == "My Friend"
    assert contacts[bare_jid].subscription == "both"
    assert contacts[bare_jid].groups == ["Friends"]
    assert contacts[bare_jid].ask == "none"
    assert hasattr(contacts[bare_jid], "resources")
    assert isinstance(contacts[bare_jid].resources, dict)
    assert contacts[bare_jid].resources[jid.resource].type == PresenceType.AVAILABLE
    assert contacts[bare_jid].resources[jid.resource].show == PresenceShow.CHAT
    assert contacts[bare_jid].resources[jid.resource].status == "Just Chatting"
    assert contacts[bare_jid].resources[jid.resource].priority == 2
    await artifact.stop()



@pytest.mark.asyncio
async def test_get_contacts_with_update_unavailable(jid: JID, iq: Iq):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)

    artifact.presence.handle_roster_update(iq)

    stanza = Presence()
    stanza["from"] = jid
    stanza.set_type(PresenceType.UNAVAILABLE.value)

    artifact.presence.handle_presence(stanza)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare
    assert bare_jid in contacts
    assert type(contacts[bare_jid]) == Contact
    assert contacts[bare_jid].name == "My Friend"
    assert contacts[bare_jid].subscription == "both"
    assert contacts[bare_jid].groups == ["Friends"]
    assert contacts[bare_jid].ask == "none"
    assert hasattr(contacts[bare_jid], "resources")
    assert isinstance(contacts[bare_jid].resources, dict)
    assert contacts[bare_jid].resources[jid.resource].type == PresenceType.UNAVAILABLE
    assert contacts[bare_jid].resources[jid.resource].show == PresenceShow.NONE
    assert contacts[bare_jid].resources[jid.resource].status is None
    assert contacts[bare_jid].resources[jid.resource].priority == 0
    await artifact.stop()

@pytest.mark.asyncio
async def test_get_contact(jid: JID, iq: Iq):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()

    await artifact.start(auto_register=False)

    artifact.presence.handle_roster_update(iq)
    contact = artifact.presence.get_contact(jid)

    assert type(contact) == Contact
    assert contact.name == "My Friend"
    assert contact.subscription == "both"
    assert len(contact.groups) == 1
    assert contact.ask == "none"
    assert hasattr(contact, "resources")
    assert isinstance(contact.resources, dict)

    await artifact.stop()

@pytest.mark.asyncio
async def test_get_invalid_jid_contact():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)

    with pytest.raises(ContactNotFound):
        artifact.presence.get_contact(JID("invalid@contact"))
    await artifact.stop()


@pytest.mark.asyncio
async def test_get_invalid_str_contact():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    await artifact.start(auto_register=False)

    with pytest.raises(ContactNotFound):
        artifact.presence.get_contact("invalid@contact")
    await artifact.stop()


@pytest.mark.asyncio
async def test_subscribe(
 jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    try:
        await artifact.start(auto_register=False)
        artifact.client.send_presence = Mock()
        artifact.presence.subscribe(jid)

        assert artifact.client.send_presence.mock_calls
        arg = artifact.client.send_presence.call_args[1]

        assert arg["pto"] == jid
        assert arg["ptype"] == "subscribe"
    finally:
        await artifact.stop()


@pytest.mark.asyncio
async def test_unsubscribe(
 jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    try:
        await artifact.start(auto_register=False)
        artifact.client.send_presence = Mock()
        artifact.presence.unsubscribe(jid)

        assert artifact.client.send_presence.mock_calls
        arg = artifact.client.send_presence.call_args[1]

        assert arg["pto"] == jid
        assert arg["ptype"] == "unsubscribe"
    finally:
        await artifact.stop()


@pytest.mark.asyncio
async def test_approve(
 jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    try:
        await artifact.start(auto_register=False)
        artifact.client.send_presence = Mock()
        artifact.presence.approve_subscription(jid)

        assert artifact.client.send_presence.mock_calls
        arg = artifact.client.send_presence.call_args[1]

        assert arg["pto"] == jid
        assert arg["ptype"] == "subscribed"
    finally:
        await artifact.stop()


@pytest.mark.asyncio
async def test_on_available( jid):
    import logging
    log = logging.getLogger("xmlstream")
    log.setLevel(logging.DEBUG)
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    try:
        await artifact.start(auto_register=False)
        artifact.presence.on_available = Mock()

        stanza = Presence()
        stanza["from"] = jid
        stanza["type"] = PresenceType.AVAILABLE

        artifact.client.event("presence_available", stanza)

        assert artifact.presence.on_available.mock_calls

        assert len(artifact.presence.on_available.mock_calls) == 2
        jid_arg = artifact.presence.on_available.call_args[0][0]
        presence_info = artifact.presence.on_available.call_args[0][1]
        last_presence = artifact.presence.on_available.call_args[0][2]

        assert jid_arg == jid
        assert presence_info.type == PresenceType.AVAILABLE
        assert last_presence is None
    finally:
        await artifact.stop()


@pytest.mark.asyncio
async def test_on_unavailable(
 jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    try:
        await artifact.start(auto_register=False)
        artifact.presence.on_unavailable = Mock()

        stanza = Presence()
        stanza["from"] = jid
        stanza["type"] = "unavailable"

        artifact.client.event("presence_unavailable", stanza)

        assert artifact.presence.on_unavailable.mock_calls

        jid_arg = artifact.presence.on_unavailable.call_args[0][0]
        presence_info = artifact.presence.on_unavailable.call_args[0][1]
        last_presence = artifact.presence.on_unavailable.call_args[0][2]

        assert jid_arg == jid
        assert presence_info.type == PresenceType.UNAVAILABLE
        assert last_presence is None

    finally:
            await artifact.stop()


@pytest.mark.asyncio
async def test_on_subscribe(
 jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    try:
        await artifact.start(auto_register=False)
        artifact.presence.on_subscribe = Mock()

        stanza = Presence()
        stanza["from"] = jid
        stanza["type"] = PresenceType.SUBSCRIBE.value

        artifact.client.event("presence_subscribe", stanza)

        assert artifact.presence.on_subscribe.mock_calls

        jid_arg = artifact.presence.on_subscribe.call_args[0][0]

        assert jid_arg == jid.bare

    finally:
        await artifact.stop()



@pytest.mark.asyncio
async def test_on_unsubscribe(
 jid):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    try:
        await artifact.start(auto_register=False)
        artifact.presence.on_unsubscribe = Mock()

        stanza = Presence()
        stanza["from"] = jid
        stanza["type"] = PresenceType.UNSUBSCRIBE.value

        artifact.client.event("presence_unsubscribe", stanza)

        assert artifact.presence.on_unsubscribe.mock_calls

        jid_arg = artifact.presence.on_unsubscribe.call_args[0][0]

        assert jid_arg == jid.bare
    finally:
        await artifact.stop()


@pytest.mark.asyncio
async def test_ignore_self_presence():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()


    try:
        await artifact.start(auto_register=False)
        jid_ = artifact.jid

        stanza = Presence()
        stanza["from"] = jid_
        stanza["type"] = PresenceType.AVAILABLE.value
        stanza["show"] = PresenceShow.CHAT.value

        artifact.client.event("presence_available", stanza)

        with pytest.raises(ContactNotFound):
            artifact.presence.get_contact(jid_)
    finally:
        await artifact.stop()
