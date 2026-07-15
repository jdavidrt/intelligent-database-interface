IDI — Interfaz Inteligente de Bases de Datos

Trabajo de Grado — Ingeniería de Sistemas y Computación
Universidad Nacional de Colombia
Autor: Juan David Ramírez Torres (jdramirezt@unal.edu.co)
Período: 2026-1S (Febrero 2 – Mayo 30, 2026)

> **[ESQUELETO / DEMO — v2]** Armazón estructural para el Capítulo 3. La v2 alinea el capítulo con la actualización del Capítulo 1 (propósito didáctico como identidad principal del proyecto; 62 RF con 7 requerimientos didácticos transversales; auto-corrección silenciosa por UC-06), incorpora el trabajo de endurecimiento del Día 4 ya comprometido (salvaguarda de filtrado de consultas, commit `8cd337b`, 2026-07-06) y añade una sección de estado del requerimiento didáctico por módulo (3.11). Las secciones `[PENDIENTE]` requieren redacción, capturas de pantalla o evidencia de ejecución que aún no se han producido. El contenido no marcado refleja trabajo ya completado y verificable en el repositorio (Días 1–4 del plan de desarrollo, per `CLAUDE.md` e historial de commits).


ÍNDICE

Capítulo 3: Desarrollo de la Solución
    3.1. Adquisición de Contexto: Context Manager Agent y FileConnector
    3.2. Comprensión de Consultas, Clarificación y Salvaguarda de Filtrado
    3.3. Generador SQL
    3.4. Agente de Verificación
    3.5. Motor de Visualización
    3.6. Gestor de Sesiones
    3.7. Orquestador Multi-Agente
    3.8. Registro de Instrucciones y Disciplina de Hot-Swap
    3.9. Reconstrucción del Frontend
    3.10. Datos Sintéticos y Preparación para Fine-Tuning LoRA (Diferido)
    3.11. Estado del Requerimiento Didáctico Transversal por Módulo
    3.12. Estado de Avance y Problemas Conocidos
    3.13. Conclusiones del Capítulo
    3.14. Recomendaciones


────────────────────────────────────────────────────────────────────────

CAPÍTULO 3: DESARROLLO DE LA SOLUCIÓN

Este capítulo desarrolla el tercer objetivo específico (OE3): implementar los siete módulos centrales de IDI con generación de datos sintéticos de entrenamiento, pipelines de fine-tuning, gestión de flujo conversacional y componentes de interfaz de usuario. A diferencia del Capítulo 2 (diseño), este capítulo documenta lo efectivamente construido — código en ejecución, verificado mediante pruebas y demostraciones — y es explícito sobre lo que quedó diferido o pendiente. Bajo el propósito actualizado del Capítulo 1 — IDI como compañero didáctico que responde enseñando —, la implementación de cada módulo se reporta en dos planos: su función central y el estado de su requerimiento didáctico transversal (consolidado en la Sección 3.11). El resultado alimenta el análisis de resultados (OE4, Capítulo 4).


3.1. ADQUISICIÓN DE CONTEXTO: CONTEXT MANAGER AGENT Y FileConnector

Implementado. El agente se alimenta de una base de datos SQLite en memoria construida a partir de archivos fuente por base de datos (`databases/<db_name>/*.sql`), a través de `FileConnector` (generalizado desde `SoundwaveFileConnector`) y `backend/app/services/db/discovery.py`. El glosario de negocio se extrajo del código a un archivo `NN_<db>_survey.json` por base de datos — un aporte directo al propósito didáctico: el contexto que el sistema usa para entender el dominio es el mismo que el aprendiz puede consultar como material de estudio.

[PENDIENTE: captura de pantalla o traza de ejecución mostrando el paquete de contexto generado; medición real de latencia de generación de embeddings frente al umbral de <200ms del RF del Capítulo 1.]


3.2. COMPRENSIÓN DE CONSULTAS, CLARIFICACIÓN Y SALVAGUARDA DE FILTRADO

