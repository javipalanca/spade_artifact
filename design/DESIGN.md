# Notas de diseño: spade_artifact_ext

Decisiones de diseño y fundamentos conceptuales del paquete.

---

## 1. Canal simétrico: focus ↔ use

`spade_artifact` solo implementa el canal **artefacto → agente** (PubSub).
La extensión añade el canal **agente → artefacto** (`<message>` XMPP), completando
la simetría del modelo CArtAgO:

```
artifacts.focus(jid, cb)    ←  artefacto notifica al agente   (PubSub, broadcast)
artifacts.use(jid, op, …)   →  agente invoca operación        (<message>, unicast)
```

La **asimetría de transporte** es intencional:
- `publish/focus` es 1→N (un artefacto, N agentes suscritos) → PubSub ideal.
- `use` es 1→1 (un agente, un artefacto específico) → mensaje XMPP ideal.

---

## 2. Patrón Proxy para extender self.artifacts

No se modifica el código de `spade_artifact`. En su lugar, `ArtifactActuatorMixin`
envuelve el `ArtifactComponent` existente con `_ArtifactComponentProxy`, que:

- Delega **todas** las llamadas existentes (`focus`, `ignore`, ...) al componente original.
- Añade `use`, `discover`, `connect_directory`, `find`, `find_by_type`, `find_by_op`.

Esto permite actualizar `spade_artifact` sin romper la extensión.

---

## 3. Orquestación vs Coreografía

Con este esquema ambos patrones son posibles:

### Orquestación
Un agente central controla la secuencia explícitamente:
```python
await self.artifacts.use("fridge@localhost", "open")
# espera callback
await self.artifacts.use("fridge@localhost", "get", "beer")
await self.artifacts.use("robot@localhost", "move_to", "owner")
```
- Alta trazabilidad, fácil de depurar.
- El orquestador es cuello de botella y punto de fallo.

### Coreografía
Cada artefacto reacciona a eventos de otros artefactos directamente.
Un `OperableArtifact` puede suscribirse a otro con `self.pubsub.subscribe()`
y enviarle mensajes con `self.send()`. No hay coordinador central; el
comportamiento emerge de las reglas locales.
- Alta escalabilidad, bajo acoplamiento.
- Comportamiento emergente, más difícil de depurar.

---

## 4. Dinamismo de las suscripciones

`focus()` e `ignore()` son llamadas XMPP asíncronas que pueden ejecutarse
**en cualquier momento del ciclo de vida del agente**, no solo en `setup()`.
Esto permite:

- Suscripción condicional (el agente conecta solo al artefacto que necesita).
- Migración de contexto (cambia de artefactos al moverse entre zonas).
- Roles dinámicos (asume/abandona capacidades en tiempo de ejecución).

---

## 5. Descubrimiento: páginas blancas vs. amarillas

| Servicio | Método | Pregunta | Mecanismo |
|:---------|:-------|:---------|:----------|
| **Páginas blancas** | `discover()` | ¿Qué artefactos están vivos? | Lista nodos PubSub (XEP-0030) |
| **Páginas amarillas** | `find*()` | ¿Quién sabe hacer X? | Caché local del `DirectoryArtifact` |

`discover()` solo muestra artefactos (crean nodos PubSub).
`find()` muestra artefactos **y agentes** registrados en el `DirectoryArtifact`.

---

## 6. El directorio como artefacto de plataforma

El `DirectoryArtifact` es un artefacto (no un agente) porque:

1. **No tiene intencionalidad**: solo almacena y devuelve información. Los agentes
   tienen metas y comportamiento autónomo; los artefactos son recursos pasivos.
2. **Acceso como operación**: los clientes invocan `register()` / `unregister()`,
   no envían mensajes ACL. Más simple y semánticamente correcto.
3. **Precedente en JaCaMo**: el `WorkspaceArtifact` de JaCaMo implementa
   `lookupArtifact`, `makeArtifact`, `disposeArtifact` exactamente así.
4. **Error histórico de FIPA**: el DF (Directory Facilitator) FIPA es un agente
   especial, decisión cuestionada en la literatura porque mezcla infraestructura
   con autonomía. Un servicio de directorio no necesita ciclo BDI.
5. **Estado compartido sin carreras de condición**: los artefactos están diseñados
   para ser recursos concurrentes; un agente-DF necesitaría gestionar esto a mano.

---

## 7. Diferencia con JADE/FIPA

| FIPA/JADE | spade_artifact_ext |
|:----------|:-------------------|
| AMS (autenticación + white pages) | Servidor XMPP + `discover()` |
| DF (yellow pages) | `DirectoryArtifact` |
| `DFService.register()` | `OperableArtifact` (auto, por introspección) |
| `DFService.register()` agentes | `AgentDirectoryMixin` (manual, declarativo) |
| `DFService.search()` | `find()`, `find_by_type()`, `find_by_op()` |

SPADE no tiene DF nativo. Esta extensión lo suple de forma coherente
con la arquitectura de artefactos.

---

## 8. Auto-registro: artefactos vs. agentes

| | Artefactos (`OperableArtifact`) | Agentes (`AgentDirectoryMixin`) |
|:--|:--|:--|
| Registro | **Automático** por introspección de `@operation` | **Manual**: lista de `capabilities` al instanciar |
| Razón | Los `@operation` son una interfaz bien definida | Las capacidades de un agente son un contrato semántico, no un conjunto de decoradores |

---

## 9. Campo `kind` en el registro

Cada entrada del directorio incluye:
```python
{"kind": "artifact"|"agent", "type": NombreDeClase, "operations": [...]}
```

- `kind` permite distinguir el tipo de entidad. La palabra fue cuestionada
  (`type` está ocupado por el nombre de clase; otras opciones: `nature`, `category`).
- Es un metadato de registro, fácil de cambiar sin afectar la lógica.

---

## 10. Parches necesarios en librerías (spade_fixes/)

Para que `spade_artifact` funcione correctamente con `pyjabber`, se aplicaron
tres parches (ver `../spade_fixes/`):

| Fichero | Bug corregido |
|:--------|:-------------|
| `pyjabber/xep_0060.py` | Payload vacío: evaluación truthy incorrecta sobre ElementTree |
| `spade_pubsub/pubsub.py` | Sin `item_id`: el servidor descartaba el payload |
| `spade_artifact/agent.py` | `AttributeError`: acceso a `.text` de un elemento None |
