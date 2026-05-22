"""
Example 01 – @operation invocation
===================================
Demonstrates how an agent invokes operations on an OperableArtifact
using self.artifacts.use(), both with and without arguments.

Scenario
────────
  Counter artifact:  exposes increment(amount) and reset()
  Watcher  agent:    observes the counter via focus()
  Operator agent:    drives the counter via artifacts.use()

Run
───
  cd /Users/mrebollo/devel/ain25-26/lab/p5_artifact
  uv run python spade_artifact_ext/examples/01_operation.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import spade
from spade_artifact import ArtifactMixin
from spade_bdi.bdi import BDIAgent
from spade_artifact_ext import operation, OperableArtifact, ArtifactActuatorMixin


# ── Artifact ──────────────────────────────────────────────────────────────────

class CounterArtifact(OperableArtifact):
    """A simple counter artifact with two operations."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.count = 0

    @operation
    async def increment(self, amount: int = 1):
        """Increment the counter by `amount` (default 1)."""
        self.count += amount
        print(f"[counter] count = {self.count}")
        await self.publish(f"count({self.count})")

    @operation
    async def reset(self):
        """Reset the counter to zero."""
        self.count = 0
        print(f"[counter] reset → 0")
        await self.publish(f"count(0)")


# ── Agents ────────────────────────────────────────────────────────────────────

class WatcherAgent(ArtifactActuatorMixin, ArtifactMixin, BDIAgent):
    """Observes the counter and prints every change."""

    async def setup(self):
        await super().setup()
        self.presence.subscribe("counter@localhost")
        await self.artifacts.focus("counter@localhost", self.on_counter)
        print(f"[watcher] subscribed to counter")

    def on_counter(self, jid, payload):
        print(f"[watcher] perceived: {payload}")


class OperatorAgent(ArtifactActuatorMixin, ArtifactMixin, BDIAgent):
    """Drives the counter artifact via use()."""

    async def setup(self):
        await super().setup()
        self.presence.subscribe("counter@localhost")
        # Schedule the demo sequence as a background behaviour
        self.add_behaviour(self.DemoSequence())

    class DemoSequence(spade.behaviour.OneShotBehaviour):
        async def run(self):
            await asyncio.sleep(0.5)   # wait for all agents to connect
            print("\n[operator] increment by 1 (default)")
            await self.agent.artifacts.use("counter@localhost", "increment")
            await asyncio.sleep(0.3)

            print("[operator] increment by 5")
            await self.agent.artifacts.use("counter@localhost", "increment", 5)
            await asyncio.sleep(0.3)

            print("[operator] reset")
            await self.agent.artifacts.use("counter@localhost", "reset")
            await asyncio.sleep(0.3)

            print("[operator] increment by 3")
            await self.agent.artifacts.use("counter@localhost", "increment", 3)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    counter  = CounterArtifact("counter@localhost", "1234")
    watcher  = WatcherAgent("watcher@localhost",  "1234", asl=None)
    operator = OperatorAgent("operator@localhost", "1234", asl=None)

    await counter.start()
    await watcher.start()
    await operator.start()

    await asyncio.sleep(3)

    print("\n[main] final counter value:", counter.count)
    await counter.stop()
    await watcher.stop()
    await operator.stop()


if __name__ == "__main__":
    spade.run(main())