Implementado (Día 1), con perfil de instrucción especializado (`backend/app/prompts/clarification.md`) ajustado en el Día 3 contra los casos EC-01…EC-08.

Durante la fase de endurecimiento (Día 4) se añadió una salvaguarda de enrutamiento de consultas (commit `8cd337b`, 2026-07-06), cuyo diseño se documenta en el Capítulo 2 (§2.5): antes de que una pregunta llegue al parseo de intención y a la generación de SQL, un filtro basado en lista de permitidos (allowlist) determina si la pregunta se relaciona con la base de datos activa (vocabulario del dominio derivado del `DBProfile`) o si constituye una pregunta de conocimiento SQL. Las preguntas sobre el sistema o la base de datos seleccionada se responden por una ruta separada — las respuestas de la base de datos seleccionada —, siempre fundamentada en hechos actuales del `DBProfile`; las preguntas no relevantes para bases de datos quedan fuera del propósito de IDI y reciben una redirección cortés sin invocar el pipeline NL2SQL. La salvaguarda está cubierta por pruebas offline (`tests/test_meta_question_filter.py`, `tests/test_query_understanding.py`).

[PENDIENTE: evidencia de las tres categorías de ambigüedad (temporal, de entidad, de métrica) siendo correctamente detectadas.]


3.3. GENERADOR SQL

Implementado (Día 1), instrucción especializada ajustada en el Día 3 y reforzada en el Día 4 (commit `8cd337b`: ajustes en `sql_generator.py` y su perfil de instrucción).

[PENDIENTE: ejemplos representativos de SQL generado sobre SoundWave, con explicación en lenguaje natural y reporte de supuestos, tal como exige el RF del SQL Generator Agent (Capítulo 1, §1.6).]


3.4. AGENTE DE VERIFICACIÓN

Implementado (Día 1) como cadena de tres capas (sintaxis → semántica → sanidad). Validado en la Puerta D1 (Gate D1): 6/8 sondas EC pasaron; EC-07 y EC-08 fueron correctamente bloqueadas por la capa de verificación sintáctica — comportamiento fail-safe funcionando según diseño. Un hallazgo de datos del Día 3 es relevante para la evaluación (Capítulo 4): la artista referenciada en la sonda EC-08 ("Adele") no existe en los datos semilla de SoundWave, por lo que la respuesta correcta de esa sonda es 0 filas.

La implementación sigue la política de auto-corrección silenciosa fijada en la actualización del Capítulo 1 (UC-06): los fallos que el reintento automático resuelve se consumen como contexto interno y no se exponen al usuario; solo los fallos no corregibles (o los bloqueos de seguridad) llegan a la interfaz, y deben llegar como explicación conceptual, no como error técnico.

[PENDIENTE: medición real del tiempo de verificación de extremo a extremo frente al umbral de <2s.]


3.5. MOTOR DE VISUALIZACIÓN

Implementado (Día 2): selección automática de gráfico vía Recharts, integrada en la respuesta didáctica de 4 paneles.

[PENDIENTE: inventario de los 8 tipos de gráfico soportados frente a los especificados en el RF del Capítulo 1; captura de pantalla del panel de visualización.]


3.6. GESTOR DE SESIONES

Implementado (Día 2): `SessionLibrary`, drawer de perfil de base de datos, Zustand stores. En la restructuración multi-base de datos (2026-07-03), `data/sessions.db` se limpió y ahora usa el nombre de carpeta de la base de datos como identificador canónico; la base se auto-repara vacía en el siguiente arranque del backend.

**Defecto conocido (KI-1)**: al restaurar una sesión desde `SessionLibrary` solo se cargan las preguntas del usuario — las respuestas del asistente no se renderizan. La ruta de restauración (persistencia de turnos en backend y/o reconstrucción de `queryStore.loadFromSession`) requiere mejora. [PENDIENTE: resolver antes de congelar el capítulo, o documentar explícitamente como alcance abierto hacia OE4. KI-1 bloquea también el requerimiento didáctico del módulo (sesiones como "ruta de aprendizaje" exportable), pues una ruta de aprendizaje sin las respuestas del asistente pierde su valor de estudio.]


