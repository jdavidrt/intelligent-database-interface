IDI — Interfaz Inteligente de Bases de Datos

Trabajo de Grado — Ingeniería de Sistemas y Computación
Universidad Nacional de Colombia
Autor: Juan David Ramírez Torres (jdramirezt@unal.edu.co)
Período: 2026-1S (Febrero 2 – Mayo 30, 2026)

> **[ESQUELETO / DEMO — v2]** Este documento es un armazón estructural para el Capítulo 2, construido para validar la numeración, la trazabilidad OE2 y la cobertura de subtemas antes de redactar el contenido definitivo. La v2 alinea el capítulo con la actualización del Capítulo 1: el propósito didáctico pasa a ser la identidad principal del proyecto (el acceso ejecutivo es su consecuencia directa), la especificación queda en 62 requerimientos funcionales (55 de función central más 7 didácticos transversales) y 20 no funcionales (incluida la claridad didáctica), los escenarios de uso son siete (UC-01–UC-07) y la política de auto-corrección es silenciosa (UC-06). Se añaden dos secciones nuevas: la obligación didáctica como preocupación transversal de diseño (2.2) y la salvaguarda de enrutamiento de consultas por lista de permitidos (2.5). Las secciones marcadas `[PENDIENTE]` requieren redacción, evidencia o diagramas que aún no se han producido. El contenido no marcado refleja decisiones ya tomadas y visibles en el repositorio (`MASTERPLAN.md`, `CLAUDE.md`, historial de commits) y se incluye para anclar el capítulo a hechos verificables.


ÍNDICE

Capítulo 2: Diseño del Sistema
    2.1. Arquitectura General de Agentes
    2.2. La Obligación Didáctica como Preocupación Transversal de Diseño
    2.3. Contratos de API entre Módulos
    2.4. Diseño de la Cadena de Verificación Tripartita y Política de Auto-Corrección Silenciosa
    2.5. Enrutamiento de Consultas: Salvaguarda de Filtrado por Lista de Permitidos
    2.6. Gestión de Sesiones: Modelo de Datos y Ciclo de Vida
    2.7. Estrategia de Comunicación de Progreso
    2.8. Selección y Justificación del Stack Tecnológico
    2.9. Decisión Arquitectónica: De LoRA Hot-Swap a Instruction-Profile Hot-Swap
    2.10. Diseño Multi-Base de Datos y Descubrimiento Dinámico
    2.11. Conclusiones del Capítulo
    2.12. Recomendaciones


────────────────────────────────────────────────────────────────────────

CAPÍTULO 2: DISEÑO DEL SISTEMA

Este capítulo desarrolla el segundo objetivo específico (OE2): diseñar la arquitectura modular de IDI, especificando responsabilidades de componentes, protocolos de comunicación inter-agente, flujos de datos, mecanismos de gestión de sesiones, estrategias de comunicación de progreso y selección de stack tecnológico. Toma como punto de partida la especificación de requerimientos del Capítulo 1 (62 RF — 55 de función central más 7 requerimientos didácticos transversales, uno por módulo — y 20 RNF, incluido el de claridad didáctica) y la traduce en decisiones arquitectónicas concretas, varias de las cuales ya fueron validadas empíricamente durante la implementación temprana (Días 0–4 del plan de desarrollo). Bajo el propósito actualizado del Capítulo 1 — IDI como compañero didáctico cuya capacidad de responder enseñando habilita, como consecuencia, el acceso ejecutivo a los datos —, el diseño trata la obligación didáctica no como una funcionalidad más sino como una preocupación transversal de arquitectura: una restricción que el contrato de cada agente debe satisfacer (Sección 2.2). El resultado alimenta directamente el desarrollo de la solución (OE3, Capítulo 3).


2.1. ARQUITECTURA GENERAL DE AGENTES

[PENDIENTE: diagrama UML/C4 formal de los siete módulos y sus dependencias.]

El sistema orquesta siete agentes especializados — Context Manager, Query Understanding, SQL Generator, Verification, Visualization Engine, Session Manager y Multi-Agent Orchestrator — coordinados por un orquestador central que activa el perfil de instrucción correspondiente antes de invocar a cada agente. La arquitectura fue validada de forma incremental: el pipeline agentic completo corre de extremo a extremo sobre `/query` desde el Día 1 (DB-less, alimentado por `FileConnector`).

