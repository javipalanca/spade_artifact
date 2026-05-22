# spade_artifact_ext

Extensión de [`spade_artifact`](https://github.com/javipalanca/spade_artifact) que añade
soporte para **invocación de operaciones** al estilo CArtAgO/JaCaMo y un servicio de
**directorio unificado** (páginas blancas + amarillas) para artefactos y agentes.

No modifica ninguna librería existente: hereda y envuelve mediante el patrón proxy.

---

## Ficheros

```
spade_artifact_ext/
├── __init__.py           ← API pública (imports)
├── artifact_ext.py       ← implementación
├── README.md             ← este fichero
└── examples/
    ├── 01_operation.py   ← @operation con y sin argumentos
    ├── 02_discovery.py   ← páginas blancas: discover() + focus dinámico
    ├── 03_directory.py   ← páginas amarillas: DirectoryArtifact
    ├── 04_ignore.py      ← suscripción dinámica: focus / ignore
    └── 05_agents_directory.py ← directorio unificado: agentes + artefactos
```

---

## Motivación

`spade_artifact` implementa el canal **artefacto → agente** vía PubSub:

```
Artifact.publish()  ──PubSub──►  ArtifactMixin.focus(callback)
```

Esta extensión añade el canal **agente → artefacto** (invocación de operaciones)
y servicios de directorio, completando la simetría:

```
artifacts.focus(jid, cb)    ←  artefacto notifica al agente   (PubSub)
artifacts.use(jid, op, …)   →  agente invoca operación        (<message> XMPP)
```

La asimetría de transporte (PubSub vs. mensaje) es intencional y correcta:
- `publish/focus` es **broadcast** (1 artefacto → N agentes) → PubSub es ideal.
- `use` es **unicast** (1 agente → 1 artefacto) → mensaje XMPP es ideal.

---

## API

### Artefacto

```python
from spade_artifact_ext import OperableArtifact, operation

class Door(OperableArtifact):

    @operation                          # marca el método como invocable
    async def lock(self):
        await self.publish("locked")    # notifica a los suscriptores

    @operation
    async def unlock(self, speed: str = "normal"):
        await self.publish(f"unlocked({speed})")

# Arranque con auto-registro en el directorio (opcional)
door = Door("door@localhost", "1234", directory_jid="directory@localhost")
```

### Agente con capacidades

```python
from spade_artifact_ext import AgentDirectoryMixin, ArtifactActuatorMixin

class RobotAgent(AgentDirectoryMixin, ArtifactActuatorMixin, ArtifactMixin, BDIAgent):
    pass    # toda la lógica en asl o en add_custom_actions

# Capacidades declaradas explícitamente al instanciar
robot = RobotAgent(
    "robot@localhost", "1234", asl="robot.asl",
    directory_jid="directory@localhost",
    capabilities=["deliver", "move", "restock"],
)
```

### Consultas desde cualquier agente

```python
from spade_artifact_ext import ArtifactActuatorMixin

class MyAgent(ArtifactActuatorMixin, ArtifactMixin, BDIAgent):
    async def setup(self):
        await super().setup()

        # ── API existente (sin cambios) ─────────────────────────────────
        await self.artifacts.focus("door@localhost", self.on_door)   # suscribirse
        await self.artifacts.ignore("door@localhost")                 # desuscribirse

        # ── Invocación de operaciones ───────────────────────────────────
        await self.artifacts.use("door@localhost", "lock")            # sin args
        await self.artifacts.use("fridge@localhost", "restock", 5)   # con args

        # ── Páginas blancas (nodos PubSub activos) ──────────────────────
        active = await self.artifacts.discover()   # ["door@...", "fridge@..."]

        # ── Páginas amarillas (requiere connect_directory) ──────────────
        await self.artifacts.connect_directory("directory@localhost")

        todos      = self.artifacts.find()              # todo lo registrado
        agentes    = self.artifacts.find("agent")       # solo agentes
        artefactos = self.artifacts.find("artifact")    # solo artefactos

        puertas    = self.artifacts.find_by_type("Door")    # por clase
        repartos   = self.artifacts.find_by_op("deliver")  # por capacidad
```

### Plataforma

```python
from spade_artifact_ext import DirectoryArtifact

directory = DirectoryArtifact("directory@localhost", "1234")
await directory.start()    # arrancar antes que el resto de entidades
```

---

## Tabla de la API completa

| Método | Dirección | Transporte | Descripción |
|:-------|:----------|:-----------|:------------|
| `Artifact.publish(data)` | art → agentes | PubSub | Notifica estado a suscriptores |
| `artifacts.focus(jid, cb)` | art → agente | PubSub | Suscribirse a un artefacto |
| `artifacts.ignore(jid)` | — | PubSub | Cancelar suscripción |
| `artifacts.use(jid, op, *args)` | agente → art | `<message>` | Invocar operación |
| `artifacts.discover()` | — | PubSub disco | Listar nodos PubSub activos (white pages) |
| `artifacts.connect_directory(jid)` | — | PubSub | Suscribirse al DirectoryArtifact |
| `artifacts.find(kind=None)` | local | — | Todas las entidades, o filtradas por `"agent"`/`"artifact"` |
| `artifacts.find_by_type(t)` | local | — | Buscar por nombre de clase |
| `artifacts.find_by_op(op)` | local | — | Buscar por operación/capacidad |

---

## Formato del registro del directorio

Cada entrada en el `DirectoryArtifact` tiene la forma:

```python
{
  "door@localhost":  {"kind": "artifact", "type": "Door",      "operations": ["lock", "unlock"]},
  "fridge@localhost":{"kind": "artifact", "type": "Fridge",    "operations": ["get", "restock"]},
  "robot@localhost": {"kind": "agent",    "type": "RobotAgent","operations": ["deliver", "move"]},
  "owner@localhost": {"kind": "agent",    "type": "OwnerAgent","operations": ["request", "pay"]},
}
```

El campo `kind` permite distinguir si una entrada es un agente autónomo o un artefacto
pasivo. Los artefactos se auto-registran por introspección de `@operation`; los agentes
declaran sus capacidades explícitamente al instanciarlos.

---

## Diferencia entre páginas blancas y amarillas

| Servicio | Método | Pregunta que responde |
|:---------|:-------|:----------------------|
| **Páginas blancas** | `discover()` | ¿Qué nodos PubSub están activos? |
| **Páginas amarillas** | `find()`, `find_by_type()`, `find_by_op()` | ¿Quién sabe hacer X? ¿Quién es de tipo Y? |

`discover()` consulta el servidor PubSub directamente (solo artefactos, no agentes).
`find*()` consulta la caché local del `DirectoryArtifact`, que incluye tanto artefactos como agentes.

---

## Equivalencias con CArtAgO / JaCaMo

| CArtAgO | spade_artifact_ext |
|:--------|:-------------------|
| `@OPERATION` | `@operation` |
| `use_artifact(id, op, args)` | `artifacts.use(jid, op, *args)` |
| `ObservableProperty` | `self.publish(value)` |
| `WorkspaceArtifact.lookupArtifact` | `artifacts.find()` / `find_by_type()` |
| `makeArtifact / disposeArtifact` | `await artifact.start()` / `.stop()` |

---

## Prerrequisitos

El servidor XMPP local (`spade run`) debe estar en marcha antes de ejecutar cualquier ejemplo.
Aplicar también los parches de `../spade_fixes/` al entorno virtual.

```bash
# Arrancar el servidor
uv run spade run --purge

# Ejecutar un ejemplo (desde la raíz del proyecto)
uv run python spade_artifact_ext/examples/01_operation.py
```

---

## Ejemplos

### 01 – Invocación de operaciones

**Artefacto:** `CounterArtifact` con `@operation increment(amount)` y `@operation reset()`.  
**Agente:** `OperatorAgent` invoca `artifacts.use("counter@...", "increment", 5)`.  
**Demuestra:** invocación con y sin argumentos, observación vía `focus`.

### 02 – Páginas blancas: `discover()`

**Artefactos:** tres `SensorArtifact` (temp, humidity, pressure) que arrancan independientemente.  
**Agente:** `ExplorerAgent` llama `artifacts.discover()` un segundo después de arrancar,
filtra los sensores por JID y se suscribe dinámicamente a todos.  
**Demuestra:** descubrimiento en tiempo de ejecución sin conocer los JIDs de antemano.

### 03 – Páginas amarillas: `DirectoryArtifact`

**Artefactos:** `Door` (ops: `lock`, `unlock`) y `Fridge` (ops: `get`, `restock`),
ambos con `directory_jid` para auto-registro.  
**Agente:** `SmartAgent` llama `connect_directory()` y luego:
- `find_by_type("Door")` → JIDs de todas las puertas
- `find_by_op("restock")` → quién sabe reabastecer  

**Demuestra:** registro automático por introspección y consulta por tipo / capacidad.

### 04 – Suscripción dinámica: `focus` / `ignore`

**Artefactos:** `TickerArtifact` (publica cada 0.5s) y `CounterArtifact`.  
**Agente:** `MonitorAgent` ejecuta una secuencia temporal:
1. `focus(ticker)` → recibe ticks durante 2 s
2. `ignore(ticker)` → deja de recibir
3. `focus(counter)` → recibe conteos durante 1 s
4. `ignore(counter)` → finaliza sin suscripciones activas  

**Demuestra:** que `focus`/`ignore` son completamente dinámicos y pueden invocarse
en cualquier punto del ciclo de vida del agente, no solo en `setup()`.

### 05 – Directorio unificado: agentes + artefactos

**Artefactos:** `Door`, `Fridge` (auto-registro vía `directory_jid`).  
**Agentes:** `RobotAgent`, `OwnerAgent` (registro con `AgentDirectoryMixin` y `capabilities`).  
**Inspector:** consulta el directorio y muestra el desglose completo:

```
All registered : ["door@...", "fridge@...", "robot@...", "owner@..."]
Agents         : ["robot@localhost", "owner@localhost"]
Artifacts      : ["door@localhost",  "fridge@localhost"]
Can lock       : ["door@localhost"]
Can deliver    : ["robot@localhost"]
```

**Demuestra:** el directorio como servicio unificado para todo el sistema multiagente,
con distinción por `kind` y consultas por tipo/capacidad que funcionan igual para
agentes y artefactos.
