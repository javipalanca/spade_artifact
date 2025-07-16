#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `spade_artifact` package."""
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock

import pytest
from spade.message import Message
from slixmpp import Message as SlixmppMessage

from tests.factories import MockedConnectedArtifactFactory, MockedConnectedArtifact


async def test_run():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()
    await artifact.start()

    await artifact.join()

    assert artifact.get("test_passed")


async def test_setup():
    class TestArtifact(MockedConnectedArtifact):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.value = False

        async def setup(self):
            self.value = True

        async def run(self):
            self.kill()

    artifact = TestArtifact(jid="fake@jid", password="fake_password")
    artifact.loop = asyncio.get_event_loop()

    assert artifact.value is False
    await artifact.start()
    await artifact.join()
    assert artifact.value


async def test_name():
    artifact = MockedConnectedArtifactFactory()
    assert artifact.name == "fake"


async def test_is_alive():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_event_loop()

    assert artifact.is_alive() is False
    await artifact.start()

    assert artifact.is_alive()


async def test_set_get():
    artifact = MockedConnectedArtifactFactory()

    assert artifact.get("A_KEY") is None

    artifact.set("A_KEY", True)

    assert artifact.get("A_KEY")

    artifact.set("A_KEY", 1234)

    assert artifact.get("A_KEY") == 1234


@pytest.mark.asyncio
async def test_send_msg():
    message = MagicMock()
    message_prepare = MagicMock()
    message.prepare.return_value = message_prepare
    message_prepare.send = MagicMock()

    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = MagicMock()
            await self.send(message)
            self.kill()

    artifact = A(jid="fakejid", password="fakesecret")
    artifact.loop = asyncio.get_event_loop()

    await artifact.start()
    await artifact.join()

    assert message_prepare.send.called
    message.prepare.assert_called_with(artifact.client)


@pytest.mark.asyncio
async def test_receive():
    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = Mock()
            self.client.send = AsyncMock()
            self.msg = await self.receive(1)
            self.kill()

    artifact = A(jid="fakejid", password="fakesecret")
    artifact.loop = asyncio.get_event_loop()
    artifact._message_received(SlixmppMessage())

    await artifact.start()
    await artifact.join()

    assert artifact.msg == Message()


@pytest.mark.asyncio
async def test_mailbox_size():
    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = Mock()
            self.client.send = AsyncMock()
            self.msg = await self.receive(1)
            self.kill()

    artifact = A(jid="fakejid", password="fakesecret")
    artifact.loop = asyncio.get_event_loop()

    artifact._message_received(SlixmppMessage())

    assert artifact.mailbox_size() == 1

    await artifact.start()
    await artifact.join()

    assert artifact.msg == Message()

    assert artifact.mailbox_size() == 0
