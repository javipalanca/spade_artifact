#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `spade_artifact` package."""
from asynctest import Mock, CoroutineMock
from spade.message import Message

from tests.factories import MockedConnectedArtifactFactory, MockedConnectedArtifact


def test_run():
    artifact = MockedConnectedArtifactFactory()
    artifact.start()
    assert artifact.get("test_passed")


def test_setup():
    class TestArtifact(MockedConnectedArtifact):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.value = False

        async def setup(self):
            self.value = True

    artifact = TestArtifact(jid="fake@jid", password="fake_password")

    assert artifact.value is False
    artifact.start()
    assert artifact.value


def test_name():
    artifact = MockedConnectedArtifactFactory()
    assert artifact.name == "fake"


def test_is_alive():
    artifact = MockedConnectedArtifactFactory()
    assert artifact.is_alive() is False
    artifact.start()
    assert artifact.is_alive()


def test_set_get():
    artifact = MockedConnectedArtifactFactory()

    assert artifact.get("A_KEY") is None

    artifact.set("A_KEY", True)

    assert artifact.get("A_KEY")

    artifact.set("A_KEY", 1234)

    assert artifact.get("A_KEY") == 1234


def test_send_msg():
    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = Mock()
            self.client.send = CoroutineMock()
            msg = Message()
            await self.send(msg)

    artifact = A(jid="fakejid", password="fakesecret")

    artifact.start()

    assert artifact.client.send.called_with(Message().prepare())


def test_receive():
    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = Mock()
            self.client.send = CoroutineMock()
            self.msg = await self.receive(1)

    artifact = A(jid="fakejid", password="fakesecret")

    artifact._message_received(Message().prepare())

    artifact.start()

    assert artifact.msg == Message()


def test_mailbox_size():
    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = Mock()
            self.client.send = CoroutineMock()
            self.msg = await self.receive(1)

    artifact = A(jid="fakejid", password="fakesecret")

    artifact._message_received(Message().prepare())

    assert artifact.mailbox_size() == 1

    artifact.start()

    assert artifact.msg == Message()

    assert artifact.mailbox_size() == 0