| Agente | Responsabilidad | Estado de diseño |
|---|---|---|
| Context Manager Agent | Adquisición de contexto y glosario de negocio | [PENDIENTE: especificación formal de la encuesta de onboarding] |
| Query Understanding Agent | Parseo de intención y detección de ambigüedad | Implementado (Día 1); endurecido con salvaguarda de filtrado (Día 4, Sección 2.5) |
| SQL Generator Agent | Traducción NL→SQL | Implementado (Día 1) |
| Verification Agent | Verificación sintáctica/semántica/de sanidad | Implementado (Día 1) |
| Visualization Engine | Selección automática de gráfico | Implementado (Día 2) |
| Session Manager Agent | Persistencia y continuidad de sesiones | Implementado (Día 2), con defecto conocido KI-1 |
| Multi-Agent Orchestrator | Enrutamiento y ciclo de vida | Implementado, extendido en Día 3 con activación de perfiles |


2.2. LA OBLIGACIÓN DIDÁCTICA COMO PREOCUPACIÓN TRANSVERSAL DE DISEÑO

El Capítulo 1 (§1.6) asignó a cada módulo un requerimiento didáctico transversal: además de ejecutar su función, cada agente debe exponer al usuario — aprendiz o ejecutivo — el razonamiento detrás de lo que hizo. Arquitectónicamente, esto no se diseñó como un octavo módulo "didáctico" sino como una restricción sobre los contratos de salida de los siete existentes: el mismo formato de respuesta sirve al ejecutivo (que lee el insight y actúa) y al aprendiz (que lee el porqué y aprende). Tres decisiones de diseño, ya visibles en el artefacto, materializan esta restricción:

1. La respuesta didáctica de 4 paneles como formato canónico de salida (Día 2): toda respuesta expone qué entendió el sistema, qué SQL construyó y por qué, qué resultado obtuvo y cómo se visualiza — el vehículo de los requerimientos didácticos del SQL Generator y del Visualization Engine.

2. La trazabilidad del perfil activo: el orquestador incorpora la etiqueta del perfil de instrucción activo en el evento `"started"` de cada agente, y el frontend la muestra como badge — el aprendiz puede ver qué "sombrero" lleva puesto el modelo en cada fase del pipeline (requerimiento didáctico del Multi-Agent Orchestrator; escenario UC-07).

3. El perfil de base de datos como material de estudio: el drawer de perfil de BD expone el esquema y el contexto de la base activa — semilla del mini-glosario navegable exigido al Context Manager Agent.

[PENDIENTE: mapa completo requerimiento didáctico → decisión de diseño → componente para los siete módulos; los del Query Understanding (clarificación como lección), Verification (explicación conceptual de fallos que sí llegan al usuario), Visualization (justificación de la elección de gráfico) y Session Manager (sesiones como "ruta de aprendizaje" exportable) aún no tienen decisión de diseño registrada.]


2.3. CONTRATOS DE API ENTRE MÓDULOS

[PENDIENTE: especificación OpenAPI y modelos Pydantic formalizados por endpoint.]

Recomendación heredada del Capítulo 1 (§1.13, OE2): formalizar los contratos de API mediante esquemas explícitos antes de que la verificación tripartita y la orquestación se prueben en aislamiento. [PENDIENTE: tabla de endpoints — `/query`, `/db/list`, `/db/last-used`, `/db/select`, y los eventos WebSocket — con su esquema de entrada/salida.]


2.4. DISEÑO DE LA CADENA DE VERIFICACIÓN TRIPARTITA Y POLÍTICA DE AUTO-CORRECCIÓN SILENCIOSA

[PENDIENTE: diagrama de flujo de las tres capas.]

La verificación se diseñó como una cadena no negociable de tres capas — sintaxis, semántica, sanidad — descrita en `MASTERPLAN.md` §4. Una decisión de diseño fijada en la actualización del Capítulo 1 gobierna el comportamiento de esta cadena hacia el usuario: la auto-corrección es silenciosa (UC-06). Los fallos de verificación que el reintento automático logra resolver se consumen como contexto interno del pipeline — el usuario nunca ve un resultado erróneo ni el detalle del error corregido. Solo los fallos que no pueden resolverse automáticamente (o los bloqueos deliberados de seguridad) se comunican, y se comunican como explicación conceptual, no como mensaje de error técnico (requerimiento didáctico del Verification Agent, Capítulo 1 §1.6).

