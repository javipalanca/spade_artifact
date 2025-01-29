import pytest
import asyncio
from spade.message import Message

from tests.compat import Mock, AsyncMock
from tests.factories import MockedConnectedArtifactFactory, MockedConnectedArtifact

@pytest.mark.asyncio
async def test_run():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()
    await artifact.start()
    await artifact._async_join(timeout=1)
    assert artifact.get("test_passed")

@pytest.mark.asyncio
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
    artifact.loop = asyncio.get_running_loop()
    assert artifact.value is False
    await artifact.start()
    await artifact._async_join(timeout=1)
    assert artifact.value

def test_name():
    artifact = MockedConnectedArtifactFactory()
    assert artifact.name == "fake"

@pytest.mark.asyncio
async def test_is_alive():
    artifact = MockedConnectedArtifactFactory()
    artifact.loop = asyncio.get_running_loop()
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
async def test_send_msg():
    artifact = MockedConnectedArtifact(jid="fakejid", password="fakesecret")
    artifact.loop = asyncio.get_running_loop()

    # Set up our mock
    mock_client = Mock()
    mock_client.send = AsyncMock()
    artifact.client = mock_client

    # Test send directly
    msg = Message()
    await artifact.send(msg)

    # Verify
    assert mock_client.send.called, "send was not called"
@pytest.mark.asyncio
async def test_receive():
    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = Mock()
            self.client.send = AsyncMock()
            self.msg = await self.receive(timeout=1)
            self.kill()

    artifact = A(jid="fakejid", password="fakesecret")
    artifact.loop = asyncio.get_running_loop()
    await artifact.start()

    msg = Message()
    msg.to = "receiver@test.com"
    msg.sender = "sender@test.com"
    msg.thread = "test_thread"

    await artifact.queue.put(msg)

    try:
        await asyncio.wait_for(
            artifact._async_join(timeout=1),
            timeout=2
        )
    except TimeoutError:
        await artifact.stop()
        pytest.fail("Artifact did not stop in time")

    assert hasattr(artifact, 'msg')
    received_msg = artifact.msg
    assert received_msg.to == msg.to
    assert received_msg.thread == msg.thread
    assert received_msg.sender == msg.sender

@pytest.mark.asyncio
async def test_mailbox_size():
    class A(MockedConnectedArtifact):
        async def run(self):
            self.client = Mock()
            self.client.send_message = AsyncMock()
            self.msg = await self.receive(1)
            self.kill()

    artifact = A(jid="fakejid", password="fakesecret")
    artifact.loop = asyncio.get_running_loop()
    await artifact.start()
    assert artifact.mailbox_size() == 0

    msg = Message().prepare()
    await artifact.queue.put(Message.from_node(msg))
    assert artifact.mailbox_size() == 1

    await artifact._async_join(timeout=1)
    assert artifact.mailbox_size() == 0
