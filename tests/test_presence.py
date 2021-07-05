#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `spade_artifact` presence."""

from unittest.mock import Mock

import pytest
from aioxmpp import PresenceShow, PresenceState, PresenceType, Presence, JID
from aioxmpp.roster.xso import Item as XSOItem
from spade.presence import ContactNotFound

from tests.factories import MockedConnectedArtifactFactory


def test_set_available():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()
    artifact.mock_presence()

    artifact.presence.set_available()
    assert artifact.presence.is_available()


def test_set_available_with_show():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()
    artifact.mock_presence()

    artifact.presence.set_available(show=PresenceShow.CHAT)
    assert artifact.presence.is_available()
    assert artifact.presence.state.show == PresenceShow.CHAT


def test_set_unavailable():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.set_unavailable()

    assert not artifact.presence.is_available()


def test_get_state_show():
    artifact = MockedConnectedArtifactFactory(available=True, show=PresenceShow.AWAY)

    future = artifact.start(auto_register=False)
    future.result()
    artifact.mock_presence()

    assert artifact.presence.state.show == PresenceShow.AWAY


def test_get_status_empty():
    artifact = MockedConnectedArtifactFactory(status={})

    future = artifact.start(auto_register=False)
    future.result()
    artifact.mock_presence()

    assert artifact.presence.status == {}


def test_get_status_string():
    artifact = MockedConnectedArtifactFactory(status="Working")

    future = artifact.start(auto_register=False)
    future.result()
    artifact.mock_presence()

    assert artifact.presence.status == {None: "Working"}


def test_get_status_dict():
    artifact = MockedConnectedArtifactFactory(status={"en": "Working"})

    future = artifact.start(auto_register=False)
    future.result()
    artifact.mock_presence()

    assert artifact.presence.status == {"en": "Working"}


def test_get_priority_default():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()
    artifact.mock_presence()

    assert artifact.presence.priority == 0


def test_get_priority():
    artifact = MockedConnectedArtifactFactory(priority=10)

    future = artifact.start(auto_register=False)
    future.result()
    artifact.mock_presence()

    assert artifact.presence.priority == 10


def test_set_presence_available():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.set_presence(state=PresenceState(available=True))

    assert artifact.presence.is_available()


def test_set_presence_unavailable():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.set_presence(state=PresenceState(available=False))

    assert not artifact.presence.is_available()


def test_set_presence_status():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.set_presence(status="Lunch")

    assert artifact.presence.status == {None: "Lunch"}


def test_set_presence_status_dict():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.set_presence(status={"en": "Lunch"})

    assert artifact.presence.status == {"en": "Lunch"}


def test_set_presence_priority():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.set_presence(priority=5)

    assert artifact.presence.priority == 5


def test_set_presence():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.set_presence(
        state=PresenceState(True, PresenceShow.PLAIN), status="Lunch", priority=2
    )

    assert artifact.presence.is_available()
    assert artifact.presence.state.show == PresenceShow.PLAIN
    assert artifact.presence.status == {None: "Lunch"}
    assert artifact.presence.priority == 2


def test_get_contacts_empty():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    assert artifact.presence.get_contacts() == {}


