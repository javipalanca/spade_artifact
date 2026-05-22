"""
spade_artifact_ext.py
Extension of spade_artifact adding CArtAgO-style operation invocation
and a platform-level DirectoryArtifact (white + yellow pages).

────────────────────────────────────────────────────────────────────────
QUICK REFERENCE
────────────────────────────────────────────────────────────────────────

  # ── Artifact side ────────────────────────────────────────────────────
  from spade_artifact_ext import OperableArtifact, operation

  class Door(OperableArtifact):
      @operation
      async def lock(self):
          await self.publish("locked")

      @operation
      async def unlock(self):
          await self.publish("unlocked")

  # Start with optional auto-registration in the platform directory
  door = Door("door@localhost", "1234", directory_jid="directory@localhost")

  # ── Agent side ────────────────────────────────────────────────────────
  from spade_artifact_ext import ArtifactActuatorMixin

  class MyAgent(ArtifactActuatorMixin, ArtifactMixin, BDIAgent):
      async def setup(self):
          await super().setup()

          # White pages: what artifacts exist?
          active = await self.artifacts.discover()

          # Yellow pages: connect to directory and query by capability
          await self.artifacts.connect_directory("directory@localhost")
          doors  = self.artifacts.find_by_type("Door")
          lockers = self.artifacts.find_by_op("lock")

          # Observe an artifact (existing API, unchanged)
          await self.artifacts.focus("door@localhost", self.door_callback)

          # Invoke an operation (new, symmetric with focus)
          await self.artifacts.use("door@localhost", "lock")

  # ── Platform setup ────────────────────────────────────────────────────
  from spade_artifact_ext import DirectoryArtifact

  directory = DirectoryArtifact("directory@localhost", "1234")
  await directory.start()
  # ... then start other artifacts with directory_jid="directory@localhost"

────────────────────────────────────────────────────────────────────────
API analogy
────────────────────────────────────────────────────────────────────────
  publish()                      ←→  @operation method body
  artifacts.focus(jid, cb)       ←→  artifacts.use(jid, op, *args)
  artifacts.discover()           = white pages (who exists?)
  artifacts.connect_directory()  = subscribe to yellow pages
  artifacts.find_by_type(t)      = yellow pages query by type
  artifacts.find_by_op(op)       = yellow pages query by capability
"""

import asyncio
import inspect
import json
import functools
import logging

from .artifact import Artifact
from .agent import ArtifactMixin
from spade.message import Message

logger = logging.getLogger(__name__)

_OP_TYPE = "artifact_operation"


# ─────────────────────────────────────────────────────────────────────────────
# Decorator
# ─────────────────────────────────────────────────────────────────────────────

def operation(func):
    """
    Marks an async method as an agent-invokable operation.
    Equivalent to @OPERATION in CArtAgO.

        class Fridge(OperableArtifact):
            @operation
            async def get(self, product: str): ...

            @operation
            async def restock(self, qty: int, product: str = "beer"): ...
    """
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        return await func(self, *args, **kwargs)
    wrapper._is_operation = True
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# Proxy: extends self.artifacts with use / discover / directory queries
# ─────────────────────────────────────────────────────────────────────────────

