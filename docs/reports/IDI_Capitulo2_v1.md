IDI — Interfaz Inteligente de Bases de Datos

Trabajo de Grado — Ingeniería de Sistemas y Computación
Universidad Nacional de Colombia
Autor: Juan David Ramírez Torres (jdramirezt@unal.edu.co)
Período: 2026-1S (Febrero 2 – Mayo 30, 2026)

> **[ESQUELETO / DEMO — v1]** Este documento es un armazón estructural para el Capítulo 2, construido para validar la numeración, la trazabilidad OE2 y la cobertura de subtemas antes de redactar el contenido definitivo. Las secciones marcadas `[PENDIENTE]` requieren redacción, evidencia o diagramas que aún no se han producido. El contenido no marcado refleja decisiones ya tomadas y visibles en el repositorio (`MASTERPLAN.md`, `CLAUDE.md`) y se incluye para anclar el capítulo a hechos verificables.


ÍNDICE

Capítulo 2: Diseño del Sistema
    2.1. Arquitectura General de Agentes
    2.2. Contratos de API entre Módulos
    2.3. Diseño de la Cadena de Verificación Tripartita
    2.4. Gestión de Sesiones: Modelo de Datos y Ciclo de Vida
    2.5. Estrategia de Comunicación de Progreso
    2.6. Selección y Justificación del Stack Tecnológico
    2.7. Decisión Arquitectónica: De LoRA Hot-Swap a Instruction-Profile Hot-Swap
    2.8. Diseño Multi-Base de Datos y Descubrimiento Dinámico
    2.9. Conclusiones del Capítulo
    2.10. Recomendaciones


────────────────────────────────────────────────────────────────────────

CAPÍTULO 2: DISEÑO DEL SISTEMA

Este capítulo desarrolla el segundo objetivo específico (OE2): diseñar la arquitectura modular de IDI, especificando responsabilidades de componentes, protocolos de comunicación inter-agente, flujos de datos, mecanismos de gestión de sesiones, estrategias de comunicación de progreso y selección de stack tecnológico. Toma como punto de partida la especificación de requerimientos del Capítulo 1 (54 RF, 19 RNF) y la traduce en decisiones arquitectónicas concretas, varias de las cuales ya fueron validadas empíricamente durante la implementación temprana (Días 0–3 del plan de desarrollo). El resultado alimenta directamente el desarrollo de la solución (OE3, Capítulo 3).


2.1. ARQUITECTURA GENERAL DE AGENTES

[PENDIENTE: diagrama UML/C4 formal de los siete módulos y sus dependencias.]

El sistema orquesta siete agentes especializados — Context Manager, Query Understanding, SQL Generator, Verification, Visualization Engine, Session Manager y Multi-Agent Orchestrator — coordinados por un orquestador central que activa el perfil de instrucción correspondiente antes de invocar a cada agente. La arquitectura fue validada de forma incremental: el pipeline agentic completo corre de extremo a extremo sobre `/query` desde el Día 1 (DB-less, alimentado por `SoundwaveFileConnector`).

| Agente | Responsabilidad | Estado de diseño |
|---|---|---|
| Context Manager Agent | Adquisición de contexto y glosario de negocio | [PENDIENTE: especificación formal de la encuesta de onboarding] |
| Query Understanding Agent | Parseo de intención y detección de ambigüedad | Implementado (Día 1) |
| SQL Generator Agent | Traducción NL→SQL | Implementado (Día 1) |
| Verification Agent | Verificación sintáctica/semántica/de sanidad | Implementado (Día 1) |
| Visualization Engine | Selección automática de gráfico | Implementado (Día 2) |
| Session Manager Agent | Persistencia y continuidad de sesiones | Implementado (Día 2), con defecto conocido KI-1 |
| Multi-Agent Orchestrator | Enrutamiento y ciclo de vida | Implementado, extendido en Día 3 con activación de perfiles |


2.2. CONTRATOS DE API ENTRE MÓDULOS

[PENDIENTE: especificación OpenAPI y modelos Pydantic formalizados por endpoint.]

Recomendación heredada del Capítulo 1 (§1.13, OE2): formalizar los contratos de API mediante esquemas explícitos antes de que la verificación tripartita y la orquestación se prueben en aislamiento. [PENDIENTE: tabla de endpoints — `/query`, `/db/list`, `/db/last-used`, `/db/select`, y los eventos WebSocket — con su esquema de entrada/salida.]


2.3. DISEÑO DE LA CADENA DE VERIFICACIÓN TRIPARTITA

[PENDIENTE: diagrama de flujo de las tres capas.]

La verificación se diseñó como una cadena no negociable de tres capas — sintaxis, semántica, sanidad — descrita en `MASTERPLAN.md` §4. [PENDIENTE: justificación de diseño de cada capa, umbrales de rechazo, y su relación con la categoría de error dominante identificada en el Capítulo 1 (schema linking, 27–68% de fallos).]


2.4. GESTIÓN DE SESIONES: MODELO DE DATOS Y CICLO DE VIDA

