"""
Example 05 – Unified directory: agents + artifacts
====================================================
Demonstrates the DirectoryArtifact as a shared white+yellow pages service
for BOTH artifacts and agents, using AgentDirectoryMixin for agent
self-registration.

Scenario
────────
  DirectoryArtifact : platform service
  Door              : OperableArtifact, auto-registers (kind=artifact)
  Fridge            : OperableArtifact, auto-registers (kind=artifact)
  RobotAgent        : AgentDirectoryMixin, registers capabilities manually
  OwnerAgent        : AgentDirectoryMixin, registers capabilities manually
  InspectorAgent    : queries the directory to get the full picture

Run
───
  cd /Users/mrebollo/devel/ain25-26/lab/p5_artifact
  uv run python spade_artifact_ext/examples/05_agents_directory.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import spade
from spade_artifact import ArtifactMixin
from spade_bdi.bdi import BDIAgent
from spade_artifact_ext import (
    operation, OperableArtifact,
    ArtifactActuatorMixin, AgentDirectoryMixin,
    DirectoryArtifact,
)

DIR_JID = "directory@localhost"


# ── Artifacts ─────────────────────────────────────────────────────────────────

class Door(OperableArtifact):
    @operation
    async def lock(self):
        await self.publish("door(locked)")

    @operation
    async def unlock(self):
        await self.publish("door(unlocked)")


class Fridge(OperableArtifact):
    @operation
    async def get(self, product: str = "beer"):
        await self.publish(f"fridge(dispensed,{product})")

    @operation
    async def restock(self, qty: int = 6):
        await self.publish(f"fridge(restocked,{qty})")


# ── Agents ────────────────────────────────────────────────────────────────────

class RobotAgent(AgentDirectoryMixin, ArtifactActuatorMixin, ArtifactMixin, BDIAgent):
    """Delivery robot: registers its capabilities in the directory."""
    pass


class OwnerAgent(AgentDirectoryMixin, ArtifactActuatorMixin, ArtifactMixin, BDIAgent):
    """Home owner: registers its capabilities in the directory."""
    pass


class InspectorAgent(ArtifactActuatorMixin, ArtifactMixin, BDIAgent):
    """Queries the directory to get a complete picture of the environment."""

    async def setup(self):
        await super().setup()
        self.add_behaviour(self.InspectBehaviour())

    class InspectBehaviour(spade.behaviour.OneShotBehaviour):
        async def run(self):
            await asyncio.sleep(2.0)   # let all entities register

            await self.agent.artifacts.connect_directory(DIR_JID)
            await asyncio.sleep(0.3)   # wait for first registry push

            print("\n── Directory snapshot ──────────────────────────────────")

            # White pages: who is alive on the PubSub server?
            active = await self.agent.artifacts.discover()
            print(f"PubSub nodes (white pages): {active}")

            # Yellow pages: breakdown by kind
            all_known  = self.agent.artifacts.find()
            agents     = self.agent.artifacts.find("agent")
            artifacts  = self.agent.artifacts.find("artifact")
            print(f"\nAll registered : {all_known}")
            print(f"Agents         : {agents}")
            print(f"Artifacts      : {artifacts}")

            # Yellow pages: by type
            doors   = self.agent.artifacts.find_by_type("Door")
            fridges = self.agent.artifacts.find_by_type("Fridge")
            robots  = self.agent.artifacts.find_by_type("RobotAgent")
            print(f"\nDoors   : {doors}")
            print(f"Fridges : {fridges}")
            print(f"Robots  : {robots}")

            # Yellow pages: by capability
            lockers    = self.agent.artifacts.find_by_op("lock")
            deliverers = self.agent.artifacts.find_by_op("deliver")
            print(f"\nCan lock    : {lockers}")
            print(f"Can deliver : {deliverers}")
            print("────────────────────────────────────────────────────────\n")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    directory = DirectoryArtifact(DIR_JID, "1234")
    door      = Door("door@localhost",   "1234", directory_jid=DIR_JID)
    fridge    = Fridge("fridge@localhost", "1234", directory_jid=DIR_JID)

    robot = RobotAgent(
        "robot@localhost", "1234", asl=None,
        directory_jid=DIR_JID,
        capabilities=["deliver", "move", "restock"],
    )
    owner = OwnerAgent(
        "owner@localhost", "1234", asl=None,
        directory_jid=DIR_JID,
        capabilities=["request", "pay"],
    )
    inspector = InspectorAgent("inspector@localhost", "1234", asl=None)

    # Directory must be first
    await directory.start()
    await asyncio.sleep(0.3)

    await door.start()
    await fridge.start()
    await robot.start()
    await owner.start()
    await inspector.start()

    await asyncio.sleep(5)

    await directory.stop()
    await door.stop()
    await fridge.stop()
    await robot.stop()
    await owner.stop()
    await inspector.stop()


if __name__ == "__main__":
    spade.run(main())
