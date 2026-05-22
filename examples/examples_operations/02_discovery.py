"""
Example 02 – White pages: artifacts.discover()
===============================================
Demonstrates how an agent discovers which artifacts are currently active
on the PubSub server using artifacts.discover(), then subscribes to them.

Scenario
────────
  Three sensor artifacts (temp, humidity, pressure) start independently.
  An ExplorerAgent wakes up, discovers them and subscribes to all of them
  dynamically — without knowing their JIDs in advance.

Run
───
  cd /Users/mrebollo/devel/ain25-26/lab/p5_artifact
  uv run python spade_artifact_ext/examples/02_discovery.py
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

class SensorArtifact(OperableArtifact):
    """Generic sensor that publishes a reading on demand."""

    def __init__(self, *args, sensor_name: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.sensor_name = sensor_name
        self.reading = 0.0

    @operation
    async def read(self):
        """Simulate a new sensor reading and publish it."""
        import random
        self.reading = round(random.uniform(10, 99), 1)
        await self.publish(f"{self.sensor_name}({self.reading})")
        print(f"[{self.sensor_name}] reading = {self.reading}")


# ── Agent ─────────────────────────────────────────────────────────────────────

class ExplorerAgent(ArtifactActuatorMixin, ArtifactMixin, BDIAgent):
    """Discovers active artifacts at runtime and subscribes to all of them."""

    async def setup(self):
        await super().setup()
        self.add_behaviour(self.DiscoverAndSubscribe())

    class DiscoverAndSubscribe(spade.behaviour.OneShotBehaviour):
        async def run(self):
            await asyncio.sleep(1.0)   # give artifacts time to register their nodes

            # ── White pages ───────────────────────────────────────────────
            active = await self.agent.artifacts.discover()
            # Filter out non-sensor nodes (e.g. the agent's own node if any)
            sensors = [j for j in active if "sensor" in j]
            print(f"\n[explorer] discovered sensors: {sensors}")

            # Subscribe to all discovered sensors
            for jid in sensors:
                self.agent.presence.subscribe(jid)
                await self.agent.artifacts.focus(jid, self.agent.on_sensor)
                print(f"[explorer] subscribed to {jid}")

            # Trigger a reading from each discovered sensor
            await asyncio.sleep(0.3)
            for jid in sensors:
                await self.agent.artifacts.use(jid, "read")

    def on_sensor(self, jid, payload):
        print(f"[explorer] data from {jid}: {payload}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    temp     = SensorArtifact("temp_sensor@localhost",     "1234", sensor_name="temp")
    humidity = SensorArtifact("humidity_sensor@localhost", "1234", sensor_name="humidity")
    pressure = SensorArtifact("pressure_sensor@localhost", "1234", sensor_name="pressure")
    explorer = ExplorerAgent("explorer@localhost", "1234", asl=None)

    await temp.start()
    await humidity.start()
    await pressure.start()
    await explorer.start()

    await asyncio.sleep(4)

    await temp.stop()
    await humidity.stop()
    await pressure.stop()
    await explorer.stop()


if __name__ == "__main__":
    spade.run(main())