[PENDIENTE: diagrama entidad-relación de `data/sessions.db`.]

El diseño soporta guardar, retomar, buscar y exportar sesiones investigativas (UC-03 del Capítulo 1). [PENDIENTE: documentar el defecto conocido KI-1 — la restauración de sesión actualmente solo recupera las preguntas del usuario, no las respuestas del asistente — como una brecha de diseño a cerrar antes de la evaluación (OE4).]


2.5. ESTRATEGIA DE COMUNICACIÓN DE PROGRESO

El diseño usa WebSockets para emitir `AgentEvent`s de progreso en tiempo real, con el perfil de instrucción activo (`adapter`) incorporado en el evento `"started"` de cada agente — de modo que el frontend puede mostrar qué "sombrero" lleva puesto el modelo en cada fase, sin requerir cambios adicionales en el store del frontend. [PENDIENTE: especificación de estimación de tiempo restante y del contrato de cancelación (<500ms, UC-05).]


2.6. SELECCIÓN Y JUSTIFICACIÓN DEL STACK TECNOLÓGICO

| Capa | Tecnología | Justificación |
|---|---|---|
| Motor de inferencia | llama.cpp + Qwen2.5-Coder-3B-Instruct (Q4_K_M) | Validado en el sandbox (Capítulo 1, §1.11): ~2GB VRAM, 25–35 tok/s en GPU, funcional en CPU-only |
| Backend | FastAPI | [PENDIENTE: justificación formal frente a alternativas] |
| Frontend | React + TypeScript + Zustand, CSS Modules (sin Tailwind) | Decisión fijada en el Día 1 del plan de desarrollo |
| Persistencia de sesiones | SQLite (`data/sessions.db`) | Auto-reparable, sin dependencia de servicios externos (RNF de seguridad/offline) |
| Contexto vectorial | ChromaDB | [PENDIENTE: justificación frente a alternativas de embeddings] |

[PENDIENTE: sección completa de justificación técnica — actualmente vive de forma dispersa en `docs/TECHNOLOGY_DEEP_DIVE.md` y debe consolidarse aquí.]


2.7. DECISIÓN ARQUITECTÓNICA: DE LoRA HOT-SWAP A INSTRUCTION-PROFILE HOT-SWAP

Esta sección documenta una desviación explícita frente al Capítulo 1 y debe redactarse como un Architecture Decision Record (ADR), tal como recomienda el propio Capítulo 1 (§1.13, OE2).

El Capítulo 1 (§1.10) especificó adaptadores LoRA intercambiables en caliente como el mecanismo de especialización. La implementación replanificada ("REPLAN v2") invierte el orden del sprint — agentes primero, base de datos física al final — y difiere el *entrenamiento* de LoRA para después del sprint. En su lugar, el mismo seam de `load_adapter()` que más adelante cargará adaptadores GGUF hoy intercambia **perfiles de instrucción** (`backend/app/prompts/<agente>.md`), registrados en `adapters/registry.json` y activados por `backend/app/services/adapter_registry.py` inmediatamente antes de que cada agente se ejecute.

[PENDIENTE: justificación explícita de por qué esta sustitución es válida para satisfacer el RNF de extensibilidad ("adaptadores LoRA intercambiables sin reinicio del servidor") durante la fase intermedia, y qué criterio determina el momento de reemplazar los perfiles por adaptadores LoRA reales entrenados.]


2.8. DISEÑO MULTI-BASE DE DATOS Y DESCUBRIMIENTO DINÁMICO

Otra desviación de diseño no anticipada en el Capítulo 1: la arquitectura evolucionó de una base de datos fija (SoundWave hardcodeada) a un diseño multi-base de datos. `SoundwaveFileConnector` se generalizó a `FileConnector` (parametrizado por `db_name`), y `backend/app/services/db/discovery.py` escanea dinámicamente `databases/` sin requerir cambios de código para añadir una base de datos nueva. El glosario de negocio, antes hardcodeado en `context_manager.py`, se extrajo a una convención genérica `NN_<db>_survey.json` por base de datos.

[PENDIENTE: justificar esta decisión frente a los requerimientos originales del Context Manager Agent (§1.6 del Capítulo 1), que asumían una única base de datos de prueba.]


2.9. CONCLUSIONES DEL CAPÍTULO

[PENDIENTE — redactar al cierre del capítulo, con al menos una conclusión rotulada "(aporta a OE2)", siguiendo el patrón de trazabilidad del Capítulo 1.]


2.10. RECOMENDACIONES

[PENDIENTE — al menos una recomendación rotulada "(OE2)", orientada a la fase de desarrollo (OE3).]


────────────────────────────────────────────────────────────────────────

REFERENCIAS

[PENDIENTE: heredar y extender la bibliografía del Capítulo 1 según se citen nuevas fuentes de diseño arquitectónico.]


────────────────────────────────────────────────────────────────────────

Universidad Nacional de Colombia — Facultad de Ingeniería — Departamento de Sistemas e Industrial
Período 2026-1S
