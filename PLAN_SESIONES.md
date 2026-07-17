# Plan de implementación — Mejoras al historial de sesiones (Pendientes 1–3)

> Creado 2026-07-16. Cubre tres pendientes de bajo/medio riesgo. Dos comparten la
> capa de persistencia de sesiones (`sessions.py` + restauración en frontend); el
> tercero es aislado (solo frontend) y puede hacerse en paralelo.

## Hallazgos del diagnóstico (código leído)

- La tabla `sessions` **ya tiene columna `title`** (`backend/app/services/memory/sessions.py:33`),
  pero el orquestador crea la sesión en la primera consulta (`orchestrator.py:91`) con
  `create_session(db_name=...)` **sin título**, dejando el default `"Session YYYY-MM-DD"`.
  Ese es el único motivo por el que el historial no muestra la primera pregunta.
- **KI-1 está casi resuelto en código sin que el doc lo refleje**: `loadFromSession`
  (`queryStore.ts:126`) ya reconstruye los mensajes del bot, `MessageBubble` ya pasa
  `restored` a `AnswerPanel`, y `AnswerPanel` ya tiene rama `restored` ("The lesson" +
  SQL + tabla). El backend **sí persiste** los turnos del asistente (`orchestrator.py:114`
  y `:272`). Falta verificar por qué en la práctica no renderiza — probablemente sesiones
  viejas en `data/sessions.db` anteriores a esa persistencia, o desajuste de tipos en
  `SessionDetail`.

---

## Pendiente 1 — Título de sesión = primera pregunta *(el más simple)*

Backend, un solo punto de cambio.

**1.1** En `backend/app/services/memory/sessions.py`, añadir helper:

```python
def set_title_if_default(session_id: str, title: str) -> None:
    """Set the session title only if it's still the auto-generated default."""
    clean = title.strip()[:60]
    with _conn() as con:
        con.execute(
            "UPDATE sessions SET title = ? "
            "WHERE session_id = ? AND (title IS NULL OR title = '' OR title LIKE 'Session %')",
            (clean, session_id),
        )
```

**1.2** En `orchestrator.py`, justo después de `append_turn(sid, "user", query)` (línea 93),
llamar `set_title_if_default(sid, query)`. Importar el helper junto a `append_turn`/`create_session`.

- Fija el título con la primera pregunta real, tanto si la sesión nació en `/query`
  como vía `POST /session`.
- Las preguntas siguientes no lo sobreescriben (la cláusula `LIKE 'Session %'` solo
  matchea el default).

**Frontend:** sin cambios (`SessionLibrary.tsx:60` ya pinta `s.title`).

**Verificación:** correr una consulta nueva, abrir `SessionLibrary`, confirmar que el
título es la pregunta truncada a 60 caracteres.

---

## Pendiente 2 — Frases didácticas de espera *(simple, aislado, solo frontend)*

Independiente de la capa de sesiones — se puede hacer en paralelo.

**2.1** Nuevo componente `frontend/src/components/WaitingPhrases.tsx`:
- Arreglo de ~10–15 datos cortos sobre bases de datos / SQL.
- `setInterval` rotando cada ~4 s (limpiar en `useEffect` cleanup).
- Montado condicionalmente cuando `useQueryStore(s => s.isWaiting)` sea `true`.

**2.2** Colocarlo junto al `AgentProgress` en el feed de chat.

**2.3** Estilos vía CSS Module con los tokens existentes (`styles/tokens.css`).

- **Sin estimación de tiempo restante** (decisión ya tomada en MASTERPLAN §Pending backlog).

**Verificación:** lanzar una consulta y ver las frases rotar mientras corre el
pipeline, y desaparecer al llegar la respuesta.

---

## Pendiente 3 — KI-1: restaurar respuestas, no solo preguntas *(medio; reproducir antes de tocar)*

Primero reproducir para localizar la capa exacta, en este orden:

**3.1 Datos frescos** — correr una consulta nueva completa, luego `GET /session/{id}` y
confirmar en el JSON que existe el turno `role:"assistant"` con `content`, `sql` y
`rows_json` poblados. Si las sesiones viejas de `data/sessions.db` fallan pero las nuevas
no, la causa era persistencia previa: documentar y limpiar la DB (self-heal ya soportado).

**3.2 Contrato de tipos** — verificar que `SessionDetail`/`turns` en
`frontend/src/services/api.ts` incluye `turn_id`, `sql` y `rows_json` (los usa
`loadFromSession`). Si falta alguno, la reconstrucción produce `undefined` y la
tabla/SQL no aparece: corregir el tipo y el parseo.

**3.3 Render** — con datos y tipos correctos, confirmar que `AnswerPanel` rama `restored`
muestra "The lesson" + SQL + tabla. Si el turno del asistente no guardó SQL (caso
meta-pregunta), cae en la rama de clarificación y muestra el `teaching_summary`
(comportamiento correcto).

**Cierre:**
- Quitar el `TODO(KI-1)` de `queryStore.ts:122`.
- Añadir dos pruebas offline en `tests/`: (a) que un `/query` completo persiste un turno
  de asistente con `sql`+`rows`; (b) que la reconstrucción de `loadFromSession` produce
  los mensajes del bot esperados.
- Marcar KI-1 como resuelto en `DAY2_PLAN.md` §Known Issues.

---

## Secuencia sugerida

- **1 y 3 juntos** — misma capa de sesiones, misma prueba manual: crear sesión →
  restaurar → verificar título y respuestas.
- **2 en paralelo** — independiente.
- Riesgo bajo en los tres; la única incógnita es el paso de reproducción de #3 (3.1).

## Archivos tocados (resumen)

| Pendiente | Archivos |
|---|---|
| 1 | `backend/app/services/memory/sessions.py`, `backend/app/services/orchestrator.py` |
| 2 | `frontend/src/components/WaitingPhrases.tsx` (nuevo) + su CSS Module, punto de montaje del feed de chat |
| 3 | `frontend/src/services/api.ts` (tipos, si aplica), `frontend/src/stores/queryStore.ts` (quitar TODO), `tests/` (2 pruebas), `DAY2_PLAN.md` |