class _ArtifactComponentProxy:
    """
    Transparent proxy around spade_artifact's ArtifactComponent.
    Delegates all existing calls (focus, ignore, …) and adds:
        use()               – invoke @operation on an artifact
        discover()          – white pages: list all active artifact JIDs
        connect_directory() – subscribe to a DirectoryArtifact
        find_by_type()      – yellow pages: lookup by artifact class name
        find_by_op()        – yellow pages: lookup by @operation name
    """

    _PRIVATE = ('_component', '_agent', '_dir_cache')

    def __init__(self, component, agent):
        object.__setattr__(self, '_component', component)
        object.__setattr__(self, '_agent', agent)
        object.__setattr__(self, '_dir_cache', {})   # {jid: {type, operations}}

    # ── Transparent delegation ────────────────────────────────────────────

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, '_component'), name)

    def __setattr__(self, name, value):
        if name in self._PRIVATE:
            object.__setattr__(self, name, value)
        else:
            setattr(object.__getattribute__(self, '_component'), name, value)

    # ── Operation invocation ─────────────────────────────────────────────

    async def use(self, artifact_jid: str, operation_name: str, *args):
        """
        Invoke a named @operation on a remote OperableArtifact.

            artifacts.use(jid, op)          # no args
            artifacts.use(jid, op, 5, "beer")  # with args
        """
        agent = object.__getattribute__(self, '_agent')
        msg = Message(
            to=artifact_jid,
            body=json.dumps(list(args)),
            metadata={"type": _OP_TYPE, "operation": operation_name},
        )
        await agent.send(msg)
        logger.debug(f"[artifacts.use] → {artifact_jid}::{operation_name}({args})")

    # ── White pages ──────────────────────────────────────────────────────

    async def discover(self) -> list:
        """
        Return the JIDs of all artifacts currently active (white pages).

        Each Artifact registers a PubSub node named after its JID when it
        starts, so listing nodes ≡ listing live artifacts.

            active = await self.artifacts.discover()
            # → ["door@localhost", "fridge@localhost", "directory@localhost"]
        """
        agent = object.__getattribute__(self, '_agent')
        nodes = await agent.pubsub.get_nodes(agent.pubsub_server)
        jids = [n["node"] for n in (nodes or [])]
        logger.debug(f"[artifacts.discover] {jids}")
        return jids

    # ── Yellow pages ─────────────────────────────────────────────────────


    async def connect_directory(self, directory_jid: str):
        """
        Subscribe to a DirectoryArtifact and keep a local cache of the registry.

        After calling this, find_by_type() and find_by_op() work synchronously
        against the local cache, which is kept up-to-date via PubSub.

            await self.artifacts.connect_directory("directory@localhost")
        """
        await self.focus(directory_jid, self._on_directory_update)
        logger.info(f"[artifacts] connected to directory {directory_jid}")

    def _on_directory_update(self, jid, payload: str):
        """Internal PubSub callback: refreshes local cache when registry changes."""
        try:
            cache = json.loads(payload)
            object.__setattr__(self, '_dir_cache', cache)
            logger.debug(f"[artifacts] directory cache updated: {list(cache.keys())}")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[artifacts] bad directory payload: {e}")

    def find_by_type(self, artifact_type: str) -> list:
        """
        Return JIDs of all registered entities of the given class name.
        Requires connect_directory() to have been called first.

            doors = self.artifacts.find_by_type("Door")
            # → ["door@localhost"]
        """
        cache = object.__getattribute__(self, '_dir_cache')
        return [jid for jid, info in cache.items()
                if info.get("type") == artifact_type]

    def find_by_op(self, operation_name: str) -> list:
        """
        Return JIDs of all registered entities that declare the given capability.
        Requires connect_directory() to have been called first.
        Works for both artifact @operations and agent capabilities.

            lockers = self.artifacts.find_by_op("lock")
            # → ["door@localhost"]
        """
        cache = object.__getattribute__(self, '_dir_cache')
        return [jid for jid, info in cache.items()
                if operation_name in info.get("operations", [])]

    def find(self, kind: str = None) -> list:
        """
        Return JIDs of registered entities, optionally filtered by kind.
        Requires connect_directory() to have been called first.

        Args:
            kind : None → all entities
                   "artifact" → only artifacts
                   "agent"    → only agents

        Examples:
            all_entities  = self.artifacts.find()
            all_agents    = self.artifacts.find("agent")
            all_artifacts = self.artifacts.find("artifact")
        """
        cache = object.__getattribute__(self, '_dir_cache')
        if kind is None:
            return list(cache.keys())
        return [jid for jid, info in cache.items()
                if info.get("kind") == kind]



# ─────────────────────────────────────────────────────────────────────────────
# Mixin for agents
# ─────────────────────────────────────────────────────────────────────────────

