#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `spade_artifact` package."""
from spade.message import Message

from tests.factories import MockedConnectedArtifactFactory, MockedConnectedArtifact


def test_run():
    artifact = MockedConnectedArtifactFactory()
    artifact.start()
    assert artifact.get("test_passed")


def test_send_msg():
    class A(MockedConnectedArtifact):
        async def run(self):
            msg = Message()
            await self.send(msg)

    artifact = A(jid="fakejid", password="fakesecret")

    artifact.start()

    assert artifact.client.send.called_with(Message().prepare())


def test_receive():
    class A(MockedConnectedArtifact):
        async def run(self):
            self.msg = await self.receive(1)

    artifact = A(jid="fakejid", password="fakesecret")

    artifact._message_received(Message().prepare())

    artifact.start()

    assert artifact.msg == Message()