def test_get_contacts(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    item = XSOItem(jid=jid)
    item.approved = True
    item.name = "My Friend"

    artifact.presence.roster._update_entry(item)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare()
    assert bare_jid in contacts
    assert type(contacts[bare_jid]) == dict
    assert contacts[bare_jid]["approved"]
    assert contacts[bare_jid]["name"] == "My Friend"
    assert contacts[bare_jid]["subscription"] == "none"
    assert "ask" not in contacts[bare_jid]
    assert "groups" not in contacts[bare_jid]


def test_get_contacts_with_presence(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    item = XSOItem(jid=jid)
    item.approved = True
    item.name = "My Available Friend"

    artifact.presence.roster._update_entry(item)

    stanza = Presence(from_=jid, type_=PresenceType.AVAILABLE)
    artifact.presence.presenceclient.handle_presence(stanza)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare()
    assert bare_jid in contacts
    assert contacts[bare_jid]["name"] == "My Available Friend"

    assert contacts[bare_jid]["presence"].type_ == PresenceType.AVAILABLE


def test_get_contacts_with_presence_on_and_off(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    item = XSOItem(jid=jid)
    item.approved = True
    item.name = "My Friend"

    artifact.presence.roster._update_entry(item)

    stanza = Presence(from_=jid, type_=PresenceType.AVAILABLE)
    artifact.presence.presenceclient.handle_presence(stanza)
    stanza = Presence(from_=jid, type_=PresenceType.UNAVAILABLE)
    artifact.presence.presenceclient.handle_presence(stanza)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare()
    assert bare_jid in contacts
    assert contacts[bare_jid]["name"] == "My Friend"

    assert contacts[bare_jid]["presence"].type_ == PresenceType.UNAVAILABLE


def test_get_contacts_with_presence_unavailable(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    item = XSOItem(jid=jid)
    item.approved = True
    item.name = "My UnAvailable Friend"

    artifact.presence.roster._update_entry(item)

    stanza = Presence(from_=jid, type_=PresenceType.UNAVAILABLE)
    artifact.presence.presenceclient.handle_presence(stanza)

    contacts = artifact.presence.get_contacts()

    bare_jid = jid.bare()
    assert bare_jid in contacts
    assert contacts[bare_jid]["name"] == "My UnAvailable Friend"

    assert "presence" not in contacts[bare_jid]


def test_get_contact(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    item = XSOItem(jid=jid)
    item.approved = True
    item.name = "My Friend"

    artifact.presence.roster._update_entry(item)

    contact = artifact.presence.get_contact(jid)

    assert type(contact) == dict
    assert contact["approved"]
    assert contact["name"] == "My Friend"
    assert contact["subscription"] == "none"
    assert "ask" not in contact
    assert "groups" not in contact


def test_get_invalid_jid_contact():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    with pytest.raises(ContactNotFound):
        artifact.presence.get_contact(JID.fromstr("invalid@contact"))


def test_get_invalid_str_contact():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    with pytest.raises(AttributeError):
        artifact.presence.get_contact("invalid@contact")


def test_subscribe(jid):
    peer_jid = str(jid)
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.client.enqueue = Mock()
    artifact.presence.subscribe(peer_jid)

    assert artifact.client.enqueue.mock_calls
    arg = artifact.client.enqueue.call_args[0][0]

    assert arg.to == jid.bare()
    assert arg.type_ == PresenceType.SUBSCRIBE


def test_unsubscribe(jid):
    peer_jid = str(jid)
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.client.enqueue = Mock()
    artifact.presence.unsubscribe(peer_jid)

    assert artifact.client.enqueue.mock_calls
    arg = artifact.client.enqueue.call_args[0][0]

    assert arg.to == jid.bare()
    assert arg.type_ == PresenceType.UNSUBSCRIBE


def test_approve(jid):
    peer_jid = str(jid)
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.client.enqueue = Mock()
    artifact.presence.approve(peer_jid)

    assert artifact.client.enqueue.mock_calls
    arg = artifact.client.enqueue.call_args[0][0]

    assert arg.to == jid.bare()
    assert arg.type_ == PresenceType.SUBSCRIBED


def test_on_available(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.on_available = Mock()

    stanza = Presence(from_=jid, type_=PresenceType.AVAILABLE)
    artifact.presence.presenceclient.handle_presence(stanza)

    jid_arg = artifact.presence.on_available.call_args[0][0]
    stanza_arg = artifact.presence.on_available.call_args[0][1]

    assert jid_arg == str(jid)
    assert stanza_arg.type_ == PresenceType.AVAILABLE


def test_on_unavailable(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.on_unavailable = Mock()
    artifact.presence.presenceclient._presences[jid.bare()] = {"home": None}

    stanza = Presence(from_=jid, type_=PresenceType.UNAVAILABLE)
    artifact.presence.presenceclient.handle_presence(stanza)

    jid_arg = artifact.presence.on_unavailable.call_args[0][0]
    stanza_arg = artifact.presence.on_unavailable.call_args[0][1]

    assert jid_arg == str(jid)
    assert stanza_arg.type_ == PresenceType.UNAVAILABLE


def test_on_subscribe(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.on_subscribe = Mock()

    stanza = Presence(from_=jid, type_=PresenceType.SUBSCRIBE)
    artifact.presence.roster.handle_subscribe(stanza)

    jid_arg = artifact.presence.on_subscribe.call_args[0][0]

    assert jid_arg == str(jid)


def test_on_subscribe_approve_all(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.approve_all = True
    artifact.client.enqueue = Mock()

    stanza = Presence(from_=jid, type_=PresenceType.SUBSCRIBE)
    artifact.presence.roster.handle_subscribe(stanza)

    assert artifact.client.enqueue.mock_calls
    arg = artifact.client.enqueue.call_args[0][0]

    assert arg.to == jid.bare()
    assert arg.type_ == PresenceType.SUBSCRIBED


def test_on_subscribed(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.on_subscribed = Mock()

    stanza = Presence(from_=jid, type_=PresenceType.SUBSCRIBED)
    artifact.presence.roster.handle_subscribed(stanza)

    jid_arg = artifact.presence.on_subscribed.call_args[0][0]

    assert jid_arg == str(jid)


def test_on_unsubscribe(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.on_unsubscribe = Mock()

    stanza = Presence(from_=jid, type_=PresenceType.UNSUBSCRIBE)
    artifact.presence.roster.handle_unsubscribe(stanza)

    jid_arg = artifact.presence.on_unsubscribe.call_args[0][0]

    assert jid_arg == str(jid)


def test_on_unsubscribe_approve_all(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.approve_all = True
    artifact.client.enqueue = Mock()

    stanza = Presence(from_=jid, type_=PresenceType.UNSUBSCRIBE)
    artifact.presence.roster.handle_unsubscribe(stanza)

    assert artifact.client.enqueue.mock_calls
    arg = artifact.client.enqueue.call_args[0][0]

    assert arg.to == jid.bare()
    assert arg.type_ == PresenceType.UNSUBSCRIBED


def test_on_unsubscribed(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    artifact.presence.on_unsubscribed = Mock()

    stanza = Presence(from_=jid, type_=PresenceType.UNSUBSCRIBED)
    artifact.presence.roster.handle_unsubscribed(stanza)

    jid_arg = artifact.presence.on_unsubscribed.call_args[0][0]

    assert jid_arg == str(jid)


def test_on_changed(jid):
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    item = XSOItem(jid=jid)
    item.approved = True
    item.name = "My Friend"

    artifact.presence.roster._update_entry(item)

    stanza = Presence(from_=jid, type_=PresenceType.AVAILABLE, show=PresenceShow.CHAT)
    artifact.presence.presenceclient.handle_presence(stanza)

    contact = artifact.presence.get_contact(jid)
    assert contact["name"] == "My Friend"
    assert contact["presence"].show == PresenceShow.CHAT

    stanza = Presence(from_=jid, type_=PresenceType.AVAILABLE, show=PresenceShow.AWAY)
    artifact.presence.presenceclient.handle_presence(stanza)

    contact = artifact.presence.get_contact(jid)

    assert contact["name"] == "My Friend"
    assert contact["presence"].show == PresenceShow.AWAY


def test_ignore_self_presence():
    artifact = MockedConnectedArtifactFactory()

    future = artifact.start(auto_register=False)
    future.result()

    jid = artifact.jid

    stanza = Presence(from_=jid, type_=PresenceType.AVAILABLE, show=PresenceShow.CHAT)
    artifact.presence.presenceclient.handle_presence(stanza)

    with pytest.raises(ContactNotFound):
        artifact.presence.get_contact(jid)

    assert len(artifact.presence.get_contacts()) == 0