class ArtifactActuatorMixin:
    """
    Agent mixin that replaces self.artifacts with the extended proxy.

    Place BEFORE ArtifactMixin in the MRO:
        class MyAgent(ArtifactActuatorMixin, ArtifactMixin, BDIAgent): ...
    """

    async def setup(self):
        await super().setup()
        if hasattr(self, 'artifacts'):
            self.artifacts = _ArtifactComponentProxy(self.artifacts, self)
        else:
            logger.warning(
                "[ArtifactActuatorMixin] self.artifacts not found; "
                "ensure ArtifactMixin is in the MRO."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Operable Artifact  (with optional auto-registration)
# ─────────────────────────────────────────────────────────────────────────────

class OperableArtifact(Artifact):
    """
    Artifact that dispatches incoming @operation calls automatically.

    Optional auto-registration with a DirectoryArtifact:
        door = Door("door@localhost", "1234", directory_jid="directory@localhost")

    If you override run(), interleave _process_operations() to keep the
    operation listener active:
        async def run(self):
            while True:
                await self._process_operations()
                await asyncio.sleep(0.1)
    """

    def __init__(self, *args, directory_jid: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._directory_jid = directory_jid

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def _async_start(self, *args, **kwargs):
        await super()._async_start(*args, **kwargs)
        if self._directory_jid:
            # Small delay to ensure the directory artifact is ready
            await asyncio.sleep(0.5)
            await self._auto_register()

    async def _auto_register(self):
        """Introspect @operation methods and register with the DirectoryArtifact."""
        ops = [
            name
            for name, method in inspect.getmembers(self, predicate=inspect.ismethod)
            if getattr(method, '_is_operation', False)
        ]
        artifact_type = type(self).__name__
        msg = Message(
            to=self._directory_jid,
            body=json.dumps([str(self.jid), artifact_type, json.dumps(ops), "artifact"]),
            metadata={"type": _OP_TYPE, "operation": "register"},
        )
        await self.send(msg)
        logger.info(
            f"[{artifact_type}@{self.jid}] registered with directory "
            f"{self._directory_jid}: ops={ops}"
        )

    # ── Operation dispatching ─────────────────────────────────────────────

    async def run(self):
        await self._listen_for_operations()

    async def _listen_for_operations(self):
        while True:
            await self._process_operations(timeout=1)

    async def _process_operations(self, timeout: float = 0):
        """Process ONE pending operation message (non-blocking when timeout=0)."""
        msg = await self.receive(timeout=timeout)
        if msg is None:
            return
        if msg.metadata.get("type") != _OP_TYPE:
            return

        op_name = msg.metadata.get("operation", "")
        try:
            args = json.loads(msg.body) if msg.body else []
        except json.JSONDecodeError:
            logger.warning(f"[OperableArtifact] bad JSON body: {msg.body!r}")
            return

        method = getattr(self, op_name, None)
        if method is None or not getattr(method, "_is_operation", False):
            logger.warning(f"[OperableArtifact] unknown @operation: '{op_name}'")
            return

        logger.debug(f"[OperableArtifact] @operation '{op_name}'{args}")
        asyncio.create_task(method(*args))


# ─────────────────────────────────────────────────────────────────────────────
# DirectoryArtifact  —  platform-level white + yellow pages
# ─────────────────────────────────────────────────────────────────────────────

class DirectoryArtifact(OperableArtifact):
    """
    Platform artifact providing AMS-like and DF-like services for artifacts.

    White pages : who exists?          → artifacts.discover()
    Yellow pages: who provides X?      → artifacts.find_by_type() / find_by_op()

    Architectural note
    ──────────────────
    Modelled as an artifact (not an agent) because the directory has no
    intentionality: it is a passive shared resource with operations.
    This mirrors JaCaMo's WorkspaceArtifact design.

    Usage
    ─────
    # 1. Start the directory first
    directory = DirectoryArtifact("directory@localhost", "1234")
    await directory.start()

    # 2. Other artifacts register automatically
    door = Door("door@localhost", "1234", directory_jid="directory@localhost")
    await door.start()

    # 3. Agents subscribe and query
    await self.artifacts.connect_directory("directory@localhost")
    doors   = self.artifacts.find_by_type("Door")
    lockers = self.artifacts.find_by_op("lock")
    """

    def __init__(self, *args, **kwargs):
        # The directory never registers itself with another directory
        kwargs.pop('directory_jid', None)
        super().__init__(*args, **kwargs)
        self._registry: dict = {}   # {jid: {"type": str, "operations": list}}

    # ── Operations ────────────────────────────────────────────────────────

    @operation
    async def register(self, jid: str, artifact_type: str, operations_json: str,
                       kind: str = "artifact"):
        """
        Register any entity (artifact or agent) in the directory.

        Called automatically by OperableArtifact (kind='artifact') and
        AgentDirectoryMixin (kind='agent') on startup.

        Args:
            jid            : JID of the entity, e.g. "door@localhost"
            artifact_type  : class name, e.g. "Door" or "RobotAgent"
            operations_json: JSON list of @operation / capability names
            kind           : "artifact" (default) or "agent"
        """
        ops = json.loads(operations_json) if operations_json else []
        self._registry[jid] = {"kind": kind, "type": artifact_type, "operations": ops}
        await self.publish(json.dumps(self._registry))
        logger.info(f"[directory] + {jid} ({kind}/{artifact_type}) ops={ops}")

    @operation
    async def unregister(self, jid: str):
        """
        Unregister an artifact (e.g. when it shuts down).

        Args:
            jid : JID of the artifact to remove
        """
        if jid in self._registry:
            entry = self._registry.pop(jid)
            await self.publish(json.dumps(self._registry))
            logger.info(f"[directory] - {jid} ({entry.get('kind','?')}")
        else:
            logger.warning(f"[directory] unregister: unknown jid '{jid}'")


# ─────────────────────────────────────────────────────────────────────────────
# AgentDirectoryMixin  —  self-registration of agents in DirectoryArtifact
# ─────────────────────────────────────────────────────────────────────────────

class AgentDirectoryMixin:
    """
    Mixin that lets a SPADE agent register itself in a DirectoryArtifact,
    announcing its type and declared capabilities (yellow pages for agents).

    Unlike OperableArtifact (which introspects @operation automatically),
    capabilities are declared explicitly by the developer — because an agent's
    "interface" is not a fixed set of decorators but a semantic contract.

    Place BEFORE ArtifactActuatorMixin and ArtifactMixin in the MRO:

        class RobotAgent(AgentDirectoryMixin, ArtifactActuatorMixin, ArtifactMixin, BDIAgent):
            ...

    Constructor parameters (all optional):
        directory_jid  : JID of the DirectoryArtifact
        agent_type     : label for yellow-pages queries (default: class name)
        capabilities   : list of capability names the agent offers

    Usage:
        robot = RobotAgent(
            "robot@localhost", "1234", asl="robot.asl",
            directory_jid="directory@localhost",
            capabilities=["deliver", "move", "restock"]
        )
    """

    def __init__(self, *args,
                 directory_jid: str = None,
                 agent_type: str = None,
                 capabilities: list = None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._dir_jid      = directory_jid
        self._agent_type   = agent_type or type(self).__name__
        self._capabilities = capabilities or []

    async def setup(self):
        await super().setup()
        if self._dir_jid:
            await asyncio.sleep(0.5)   # let the directory be ready
            await self._register_agent()

    async def _register_agent(self):
        """Send the registration message to the DirectoryArtifact."""
        msg = Message(
            to=self._dir_jid,
            body=json.dumps([
                str(self.jid),
                self._agent_type,
                json.dumps(self._capabilities),
                "agent",
            ]),
            metadata={"type": _OP_TYPE, "operation": "register"},
        )
        await self.send(msg)
        logger.info(
            f"[{self._agent_type}@{self.jid}] registered with directory "
            f"{self._dir_jid}: capabilities={self._capabilities}"
        )

    async def unregister_agent(self):
        """Explicitly remove the agent from the directory (call before stop)."""
        if self._dir_jid:
            msg = Message(
                to=self._dir_jid,
                body=json.dumps([str(self.jid)]),
                metadata={"type": _OP_TYPE, "operation": "unregister"},
            )
            await self.send(msg)
            logger.info(f"[{self._agent_type}] unregistered from directory")
