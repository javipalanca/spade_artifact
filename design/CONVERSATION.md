# Conversación: diseño de spade_artifact_ext
*22 de abril de 2026*

---

## Contexto inicial

El proyecto ya tenía funcionando `spade_artifact` con un sistema de PubSub para que
los artefactos notifiquen a los agentes. El objetivo era añadir el canal inverso:
que los agentes puedan invocar operaciones en los artefactos.

---

## Q&A

---

**¿Con este esquema se puede hacer orquestación y coreografía de artefactos?**

Sí, y de forma natural. El esquema permite los dos patrones:

**Orquestación**: un agente central controla la secuencia explícitamente combinando
`focus()` + `use()`. El robot decide el orden y coordina todos los artefactos paso
a paso. Alta trazabilidad pero el orquestador es cuello de botella.

**Coreografía**: los artefactos se suscriben entre sí y reaccionan autónomamente.
Un `OperableArtifact` puede llamar a `self.pubsub.subscribe()` y `self.send()`,
actuando como observador y actuador de otros artefactos. No hay coordinador;
el comportamiento emerge de las reglas locales.

---

**Ahora los agentes se registran en el inicio. ¿Hay algo que impida registrarse
con un artefacto en cualquier momento del ciclo de vida?**

No hay nada que lo impida. Es una decisión de diseño puramente convencional.
`focus()`, `ignore()` y `use()` son llamadas XMPP asíncronas que el servidor
procesa independientemente del momento. Un agente puede llamarlas desde cualquier
`Behaviour`, en cualquier punto de su ejecución.

Patrones que esto habilita:
- Suscripción condicional (conectar solo al artefacto necesario)
- Migración de contexto (cambiar de artefactos según la zona)
- Roles dinámicos (asumir/abandonar capacidades en tiempo real)

---

**¿`ignore()` está implementado en spade_artifacts?**

Sí, ya existe en `spade_artifact/agent.py`:

```python
async def ignore(self, artifact_jid):
    await self.agent.pubsub.unsubscribe(self.agent.pubsub_server, str(artifact_jid))
    if artifact_jid in self.focus_callbacks:
        del self.focus_callbacks[artifact_jid]
```

Cancela la suscripción PubSub y elimina el callback. Listo para usar.

---

**¿XMPP tiene alguna manera de identificar qué artefactos tiene registrados?**

Sí. `spade_pubsub` ya tiene `get_nodes()` (XEP-0030, Service Discovery) que lista
todos los nodos del servidor PubSub. Como cada artefacto crea un nodo con su JID,
listar nodos = listar artefactos activos. Se añadió `artifacts.discover()` como
wrapper de esto.

---

**La función de descubrimiento sería páginas blancas ¿no? ¿y quedaría
pendiente el de páginas amarillas?**

Exacto:
- **Páginas blancas** = `discover()`: "¿qué artefactos existen?" → devuelve JIDs
- **Páginas amarillas** = "¿qué artefacto sabe hacer X?" → requiere un registro
  de capacidades

Para las amarillas, la información ya está disponible por introspección Python:
un `OperableArtifact` puede auto-publicitar sus métodos `@operation` al arrancar.
Se diseñó el `DirectoryArtifact` para esto.

---

**¿Tiene SPADE algo equivalente para los agentes?**

No. SPADE no tiene un equivalente nativo a FIPA AMS/DF.

Lo que sí tiene a través de XMPP:
- **Presencia**: `self.presence.get_contacts()` — solo agentes conocidos (con
  subscripción de presencia previa), no un directorio global.

Lo que no tiene:
- No hay DF (Directory Facilitator).  La comunidad SPADE implementa un "agente directorio"
  a mano, lo que es menos elegante.

Comparativa:

| Servicio | JADE | SPADE |
|:---------|:-----|:------|
| AMS (white pages) | Integrado | Servidor XMPP (solo auth) |
| DF (yellow pages) | Integrado | ❌ Manual |
| Presencia online | Parcial | ✅ XMPP Presence |

---

**¿Esta funcionalidad tiene más sentido como artefacto que como agente?**

Completamente. Argumentos:

1. **Sin intencionalidad**: un directorio no tiene metas ni comportamiento autónomo.
   Los artefactos son recursos pasivos; los agentes tienen ciclo BDI. El directorio
   encaja semánticamente como artefacto.

2. **Acceso como operación**: interactuar con un agente-DF requiere mensajes ACL
   (FIPA-DF Request, Search...). Con un artefacto-directorio se invoca `register()`
   y `lookup()` directamente. Más simple.