[PENDIENTE: justificación de diseño de cada capa, umbrales de rechazo, y su relación con la categoría de error dominante identificada en el Capítulo 1 (schema linking, 27–68% de fallos).]


2.5. ENRUTAMIENTO DE CONSULTAS: SALVAGUARDA DE FILTRADO POR LISTA DE PERMITIDOS

Decisión de diseño posterior al Capítulo 1, surgida durante el endurecimiento del pipeline (Día 4; commit `8cd337b`, 2026-07-06) y candidata a documentarse como ADR: no toda entrada del usuario debe llegar al pipeline NL2SQL. El diseño distingue tres rutas de respuesta:

a) preguntas relacionadas con la base de datos activa o con conocimiento de SQL: siguen el pipeline completo (intención → SQL → verificación → resultado);
b) preguntas meta sobre el sistema o sobre la base de datos ("¿qué tablas tienes?", "¿qué puedes hacer?"): se responden por una ruta directa, siempre fundamentada en hechos actuales del `DBProfile` — nunca desde la memoria del modelo;
c) preguntas personales o fuera de tema: se contestan con una redirección cortés, sin invocar el pipeline NL2SQL.

La pertenencia a la ruta (a) se decide por lista de permitidos (allowlist) — relación de la pregunta con el vocabulario del dominio derivado del `DBProfile`, o señal de pregunta de conocimiento SQL — y no por una lista negra de patrones. La razón: una blocklist de formulaciones fuera de tema siempre queda un caso por detrás de las formulaciones imprevistas, mientras que la allowlist falla de forma segura — lo que no se reconoce como pertinente no genera SQL, en coherencia con el principio fail-safe del proyecto.

[PENDIENTE: diagrama de decisión de las tres rutas y su relación formal con el contrato del Query Understanding Agent.]


2.6. GESTIÓN DE SESIONES: MODELO DE DATOS Y CICLO DE VIDA

[PENDIENTE: diagrama entidad-relación de `data/sessions.db`.]

El diseño soporta guardar, retomar, buscar y exportar sesiones investigativas (UC-03 del Capítulo 1), incluyendo la marcación de una sesión como "ruta de aprendizaje" exportable como material de estudio (requerimiento didáctico del Session Manager Agent). [PENDIENTE: documentar el defecto conocido KI-1 — la restauración de sesión actualmente solo recupera las preguntas del usuario, no las respuestas del asistente — como una brecha de diseño a cerrar antes de la evaluación (OE4).]


2.7. ESTRATEGIA DE COMUNICACIÓN DE PROGRESO

El diseño usa WebSockets para emitir `AgentEvent`s de progreso en tiempo real, con el perfil de instrucción activo (`adapter`) incorporado en el evento `"started"` de cada agente — de modo que el frontend puede mostrar qué "sombrero" lleva puesto el modelo en cada fase, sin requerir cambios adicionales en el store del frontend. Esta trazabilidad cumple una doble función fijada en el Capítulo 1: comunicación de progreso para el ejecutivo (RNF de desempeño, consultas de hasta 30 segundos con progreso informado) y transparencia arquitectónica para el aprendiz (requerimiento didáctico del Multi-Agent Orchestrator, escenario UC-07). [PENDIENTE: especificación de estimación de tiempo restante y del contrato de cancelación (<500ms, UC-05).]


2.8. SELECCIÓN Y JUSTIFICACIÓN DEL STACK TECNOLÓGICO

| Capa | Tecnología | Justificación |
|---|---|---|
| Motor de inferencia | llama.cpp + Qwen2.5-Coder-3B-Instruct (Q4_K_M) | Validado en el sandbox (Capítulo 1, §1.11): ~2GB VRAM, 25–35 tok/s en GPU, funcional en CPU-only |
| Backend | FastAPI | [PENDIENTE: justificación formal frente a alternativas] |
| Frontend | React + TypeScript + Zustand, CSS Modules (sin Tailwind) | Decisión fijada en el Día 1 del plan de desarrollo |
| Persistencia de sesiones | SQLite (`data/sessions.db`) | Auto-reparable, sin dependencia de servicios externos (RNF de seguridad/offline) |
| Contexto vectorial | ChromaDB | [PENDIENTE: justificación frente a alternativas de embeddings] |

