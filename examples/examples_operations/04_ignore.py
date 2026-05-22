"""
Example 04 – Dynamic focus / ignore
=====================================
Demonstrates that focus() and ignore() can be called at any point in the
agent's lifecycle (not only in setup()), enabling dynamic subscription
management.

Scenario
────────
  Ticker artifact: publishes a tick every 0.5 s
  MonitorAgent:
    t=0.0  → focus: starts receiving ticks
    t=2.0  → ignore: stops receiving ticks (silently drops the rest)
    t=3.5  → focus again on a different artifact (counter)
    t=4.5  → ignore counter

Run
───
  cd /Users/mrebollo/devel/ain25-26/lab/p5_artifact
  uv run python spade_artifact_ext/examples/04_ignore.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import spade
from spade_artifact import ArtifactMixin
from spade_bdi.bdi import BDIAgent
from spade_artifact_ext import operation, OperableArtifact, ArtifactActuatorMixin


# ── Artifacts ─────────────────────────────────────────────────────────────────

class TickerArtifact(OperableArtifact):
    """Publishes a tick every interval_s seconds."""

    def __init__(self, *args, interval_s: float = 0.5, **kwargs):
        super().__init__(*args, **kwargs)
        self.interval = interval_s
        self.tick = 0

    async def run(self):
        while True:
            self.tick += 1
            await self.publish(f"tick({self.tick})")
            # Also dispatch any incoming operations
            await self._process_operations()
            await asyncio.sleep(self.interval)


class CounterArtifact(OperableArtifact):
    """Simple counter, incremented via operation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.count = 0

    @operation
    async def increment(self):
        self.count += 1
        await self.publish(f"count({self.count})")
        print(f"[counter] count = {self.count}")


# ── Agent ─────────────────────────────────────────────────────────────────────

class MonitorAgent(ArtifactActuatorMixin, ArtifactMixin, BDIAgent):

    async def setup(self):
        await super().setup()
        self.presence.subscribe("ticker@localhost")
        self.presence.subscribe("counter@localhost")
        self.add_behaviour(self.DynamicSubDemo())

    def on_tick(self, jid, payload):
        print(f"[monitor] ← tick: {payload}")

    def on_count(self, jid, payload):
        print(f"[monitor] ← count: {payload}")

    class DynamicSubDemo(spade.behaviour.OneShotBehaviour):
        async def run(self):
            agent = self.agent

            # t=0 – subscribe to ticker
            print("\n[monitor] t=0  → focus(ticker)")
            await agent.artifacts.focus("ticker@localhost", agent.on_tick)

            await asyncio.sleep(2.0)

            # t=2 – unsubscribe from ticker
            print("\n[monitor] t=2  → ignore(ticker)")
            await agent.artifacts.ignore("ticker@localhost")
            print("[monitor] no more tick events will be received")

            await asyncio.sleep(1.5)

            # t=3.5 – subscribe to counter and trigger some increments
            print("\n[monitor] t=3.5 → focus(counter)")
            await agent.artifacts.focus("counter@localhost", agent.on_count)
            for _ in range(3):
                await agent.artifacts.use("counter@localhost", "increment")
                await asyncio.sleep(0.3)

            await asyncio.sleep(0.5)

            # t=4.5 – unsubscribe from counter
            print("\n[monitor] t=4.5 → ignore(counter)")
            await agent.artifacts.ignore("counter@localhost")
            print("[monitor] done — no more subscriptions active")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    ticker  = TickerArtifact("ticker@localhost",  "1234", interval_s=0.5)
    counter = CounterArtifact("counter@localhost", "1234")
    monitor = MonitorAgent("monitor@localhost", "1234", asl=None)

    await ticker.start()
    await counter.start()
    await monitor.start()

    await asyncio.sleep(6)

    await ticker.stop()
    await counter.stop()
    await monitor.stop()


if __name__ == "__main__":
    spade.run(main())
