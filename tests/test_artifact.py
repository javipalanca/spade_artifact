import pytest
import asyncio
from spade.message import Message
from aioxmpp import JID
from asynctest import Mock, CoroutineMock
from tests.factories import MockedConnectedArtifactFactory, MockedConnectedArtifact


@pytest.mark.asyncio
async def test_run(event_loop):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = event_loop
    await artifact.start()
    await artifact._async_join(timeout=1)
    assert artifact.get("test_passed")


@pytest.mark.asyncio
async def test_setup(event_loop):
    class TestArtifact(MockedConnectedArtifact):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.value = False

        async def setup(self):
            self.value = True

        async def run(self):
            self.kill()

    artifact = TestArtifact(jid="fake@jid", password="fake_password")
    artifact.loop = event_loop
    assert artifact.value is False
    await artifact.start()
    await artifact._async_join(timeout=1)
    assert artifact.value


def test_name():
    artifact = MockedConnectedArtifactFactory()
    assert artifact.name == "fake"


@pytest.mark.asyncio
async def test_is_alive(event_loop):
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = event_loop
    assert artifact.is_alive() is False
    await artifact.start()
    assert artifact.is_alive()
    await artifact.stop()


def test_set_get():
    artifact = MockedConnectedArtifactFactory()
    assert artifact.get("A_KEY") is None
    artifact.set("A_KEY", True)
    assert artifact.get("A_KEY")
    artifact.set("A_KEY", 1234)
    assert artifact.get("A_KEY") == 1234


@pytest.mark.asyncio
async def test_send_msg(event_loop):
    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = Mock()
            self.client.send = CoroutineMock()
            msg = Message()
            await self.send(msg)
            self.kill()

    artifact = A(jid="fakejid", password="fakesecret")
    artifact.loop = event_loop
    await artifact.start()
    await artifact._async_join(timeout=1)
    artifact.client.send.assert_called_once()
    actual_call = artifact.client.send.call_args[0][0]
    expected_jid = JID.fromstr("fakejid")
    assert actual_call.from_ == expected_jid


@pytest.mark.asyncio
async def test_receive(event_loop):
    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = Mock()
            self.client.send = CoroutineMock()
            self.msg = await self.receive(1)
            self.kill()

    artifact = A(jid="fakejid", password="fakesecret")
    artifact.loop = event_loop
    await artifact.start()

    future = artifact._message_received(Message().prepare())
    await asyncio.wrap_future(future)
    await artifact._async_join(timeout=1)

    assert hasattr(artifact, 'msg')
    received_msg = artifact.msg
    expected_msg = Message()
    assert received_msg.to == expected_msg.to
    assert received_msg.thread == expected_msg.thread
    assert received_msg.metadata == expected_msg.metadata


@pytest.mark.asyncio
async def test_mailbox_size(event_loop):
    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = Mock()
            self.client.send = CoroutineMock()
            self.msg = await self.receive(1)
            self.kill()

    artifact = A(jid="fakejid", password="fakesecret")
    artifact.loop = event_loop
    await artifact.start()
    assert artifact.mailbox_size() == 0

    msg = Message().prepare()
    await artifact.queue.put(Message.from_node(msg))
    assert artifact.mailbox_size() == 1

    await artifact._async_join(timeout=1)
    assert artifact.mailbox_size() == 0