3. **Precedente en JaCaMo**: las operaciones de gestión del entorno (`makeArtifact`,
   `lookupArtifact`, `disposeArtifact`) están en el `WorkspaceArtifact`, un
   artefacto de plataforma, no un agente especial.

4. **Error histórico de FIPA**: la decisión de modelar el DF como agente especial
   fue cuestionada en la literatura. Mezcla infraestructura con autonomía.

5. **Concurrencia**: los artefactos están diseñados para ser recursos compartidos
   y accedidos concurrentemente. Un agente-DF gestiona esto manualmente.

---

**¿Los agentes SPADE pueden usar este servicio para registrar sus nombres
y funcionalidades?**

Sí. El `DirectoryArtifact` no distingue quién envía el mensaje de `register`.
Un agente con `ArtifactActuatorMixin` puede llamar directamente:

```python
await self.artifacts.use(
    "directory@localhost", "register",
    str(self.jid), "RobotAgent", json.dumps(["deliver", "move"])
)
```

Diferencia con los artefactos: éstos se auto-registran por introspección de `@operation`.
Los agentes registran sus capacidades explícitamente (son un contrato semántico, no
un conjunto de decoradores).

Se añadió `AgentDirectoryMixin` para hacer esto transparente:

```python
robot = RobotAgent(
    "robot@localhost", "1234", asl="robot.asl",
    directory_jid="directory@localhost",
    capabilities=["deliver", "move", "restock"],
)
```

---

**¿Cómo se sabe si lo que devuelve el directorio es un agente o un artefacto?**

Se añadió un campo `kind` al registro con valor `"artifact"` o `"agent"`.
El campo `type` ya estaba ocupado por el nombre de clase.

Cada entrada del directorio:
```python
{
  "door@localhost":  {"kind": "artifact", "type": "Door",      "operations": ["lock","unlock"]},
  "robot@localhost": {"kind": "agent",    "type": "RobotAgent","operations": ["deliver","move"]},
}
```

Y se sustituyeron `find_agents()` / `find_artifacts()` por un único `find(kind=None)`:

```python
find()              # todo lo registrado
find("agent")       # solo agentes
find("artifact")    # solo artefactos
find_by_type("Door")        # por clase
find_by_op("deliver")       # por capacidad
```

---

**Nota sobre el nombre `kind`**

El usuario expresó duda sobre si `kind` es el término más adecuado.
`type` no se puede usar (ya ocupado por el nombre de clase).
Alternativas valoradas: `nature`, `category`, `entity`.
Se dejó como `kind` por ahora (fácil de renombrar sin cambiar lógica).

---

## Resultado final

```
spade_artifact_ext/
├── __init__.py           ← API pública
├── artifact_ext.py       ← implementación
├── README.md             ← referencia técnica
├── DESIGN.md             ← fundamentos conceptuales
├── CONVERSATION.md       ← este fichero
└── examples/
    ├── 01_operation.py        @operation con/sin argumentos
    ├── 02_discovery.py        páginas blancas: discover()
    ├── 03_directory.py        páginas amarillas: DirectoryArtifact
    ├── 04_ignore.py           suscripción dinámica: focus/ignore
    └── 05_agents_directory.py directorio unificado agentes + artefactos
```

### API completa

| Método | Quién lo usa | Descripción |
|:-------|:------------|:------------|
| `@operation` | Artefacto | Decora métodos como invocables por agentes |
| `OperableArtifact` | Artefacto | Base class con dispatcher automático |
| `artifacts.focus(jid, cb)` | Agente | Suscribirse a un artefacto (existente) |
| `artifacts.ignore(jid)` | Agente | Cancelar suscripción (existente) |
| `artifacts.use(jid, op, *args)` | Agente | Invocar operación en artefacto |
| `artifacts.discover()` | Agente | Listar artefactos activos (PubSub) |
| `artifacts.connect_directory(jid)` | Agente | Suscribirse al DirectoryArtifact |
| `artifacts.find(kind=None)` | Agente | Todo / solo agentes / solo artefactos |
| `artifacts.find_by_type(t)` | Agente | Buscar por nombre de clase |
| `artifacts.find_by_op(op)` | Agente | Buscar por operación/capacidad |
| `DirectoryArtifact` | Plataforma | Artefacto de directorio blancas+amarillas |
| `AgentDirectoryMixin` | Agente | Auto-registro del agente en el directorio |
