IDI — Interfaz Inteligente de Bases de Datos

Trabajo de Grado — Ingeniería de Sistemas y Computación
Universidad Nacional de Colombia
Autor: Juan David Ramírez Torres (jdramirezt@unal.edu.co)
Período: 2026-1S (Febrero 2 – Mayo 30, 2026)

> **[ESQUELETO / DEMO — v1]** Armazón estructural para el Capítulo 3. Las secciones `[PENDIENTE]` requieren redacción, capturas de pantalla o evidencia de ejecución que aún no se han producido. El contenido no marcado refleja trabajo ya completado y verificable en el repositorio (Días 1–3 del plan de desarrollo, per `CLAUDE.md`).


ÍNDICE

Capítulo 3: Desarrollo de la Solución
    3.1. Adquisición de Contexto: Context Manager Agent y FileConnector
    3.2. Comprensión de Consultas y Clarificación
    3.3. Generador SQL
    3.4. Agente de Verificación
    3.5. Motor de Visualización
    3.6. Gestor de Sesiones
    3.7. Orquestador Multi-Agente
    3.8. Registro de Instrucciones y Disciplina de Hot-Swap
    3.9. Reconstrucción del Frontend
    3.10. Datos Sintéticos y Preparación para Fine-Tuning LoRA (Diferido)
    3.11. Estado de Avance y Problemas Conocidos
    3.12. Conclusiones del Capítulo
    3.13. Recomendaciones


────────────────────────────────────────────────────────────────────────

CAPÍTULO 3: DESARROLLO DE LA SOLUCIÓN

Este capítulo desarrolla el tercer objetivo específico (OE3): implementar los siete módulos centrales de IDI con generación de datos sintéticos de entrenamiento, pipelines de fine-tuning, gestión de flujo conversacional y componentes de interfaz de usuario. A diferencia del Capítulo 2 (diseño), este capítulo documenta lo efectivamente construido — código en ejecución, verificado mediante pruebas y demostraciones — y es explícito sobre lo que quedó diferido o pendiente. El resultado alimenta el análisis de resultados (OE4, Capítulo 4).


3.1. ADQUISICIÓN DE CONTEXTO: CONTEXT MANAGER AGENT Y FileConnector

Implementado. El agente se alimenta de una base de datos SQLite en memoria construida a partir de archivos fuente por base de datos (`databases/<db_name>/*.sql`), a través de `FileConnector` (generalizado desde `SoundwaveFileConnector`) y `backend/app/services/db/discovery.py`. El glosario de negocio se extrajo del código a un archivo `NN_<db>_survey.json` por base de datos.

[PENDIENTE: captura de pantalla o traza de ejecución mostrando el paquete de contexto generado; medición real de latencia de generación de embeddings frente al umbral de <200ms del RF del Capítulo 1.]


3.2. COMPRENSIÓN DE CONSULTAS Y CLARIFICACIÓN

Implementado (Día 1), con perfil de instrucción especializado (`backend/app/prompts/clarification.md`) ajustado en el Día 3 contra los casos EC-01…EC-08. [PENDIENTE: evidencia de las tres categorías de ambigüedad (temporal, de entidad, de métrica) siendo correctamente detectadas; nota de trabajo en curso — el archivo `clarification.py` y el test `test_meta_question_filter.py` están actualmente en modificación/creación sin comprometer.]


3.3. GENERADOR SQL

Implementado (Día 1), instrucción especializada ajustada en el Día 3.

[PENDIENTE: ejemplos representativos de SQL generado sobre SoundWave, con explicación en lenguaje natural y reporte de supuestos, tal como exige el RF del SQL Generator Agent (Capítulo 1, §1.6).]


3.4. AGENTE DE VERIFICACIÓN

Implementado (Día 1) como cadena de tres capas (sintaxis → semántica → sanidad). Validado en la Puerta D1 (Gate D1): 6/8 sondas EC pasaron; EC-07 y EC-08 fueron correctamente bloqueadas por la capa de verificación sintáctica — comportamiento fail-safe funcionando según diseño.

[PENDIENTE: medición real del tiempo de verificación de extremo a extremo frente al umbral de <2s.]


3.5. MOTOR DE VISUALIZACIÓN

Implementado (Día 2): selección automática de gráfico vía Recharts, integrada en la respuesta didáctica de 4 paneles.

[PENDIENTE: inventario de los 8 tipos de gráfico soportados frente a los especificados en el RF del Capítulo 1; captura de pantalla del panel de visualización.]


3.6. GESTOR DE SESIONES

Implementado (Día 2): `SessionLibrary`, drawer de perfil de base de datos, Zustand stores.