[PENDIENTE: sección completa de justificación técnica — actualmente vive de forma dispersa en `docs/TECHNOLOGY_DEEP_DIVE.md` y debe consolidarse aquí.]


2.9. DECISIÓN ARQUITECTÓNICA: DE LoRA HOT-SWAP A INSTRUCTION-PROFILE HOT-SWAP

Esta sección documenta una desviación explícita frente al Capítulo 1 y debe redactarse como un Architecture Decision Record (ADR), tal como recomienda el propio Capítulo 1 (§1.13, OE2).

El Capítulo 1 (§1.10) especificó adaptadores LoRA intercambiables en caliente como el mecanismo de especialización. La implementación replanificada ("REPLAN v2") invierte el orden del sprint — agentes primero, base de datos física al final — y difiere el *entrenamiento* de LoRA para después del sprint. En su lugar, el mismo seam de `load_adapter()` que más adelante cargará adaptadores GGUF hoy intercambia **perfiles de instrucción** (`backend/app/prompts/<agente>.md`), registrados en `adapters/registry.json` y activados por `backend/app/services/adapter_registry.py` inmediatamente antes de que cada agente se ejecute.

[PENDIENTE: justificación explícita de por qué esta sustitución es válida para satisfacer el RNF de extensibilidad ("adaptadores LoRA intercambiables sin reinicio del servidor") durante la fase intermedia, y qué criterio determina el momento de reemplazar los perfiles por adaptadores LoRA reales entrenados.]


2.10. DISEÑO MULTI-BASE DE DATOS Y DESCUBRIMIENTO DINÁMICO

Otra desviación de diseño no anticipada en el Capítulo 1: la arquitectura evolucionó de una base de datos fija (SoundWave hardcodeada) a un diseño multi-base de datos. `SoundwaveFileConnector` se generalizó a `FileConnector` (parametrizado por `db_name`), y `backend/app/services/db/discovery.py` escanea dinámicamente `databases/` sin requerir cambios de código para añadir una base de datos nueva. El glosario de negocio, antes hardcodeado en `context_manager.py`, se extrajo a una convención genérica `NN_<db>_survey.json` por base de datos.

Bajo el propósito didáctico actualizado del Capítulo 1, esta decisión adquiere una justificación adicional: un entorno de aprendizaje gana valor si el estudiante puede practicar sobre bases de datos distintas — dejar caer una carpeta nueva en `databases/` basta para tener un nuevo terreno de práctica, sin cambios de código. [PENDIENTE: justificar formalmente esta decisión frente a los requerimientos originales del Context Manager Agent (§1.6 del Capítulo 1), que asumían una única base de datos de prueba.]


2.11. CONCLUSIONES DEL CAPÍTULO

[PENDIENTE — redactar al cierre del capítulo, con al menos una conclusión rotulada "(aporta a OE2)", siguiendo el patrón de trazabilidad del Capítulo 1. Candidatas evidentes a partir de este esqueleto: (i) la obligación didáctica pudo satisfacerse como restricción de contratos sin añadir módulos — evidencia de que el complemento de alcance no alteró la arquitectura aprobada; (ii) el seam `load_adapter()` demostró que la especialización por perfiles de instrucción y la futura especialización por LoRA son intercambiables desde el punto de vista del orquestador.]


2.12. RECOMENDACIONES

[PENDIENTE — al menos una recomendación rotulada "(OE2)", orientada a la fase de desarrollo (OE3). Candidatas evidentes: (i) documentar como ADRs formales las tres desviaciones registradas en este capítulo (Secciones 2.5, 2.9 y 2.10) antes del cierre del documento final; (ii) diseñar las decisiones didácticas aún sin registrar (Sección 2.2, QUA/VA/VE/SMA) antes de la evaluación de la métrica de Claridad Didáctica (Capítulo 4).]


────────────────────────────────────────────────────────────────────────

REFERENCIAS

[PENDIENTE: heredar y extender la bibliografía del Capítulo 1 según se citen nuevas fuentes de diseño arquitectónico.]


────────────────────────────────────────────────────────────────────────

Universidad Nacional de Colombia — Facultad de Ingeniería — Departamento de Sistemas e Industrial
Período 2026-1S
