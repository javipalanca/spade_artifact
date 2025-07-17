# -*- coding: utf-8 -*-
import abc
import asyncio
import time
from asyncio import Event
from typing import Union, Optional

from slixmpp import JID
from slixmpp.exceptions import IqError, _DEFAULT_ERROR_TYPES
from slixmpp.stanza.message import Message as SlixmppMessage

from loguru import logger
from spade.agent import AuthenticationFailure, DisconnectedException
from spade.container import Container
from spade.message import Message
from spade.presence import PresenceManager
from spade.xmpp_client import XMPPClient
from spade_pubsub import PubSubMixin


class AbstractArtifact(object, metaclass=abc.ABCMeta):
    async def _hook_plugin_before_connection(self, *args, **kwargs):
        """
        Overload this method to hook a plugin before connection is done
        """
        pass

    async def _hook_plugin_after_connection(self, *args, **kwargs):
        """
        Overload this method to hook a plugin after connection is done
        """
        pass


class Artifact(PubSubMixin, AbstractArtifact):
    def __init__(
        self, jid, password, pubsub_server=None, port=5222, verify_security=False
    ):
        """
        Creates an artifact

        Args:
          jid (str): The identifier of the artifact in the form username@server
          password (str): The password to connect to the server
          verify_security (bool): Wether to verify or not the SSL certificates
        """
        self.jid = JID(jid)
        self.xmpp_port = port
        self.password = password
        self.verify_security = verify_security

        self.pubsub_server = (
            pubsub_server if pubsub_server else f"pubsub.{self.jid.domain}"
        )

        self.client: Optional[XMPPClient] = None
        self.presence: Optional[PresenceManager] = None

        self._values = {}

        self.message_dispatcher = None

        self.container = Container()
        self.container.register(self)

        self.loop = self.container.loop

        self.queue = asyncio.Queue()
        self._alive = Event()
        self.subscriptions = {}

    def set_loop(self, loop):
        self.loop = loop

    def set_container(self, container):
        """
        Sets the container to which the artifact is attached

        Args:
            container (spade.container.Container): the container to be attached to
        """
        self.container = container

    async def _hook_plugin_after_connection(self, *args, **kwargs):
        try:
            await super()._hook_plugin_after_connection(*args, **kwargs)
        except AttributeError:
            logger.debug("_hook_plugin_after_connection is undefined")

        # Set the publication handler once the connection is established
        self.pubsub.set_on_item_published(self.on_item_published)

    async def start(self, auto_register: bool = True) -> None:
        """
        Tells the container to start this agent.
        It returns a coroutine or a future depending on whether it is called from a coroutine or a synchronous method.

        Args:
            auto_register (bool): register the agent in the server (Default value = True)
        """
        return await self._async_start(auto_register=auto_register)

    async def _async_start(self, auto_register=True):
        """
        Starts the agent from a coroutine. This fires some actions:

            * if auto_register: register the agent in the server
            * runs the event loop
            * connects the agent to the server
            * runs the registered behaviours

        Args:
          auto_register (bool, optional): register the agent in the server (Default value = True)

        """

        await self._hook_plugin_before_connection()

        self.client = XMPPClient(
            self.jid, self.password, self.verify_security, auto_register
        )

        # Presence service
        self.presence = PresenceManager(agent=self, approve_all=False)

        await self._async_connect()
        await self._hook_plugin_after_connection()

        # pubsub initialization
        try:
            self._node = str(self.jid.bare)
            await self.pubsub.create(self.pubsub_server, f"{self._node}")
        except IqError as e:
            if e.condition == _DEFAULT_ERROR_TYPES["conflict"]:
                logger.info(f"Node {self._node} already registered")
            elif e.condition == _DEFAULT_ERROR_TYPES["forbidden"]:
                logger.error(
                    f"Artifact {self._node} is not allowed to publish properties."
                )
            else:
                logger.error(f"Error creating node: {e.format()}")
            raise e

        await self.setup()
        self._alive.set()
        asyncio.run_coroutine_threadsafe(self.run(), loop=self.loop)

    async def _async_connect(self):  # pragma: no cover
        """ connect and authenticate to the XMPP server. Async mode. """

        if self.client is not None:
            self.client.connected_event = asyncio.Event()
            self.client.disconnected_event = asyncio.Event()
            self.client.failed_auth_event = asyncio.Event()

            connected_task = asyncio.create_task(
                self.client.connected_event.wait(), name="connected"
            )
            disconnected_task = asyncio.create_task(
                self.client.disconnected_event.wait(), name="disconnected"
            )
            failed_auth_task = asyncio.create_task(
                self.client.failed_auth_event.wait(), name="failed_auth"
            )

            self.client.add_event_handler(
                "session_start", lambda _: self.client.connected_event.set()
            )
            self.client.add_event_handler(
                "disconnected", lambda _: self.client.disconnected_event.set()
            )
            self.client.add_event_handler(
                "failed_all_auth", lambda _: self.client.failed_auth_event.set()
            )
            self.client.add_event_handler("message", self._message_received)

            _ = self.client.connect(host=self.jid.host, port=self.xmpp_port)

            done, pending = await asyncio.wait(
                [connected_task, disconnected_task, failed_auth_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            for task in done:
                await task

                if task.get_name() == "failed_auth":
                    raise AuthenticationFailure(
                        "Could not authenticate the agent. Check user and password or use auto_register=True"
                    )
                elif task.get_name() == "disconnected":
                    raise DisconnectedException(
                        "Error during the connection with the server"
                    )

            logger.info(f"Agent {str(self.jid)} connected and authenticated.")

        else:
            raise RuntimeError("XMPPClient is not initialized.")

    async def setup(self):
        """
        Setup artifact before startup.
        This coroutine may be overloaded.
        """
        await asyncio.sleep(0)

    def kill(self):
        self._alive.clear()

    async def run(self):
        """
        Main body of the artifact.
        This coroutine SHOULD be overloaded.
        """
        raise NotImplementedError

    @property
    def name(self):
        """Returns the name of the artifact (the string before the '@')"""

        return self.jid.node

    async def stop(self) -> None:
        """
        Stops this agent.
        """
        self.kill()
        return await self._async_stop()

    async def _async_stop(self):
        """Stops an artifact and kills all its behaviours."""
        if self.presence:
            self.presence.set_unavailable()

        if self.is_alive():
            await self.client.disconnect()
            logger.info("Client disconnected.")

        self._alive.clear()

    def is_alive(self):
        """
        Checks if the artifact is alive.

        Returns:
          bool: wheter the artifact is alive or not

        """
        return self._alive.is_set()

    def set(self, name, value):
        """
        Stores a knowledge item in the artifact knowledge base.

        Args:
          name (str): name of the item
          value (object): value of the item

        """
        self._values[name] = value

    def get(self, name):
        """
        Recovers a knowledge item from the artifact's knowledge base.

        Args:
          name(str): name of the item

        Returns:
          object: the object retrieved or None

        """
        if name in self._values:
            return self._values[name]
        else:
            return None

    def _message_received(self, msg) -> None:
        """
        Callback run when an XMPP Message is reveived.
        The slixmpp.stanza.Message is converted to spade.message.Message

        Args:
          msg (slixmpp.stanza.Messagge): the message just received.
        """

        msg = Message.from_node(msg)
        logger.debug(f"Got message: {msg}")
        self.queue.put_nowait(msg)

    async def send(self, msg: Message):
        """
        Sends a message.

        Args:
            msg (spade.message.Message): the message to be sent.
        """
        if not msg.sender:
            msg.sender = str(self.jid)
            logger.debug(f"Adding artifact's jid as sender to message: {msg}")
        slixmpp_msg = msg.prepare(self.client)
        slixmpp_msg.send()
        msg.sent = True

    async def receive(self, timeout: float = None) -> Union[Message, None]:
        """
        Receives a message for this artifact.
        If timeout is not None it returns the message or "None"
        after timeout is done.

        Args:
            timeout (float): number of seconds until return

        Returns:
            spade.message.Message: a Message or None
        """
        if timeout:
            coro = self.queue.get()
            try:
                msg = await asyncio.wait_for(coro, timeout=timeout)
            except asyncio.TimeoutError:
                msg = None
        else:
            try:
                msg = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                msg = None
        return msg

    def mailbox_size(self) -> int:
        """
        Checks if there is a message in the mailbox

        Returns:
          int: the number of messages in the mailbox

        """
        return self.queue.qsize()

    def join(self, timeout=None):
        try:
            in_coroutine = asyncio.get_event_loop() == self.loop
        except RuntimeError:  # pragma: no cover
            in_coroutine = False

        if not in_coroutine:
            t_start = time.time()
            while self.is_alive():
                time.sleep(0.001)
                t = time.time()
                if timeout is not None and t - t_start > timeout:
                    raise TimeoutError
        else:
            return self._async_join(timeout=timeout)

    async def _async_join(self, timeout):
        t_start = time.time()
        while self.is_alive():
            await asyncio.sleep(0.001)
            t = time.time()
            if timeout is not None and t - t_start > timeout:
                raise TimeoutError

    async def publish(self, payload: str) -> None:
        await self.pubsub.publish(
            self.pubsub_server, self._node, payload, ifrom=self.jid.bare
        )

    def on_item_published(self, msg: SlixmppMessage):
        """
        Callback to handle an item published event.

        Args:
            jid (str): The JID of the publisher.
            node (str): The node/topic from which the item was published.
            item (object): The item that was published.
            message (str, optional): Additional message or data associated with the publication.
        """
        node = msg["pubsub_event"]["items"]["node"]
        if node in self.subscriptions:
            item = msg["pubsub_event"]["items"]["item"]["payload"]
            jid = msg["pubsub_event"]["items"]["item"]["publisher"]
            self.subscriptions[node](jid, item)

    async def link(self, target_artifact_jid, callback):
        """
        Subscribe to another artifact's publications.

        Args:
            target_artifact_jid (str): The JID of the target artifact to subscribe to.
            callback (Callable): The callback to invoke when an item is published.
        """
        await self.pubsub.subscribe(self.pubsub_server, str(target_artifact_jid))
        self.subscriptions[target_artifact_jid] = callback

    async def unlink(self, target_artifact_jid):
        """
        Unsubscribe from another artifact's publications.

        Args:
            target_artifact_jid (str): The JID of the target artifact to unsubscribe from.
        """
        await self.pubsub.unsubscribe(self.pubsub_server, str(target_artifact_jid))
        if target_artifact_jid in self.subscriptions:
            del self.subscriptions[target_artifact_jid]