3.7. ORQUESTADOR MULTI-AGENTE

Implementado y extendido en el Día 3: activa el perfil de instrucción de cada agente inmediatamente antes de su ejecución e incorpora la etiqueta del perfil (`adapter`) en el payload `"started"` del `AgentEvent` correspondiente — sin requerir cambios en el frontend, que ya combinaba `payload.adapter` desde cualquier evento de estado. Esta trazabilidad de fase y agente activo constituye, además, el requerimiento didáctico del módulo ya implementado (Sección 3.11).

[PENDIENTE: documentar el mecanismo de reintento automático (máximo 2) y la propagación de cancelación (<500ms, UC-05) con evidencia de prueba, verificando que el reintento cumple la política de auto-corrección silenciosa (Sección 3.4).]


3.8. REGISTRO DE INSTRUCCIONES Y DISCIPLINA DE HOT-SWAP

Implementado (Día 3): `adapters/registry.json` + `backend/app/services/adapter_registry.py` externalizan el mapeo agente → perfil de instrucción. Los cuatro perfiles (`backend/app/prompts/*.md`) fueron expandidos a especializaciones reales ajustadas contra EC-01…EC-08. El servicio LLM expone además `chat_with_meta()` para reportar tokens/segundo, insumo de la evaluación de desempeño (Capítulo 4, §4.4).

[PENDIENTE: resultados del harness A/B base-vs-especializado (`tests/ab_harness.py`) — el harness ya existe pero requiere ejecución manual contra un backend en vivo; sus resultados pertenecen propiamente al Capítulo 4 (OE4), pero su *construcción* se documenta aquí.]


3.9. RECONSTRUCCIÓN DEL FRONTEND

Implementado (Día 2): respuestas didácticas de 4 paneles, etiquetas de perfil activo, autocompletado inline, `SessionLibrary` + drawer de perfil de BD, Zustand stores, `styles/tokens.css`, sin artefactos de Tailwind. Landing screen de selección de base de datos (`DatabaseSelector.tsx`) añadida en la restructuración multi-base de datos. La respuesta de 4 paneles es el vehículo principal del propósito didáctico en la interfaz: la misma respuesta que el ejecutivo lee como insight, el aprendiz la lee como lección (qué se entendió, qué SQL se construyó, qué resultado produjo y cómo se visualiza).

[PENDIENTE: capturas de pantalla del frontend actual — reemplazan las capturas del sandbox del Capítulo 1.]


3.10. DATOS SINTÉTICOS Y PREPARACIÓN PARA FINE-TUNING LoRA (DIFERIDO)

Esta sección debe ser explícita sobre una brecha frente al plan original: el Capítulo 1 (§1.10) especificó el entrenamiento de 4 adaptadores LoRA vía QLoRA/Unsloth sobre datasets de 15,000–20,000 ejemplos. Ese entrenamiento **no se ha ejecutado** — el seam de hot-swap está construido y probado (§3.8) pero opera hoy sobre perfiles de instrucción, no sobre pesos LoRA entrenados.

[PENDIENTE: cronograma real de generación de datos sintéticos y entrenamiento LoRA post-sprint; o, alternativamente, una justificación registrada de por qué el entrenamiento LoRA se excluye del alcance evaluado en OE4 y se traslada a trabajo futuro.]


3.11. ESTADO DEL REQUERIMIENTO DIDÁCTICO TRANSVERSAL POR MÓDULO

El Capítulo 1 (§1.6) asignó un requerimiento didáctico a cada uno de los siete módulos. Su estado de implementación, honesto frente a la evaluación de Claridad Didáctica del Capítulo 4 (§4.7), es el siguiente:

| Módulo | Requerimiento didáctico (Capítulo 1, §1.6) | Estado |
|---|---|---|
| Context Manager | Mini-glosario navegable del dominio, con ejemplos por término | Parcial: el drawer de perfil de BD (Día 2) expone esquema y contexto de la base activa; [PENDIENTE: ejemplos de consulta por término] |
| Query Understanding | Cada clarificación explica por qué la ambigüedad importa | [PENDIENTE: evidencia de ejecución] |
| SQL Generator | Anotación por cláusula del SQL generado | Parcial: la respuesta de 4 paneles incluye el SQL y su explicación; [PENDIENTE: verificar cobertura cláusula a cláusula] |
| Verification | Explicación conceptual de los fallos que llegan al usuario | [PENDIENTE: evidencia; los fallos auto-corregidos no se exponen, por la política silenciosa de UC-06] |
| Visualization Engine | Justificación de la elección del tipo de gráfico | [PENDIENTE: verificación en el panel de visualización] |
| Session Manager | Sesiones marcables como "ruta de aprendizaje" exportable | Pendiente — bloqueado parcialmente por KI-1 (§3.6) |
| Orchestrator | Trazabilidad de fase y agente activo | Implementado (Día 3): etiqueta del perfil en el evento `"started"` + etiquetas de perfil activo en el frontend |


3.12. ESTADO DE AVANCE Y PROBLEMAS CONOCIDOS

| Artefacto | Estado |
|---|---|
| Pipeline de 7 agentes end-to-end sobre `/query` | Completado (Día 1) |
| Frontend didáctico de 4 paneles | Completado (Día 2) |
| Registro de adaptadores/instrucciones + hot-swap | Completado (Día 3) |
| Suite de pruebas offline (`pytest`) | Completado (Día 3), extendida en Día 4 con las pruebas de filtrado de consultas |
| `ruff`/`black`, `eslint`/`prettier` | Completado (Día 3) |
| Salvaguarda de filtrado de consultas (allowlist) | Completado (Día 4, commit `8cd337b`, 2026-07-06) |
| Requerimientos didácticos transversales (7) | Parcial — ver Sección 3.11 |
| Restauración de sesión (respuestas del asistente) | **Pendiente — KI-1** |
| Conexión a base de datos real (MySQL) | **Pendiente — Día 4, en curso (al 2026-07-13)** |
| Entrenamiento LoRA | **Diferido — post-sprint** |

[PENDIENTE: incorporar el estado del Día 4 (Real DB Connection & Hardening) una vez cerrado.]


3.13. CONCLUSIONES DEL CAPÍTULO

[PENDIENTE — redactar al cierre, con al menos una conclusión rotulada "(aporta a OE3)". Candidata evidente a partir de este esqueleto: el requerimiento didáctico transversal se implementó sin módulos adicionales — donde está implementado, viaja dentro de los contratos existentes (4 paneles, etiquetas de perfil, drawer), validando la decisión de diseño del Capítulo 2 (§2.2).]


3.14. RECOMENDACIONES

[PENDIENTE — al menos una recomendación rotulada "(OE3)", orientada a la evaluación (OE4). Candidatas evidentes: (i) priorizar el cierre de KI-1 antes de la revisión experta heurística, dado que la continuidad de sesiones es un caso de uso central (UC-03) y bloquea el requerimiento didáctico del Session Manager; (ii) cerrar las brechas didácticas de la Sección 3.11 (QUA, VA, VE) antes de medir la métrica de Claridad Didáctica, para que la evaluación mida el diseño y no su ausencia.]


────────────────────────────────────────────────────────────────────────

REFERENCIAS

[PENDIENTE: heredar y extender la bibliografía de capítulos previos.]


────────────────────────────────────────────────────────────────────────

Universidad Nacional de Colombia — Facultad de Ingeniería — Departamento de Sistemas e Industrial
Período 2026-1S