**Defecto conocido (KI-1)**: al restaurar una sesión desde `SessionLibrary` solo se cargan las preguntas del usuario — las respuestas del asistente no se renderizan. La ruta de restauración (persistencia de turnos en backend y/o reconstrucción de `queryStore.loadFromSession`) requiere mejora. [PENDIENTE: resolver antes de congelar el capítulo, o documentar explícitamente como alcance abierto hacia OE4.]


3.7. ORQUESTADOR MULTI-AGENTE

Implementado y extendido en el Día 3: activa el perfil de instrucción de cada agente inmediatamente antes de su ejecución e incorpora la etiqueta del perfil (`adapter`) en el payload `"started"` del `AgentEvent` correspondiente — sin requerir cambios en el frontend, que ya combinaba `payload.adapter` desde cualquier evento de estado.

[PENDIENTE: documentar el mecanismo de reintento automático (máximo 2) y la propagación de cancelación (<500ms, UC-05) con evidencia de prueba.]


3.8. REGISTRO DE INSTRUCCIONES Y DISCIPLINA DE HOT-SWAP

Implementado (Día 3): `adapters/registry.json` + `backend/app/services/adapter_registry.py` externalizan el mapeo agente → perfil de instrucción. Los cuatro perfiles (`backend/app/prompts/*.md`) fueron expandidos a especializaciones reales ajustadas contra EC-01…EC-08.

[PENDIENTE: resultados del harness A/B base-vs-especializado (`tests/ab_harness.py`) — el harness ya existe pero requiere ejecución manual contra un backend en vivo; sus resultados pertenecen propiamente al Capítulo 4 (OE4), pero su *construcción* se documenta aquí.]


3.9. RECONSTRUCCIÓN DEL FRONTEND

Implementado (Día 2): respuestas didácticas de 4 paneles, badges de adaptador, autocompletado inline, `SessionLibrary` + drawer de perfil de BD, Zustand stores, `styles/tokens.css`, sin artefactos de Tailwind. Landing screen de selección de base de datos (`DatabaseSelector.tsx`) añadida en la restructuración multi-base de datos.

[PENDIENTE: capturas de pantalla del frontend actual — reemplazan las capturas del sandbox del Capítulo 1.]


3.10. DATOS SINTÉTICOS Y PREPARACIÓN PARA FINE-TUNING LoRA (DIFERIDO)

Esta sección debe ser explícita sobre una brecha frente al plan original: el Capítulo 1 (§1.10) especificó el entrenamiento de 4 adaptadores LoRA vía QLoRA/Unsloth sobre datasets de 15,000–20,000 ejemplos. Ese entrenamiento **no se ha ejecutado** — el seam de hot-swap está construido y probado (§3.8) pero opera hoy sobre perfiles de instrucción, no sobre pesos LoRA entrenados.

[PENDIENTE: cronograma real de generación de datos sintéticos y entrenamiento LoRA post-sprint; o, alternativamente, una justificación registrada de por qué el entrenamiento LoRA se excluye del alcance evaluado en OE4 y se traslada a trabajo futuro.]


3.11. ESTADO DE AVANCE Y PROBLEMAS CONOCIDOS

| Artefacto | Estado |
|---|---|
| Pipeline de 7 agentes end-to-end sobre `/query` | Completado (Día 1) |
| Frontend didáctico de 4 paneles | Completado (Día 2) |
| Registro de adaptadores/instrucciones + hot-swap | Completado (Día 3) |
| Suite de 24 pruebas offline (`pytest`) | Completado (Día 3) |
| `ruff`/`black`, `eslint`/`prettier` | Completado (Día 3) |
| Restauración de sesión (respuestas del asistente) | **Pendiente — KI-1** |
| Conexión a base de datos real (MySQL) | **Pendiente — Día 4, en curso** |
| Entrenamiento LoRA | **Diferido — post-sprint** |

[PENDIENTE: incorporar el estado del Día 4 (Real DB Connection & Hardening) una vez cerrado.]


3.12. CONCLUSIONES DEL CAPÍTULO

[PENDIENTE — redactar al cierre, con al menos una conclusión rotulada "(aporta a OE3)".]


3.13. RECOMENDACIONES

[PENDIENTE — al menos una recomendación rotulada "(OE3)", orientada a la evaluación (OE4). Candidata evidente a partir de este esqueleto: priorizar el cierre de KI-1 antes de la revisión experta heurística, dado que la continuidad de sesiones es un caso de uso central (UC-03).]


────────────────────────────────────────────────────────────────────────

REFERENCIAS

[PENDIENTE: heredar y extender la bibliografía de capítulos previos.]


────────────────────────────────────────────────────────────────────────

Universidad Nacional de Colombia — Facultad de Ingeniería — Departamento de Sistemas e Industrial
Período 2026-1S
