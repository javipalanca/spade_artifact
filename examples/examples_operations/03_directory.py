"""
Example 03 – Yellow pages: DirectoryArtifact
=============================================
Demonstrates the platform-level DirectoryArtifact that acts as both
white pages (who exists?) and yellow pages (who provides capability X?).

Artifacts auto-register when they start (directory_jid parameter).
Agents call connect_directory() once, then use find_by_type() and
find_by_op() as synchronous local lookups against the cached registry.

Scenario
────────
  DirectoryArtifact  : platform service
  Door               : exposes lock / unlock
  Fridge             : exposes get / restock
  SmartAgent         : discovers by type and by operation

Run
───
  cd /Users/mrebollo/devel/ain25-26/lab/p5_artifact
  uv run python spade_artifact_ext/examples/03_directory.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import spade
from spade_artifact import ArtifactMixin
from spade_bdi.bdi import BDIAgent
from spade_artifact_ext import operation, OperableArtifact, ArtifactActuatorMixin, DirectoryArtifact


DIR_JID = "directory@localhost"


# ── Domain artifacts ──────────────────────────────────────────────────────────

class Door(OperableArtifact):
    @operation
    async def lock(self):
        await self.publish("door(locked)")
        print("[door] locked")

    @operation
    async def unlock(self):
        await self.publish("door(unlocked)")
        print("[door] unlocked")


class Fridge(OperableArtifact):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stock = 6

    @operation
    async def get(self, product: str = "beer"):
        if self.stock > 0:
            self.stock -= 1
            await self.publish(f"fridge(stock,{self.stock})")
            print(f"[fridge] got {product}, stock={self.stock}")

    @operation
    async def restock(self, qty: int = 6):
        self.stock += qty
        await self.publish(f"fridge(stock,{self.stock})")
        print(f"[fridge] restocked +{qty}, stock={self.stock}")


# ── Agent ─────────────────────────────────────────────────────────────────────

class SmartAgent(ArtifactActuatorMixin, ArtifactMixin, BDIAgent):

    async def setup(self):
        await super().setup()
        self.add_behaviour(self.DirectoryDemo())

    class DirectoryDemo(spade.behaviour.OneShotBehaviour):
        async def run(self):
            await asyncio.sleep(1.5)   # let all artifacts register

            # Connect to directory (subscribes and caches updates reactively)
            await self.agent.artifacts.connect_directory(DIR_JID)
            await asyncio.sleep(0.3)   # wait for first registry publication

            # ── Yellow pages: by type ─────────────────────────────────────
            doors   = self.agent.artifacts.find_by_type("Door")
            fridges = self.agent.artifacts.find_by_type("Fridge")
            print(f"\n[agent] Doors:   {doors}")
            print(f"[agent] Fridges: {fridges}")

            # ── Yellow pages: by operation ────────────────────────────────
            lockers   = self.agent.artifacts.find_by_op("lock")
            restockers = self.agent.artifacts.find_by_op("restock")
            print(f"[agent] Artifacts with 'lock':    {lockers}")
            print(f"[agent] Artifacts with 'restock': {restockers}")

            # ── Act on discovered artifacts ───────────────────────────────
            for door_jid in doors:
                await self.agent.artifacts.use(door_jid, "lock")

            for fridge_jid in fridges:
                await self.agent.artifacts.use(fridge_jid, "get", "beer")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    directory = DirectoryArtifact(DIR_JID, "1234")
    door      = Door("door@localhost",   "1234", directory_jid=DIR_JID)
    fridge    = Fridge("fridge@localhost", "1234", directory_jid=DIR_JID)
    agent     = SmartAgent("smart@localhost", "1234", asl=None)

    # Directory must start first
    await directory.start()
    await asyncio.sleep(0.3)
    await door.start()
    await fridge.start()
    await agent.start()

    await asyncio.sleep(4)

    await directory.stop()
    await door.stop()
    await fridge.stop()
    await agent.stop()


if __name__ == "__main__":
    spade.run(main())
